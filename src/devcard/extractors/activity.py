from __future__ import annotations

import logging
import statistics
from collections import Counter
from datetime import UTC, datetime

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

        for event in push_events:
            try:
                dt = datetime.fromisoformat(event.created_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                continue
            if most_recent_event is None or dt > most_recent_event:
                most_recent_event = dt
            heatmap[dt.weekday()][dt.hour] += 1
            hour_counts[dt.hour] += 1

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
            if offset >= 0:
                tz_estimate = f"UTC+{offset}"
            else:
                tz_estimate = f"UTC{offset}"

        commits_estimate = None
        active_repos = [r for r in repos if r.pushed_at]
        if active_repos:
            recent_count = sum(
                1
                for r in active_repos
                if _days_since_push(r, now) < 365
            )
            if push_events:
                total_commits = sum(
                    e.payload.get("size", 1) for e in push_events
                )
                earliest = min(
                    datetime.fromisoformat(e.created_at.replace("Z", "+00:00"))
                    for e in push_events
                )
                days_span = max((now - earliest).days, 1)
                commits_estimate = int(total_commits / days_span * 365)
            elif recent_count > 0:
                commits_estimate = recent_count * 30

        has_heatmap = any(any(row) for row in heatmap)
        score, description = _compute_consistency(
            heatmap if has_heatmap else None, status, peak_hours,
        )

        return Activity(
            status=status,
            commits_last_year=commits_estimate,
            peak_hours=peak_hours,
            timezone_estimate=tz_estimate,
            heatmap=heatmap if has_heatmap else None,
            consistency_score=score,
            consistency_description=description,
        )
    except Exception:
        logger.warning("Failed to extract activity for %s", user.login, exc_info=True)
        return None


def _compute_consistency(
    heatmap: list[list[int]] | None,
    status: str,
    peak_hours: list[int],
) -> tuple[int, str]:
    if not heatmap:
        fallback_scores = {"active": 70, "moderate": 50, "sporadic": 25, "dormant": 0}
        score = fallback_scores.get(status, 0)
        return score, f"{status} (no detailed data)"

    day_totals = [sum(row) for row in heatmap]
    if max(day_totals) == 0:
        return 0, "no activity detected"

    mean = statistics.mean(day_totals)
    stdev = statistics.stdev(day_totals) if len(day_totals) > 1 else 0.0
    cv = stdev / mean if mean > 0 else 1.0
    score = max(0, min(100, int((1 - cv) * 100)))

    peak_days = sorted(
        range(7), key=lambda i: day_totals[i], reverse=True,
    )[:2]
    peak_day_names = " & ".join(_DAY_NAMES[d] for d in sorted(peak_days))

    if score >= 70:
        label = "steady"
    elif score >= 40:
        label = "moderate"
    else:
        label = "bursty"

    return score, f"{label}, heavy {peak_day_names}"


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
