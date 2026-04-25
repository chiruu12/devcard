from __future__ import annotations

import logging
from collections import Counter
from datetime import UTC, datetime

from devcard.github.client import GitHubClient
from devcard.github.models import GitHubRepo, GitHubUser
from devcard.models import Activity

logger = logging.getLogger(__name__)


async def extract_activity(
    client: GitHubClient,
    user: GitHubUser,
    repos: list[GitHubRepo],
    **kwargs,
) -> Activity | None:
    try:
        events = kwargs.get("events") or await client.get_user_events(user.login)
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

        return Activity(
            status=status,
            commits_last_year=commits_estimate,
            peak_hours=peak_hours,
            timezone_estimate=tz_estimate,
            heatmap=heatmap if any(any(row) for row in heatmap) else None,
        )
    except Exception:
        logger.warning("Failed to extract activity for %s", user.login, exc_info=True)
        return None


def _days_since_push(repo: GitHubRepo, now: datetime) -> int:
    if not repo.pushed_at:
        return 9999
    try:
        pushed = datetime.fromisoformat(repo.pushed_at.replace("Z", "+00:00"))
        return (now - pushed).days
    except (ValueError, AttributeError):
        return 9999
