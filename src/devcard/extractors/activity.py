from __future__ import annotations

import logging
import statistics
from collections import Counter
from datetime import UTC, datetime, timedelta

from devcard.github.client import GitHubClient
from devcard.github.models import GitHubRepo, GitHubUser
from devcard.models import Activity

logger = logging.getLogger(__name__)

_DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_SPARKLINE_CHARS = " ▁▂▃▄▅▆▇█"


async def extract_activity(
    client: GitHubClient,
    user: GitHubUser,
    repos: list[GitHubRepo],
    **kwargs,
) -> Activity | None:
    try:
        events = kwargs.get("events")
        if events is None:
            events = await client.get_user_events(user.login)
        now = datetime.now(UTC)

        push_events = [e for e in events if e.type == "PushEvent"]

        heatmap = [[0] * 24 for _ in range(7)]
        hour_counts: Counter[int] = Counter()
        most_recent_event = None
        event_dates: set[str] = set()

        for event in push_events:
            try:
                dt = datetime.fromisoformat(event.created_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                continue
            if most_recent_event is None or dt > most_recent_event:
                most_recent_event = dt
            heatmap[dt.weekday()][dt.hour] += 1
            hour_counts[dt.hour] += 1
            event_dates.add(dt.strftime("%Y-%m-%d"))

        if most_recent_event:
            days_since = (now - most_recent_event).days
            if days_since <= 7:
                status = "active"
            elif days_since <= 30:
                status = "moderate"
            elif days_since <= 90:
                status = "sporadic"
            else:
                status = "dormant"
        else:
            recent_pushes = []
            for r in repos:
                if r.pushed_at:
                    try:
                        pushed = datetime.fromisoformat(r.pushed_at.replace("Z", "+00:00"))
                        recent_pushes.append(pushed)
                    except (ValueError, AttributeError):
                        pass
            if recent_pushes:
                latest = max(recent_pushes)
                days_since = (now - latest).days
                if days_since <= 30:
                    status = "moderate"
                elif days_since <= 90:
                    status = "sporadic"
                else:
                    status = "dormant"
            else:
                status = "dormant"

        peak_hours = [h for h, _ in hour_counts.most_common(3)]

        tz_estimate = None
        if peak_hours:
            avg_peak = sum(peak_hours) / len(peak_hours)
            offset = int(round(14 - avg_peak))
            offset = max(-12, min(12, offset))
            tz_estimate = f"UTC+{offset}" if offset >= 0 else f"UTC{offset}"

        commits_estimate = await _estimate_commits(client, user, repos, push_events, now)

        active_day_count, longest_gap = _compute_gaps(event_dates)

        has_heatmap = any(any(row) for row in heatmap)
        score, description = _compute_consistency(
            heatmap if has_heatmap else None, status, active_day_count, longest_gap,
        )

        return Activity(
            status=status,
            commits_last_year=commits_estimate,
            peak_hours=peak_hours,
            timezone_estimate=tz_estimate,
            heatmap=heatmap if has_heatmap else None,
            consistency_score=score,
            consistency_description=description,
            longest_gap_days=longest_gap if event_dates else None,
            active_days=active_day_count if event_dates else None,
        )
    except Exception:
        logger.warning("Failed to extract activity for %s", user.login, exc_info=True)
        return None


async def _estimate_commits(
    client: GitHubClient,
    user: GitHubUser,
    repos: list[GitHubRepo],
    push_events: list,
    now: datetime,
) -> int | None:
    one_year_ago = (now - timedelta(days=365)).strftime("%Y-%m-%d")
    if client is not None:
        search_count = await client.search_user_commit_count(user.login, one_year_ago)
        if search_count is not None:
            return search_count

    active_repos = [r for r in repos if r.pushed_at]
    if active_repos:
        recent_count = sum(1 for r in active_repos if _days_since_push(r, now) < 365)
        if push_events:
            total_commits = sum(e.payload.get("size", 1) for e in push_events)
            earliest = min(
                datetime.fromisoformat(e.created_at.replace("Z", "+00:00"))
                for e in push_events
            )
            days_span = max((now - earliest).days, 1)
            return int(total_commits / days_span * 365)
        if recent_count > 0:
            return recent_count * 30
    return None


def _compute_gaps(event_dates: set[str]) -> tuple[int, int]:
    if not event_dates:
        return 0, 0
    sorted_dates = sorted(datetime.strptime(d, "%Y-%m-%d").date() for d in event_dates)
    active_day_count = len(sorted_dates)
    longest_gap = 0
    for i in range(1, len(sorted_dates)):
        gap = (sorted_dates[i] - sorted_dates[i - 1]).days
        if gap > longest_gap:
            longest_gap = gap
    return active_day_count, longest_gap


def _compute_consistency(
    heatmap: list[list[int]] | None,
    status: str,
    active_day_count: int = 0,
    longest_gap: int = 0,
) -> tuple[int, str]:
    if not heatmap:
        fallback_scores = {"active": 70, "moderate": 50, "sporadic": 25, "dormant": 0}
        score = fallback_scores.get(status, 0)
        return score, f"{status} (no detailed data)"

    day_totals = [sum(row) for row in heatmap]
    if max(day_totals) == 0:
        return 0, "no activity detected"

    active_dow_count = sum(1 for t in day_totals if t > 0)
    dow_coverage = active_dow_count / 7

    active_totals = [t for t in day_totals if t > 0]
    if len(active_totals) > 1:
        cv = statistics.stdev(active_totals) / statistics.mean(active_totals)
    else:
        cv = 0.0
    evenness = max(0.0, 1.0 - cv)

    gap_penalty = 0
    if longest_gap >= 7:
        gap_penalty = min(30, longest_gap * 2)

    base_score = int(dow_coverage * 60 + evenness * dow_coverage * 25)
    density_bonus = min(15, active_day_count) if active_day_count > 0 else 0
    score = max(0, min(100, base_score + density_bonus - gap_penalty))

    active_days_list = [i for i in range(7) if day_totals[i] > 0]
    peak_days = sorted(active_days_list, key=lambda i: day_totals[i], reverse=True)[:2]
    peak_day_names = " & ".join(_DAY_NAMES[d] for d in sorted(peak_days))

    if score >= 70:
        label = "steady"
    elif score >= 40:
        label = "moderate"
    else:
        label = "bursty"

    parts = [label]
    if peak_day_names:
        parts.append(f"heavy {peak_day_names}")
    if longest_gap >= 5:
        parts.append(f"{longest_gap}-day gap")
    if active_day_count > 0:
        parts.append(f"{active_day_count} active days")

    return score, ", ".join(parts)


def heatmap_sparkline(heatmap: list[list[int]] | None) -> str:
    if not heatmap:
        return ""
    day_totals = [sum(row) for row in heatmap]
    max_val = max(day_totals) if day_totals else 0
    if max_val == 0:
        return " ".join(f"{d} {_SPARKLINE_CHARS[0]}" for d in _DAY_NAMES)
    chars = []
    for i, total in enumerate(day_totals):
        idx = int(total / max_val * (len(_SPARKLINE_CHARS) - 1))
        chars.append(f"{_DAY_NAMES[i]}{_SPARKLINE_CHARS[idx]}")
    return " ".join(chars)


def _days_since_push(repo: GitHubRepo, now: datetime) -> int:
    if not repo.pushed_at:
        return 9999
    try:
        pushed = datetime.fromisoformat(repo.pushed_at.replace("Z", "+00:00"))
        return (now - pushed).days
    except (ValueError, AttributeError):
        return 9999
