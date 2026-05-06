from __future__ import annotations

import logging
import re

from devcard.github.client import GitHubClient
from devcard.github.models import GitHubRepo, GitHubUser
from devcard.models import CommitQuality

logger = logging.getLogger(__name__)

_CONVENTIONAL_RE = re.compile(
    r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(.+\))?!?:"
)


async def extract_commit_quality(
    client: GitHubClient,
    user: GitHubUser,
    repos: list[GitHubRepo],
    **kwargs,
) -> CommitQuality | None:
    try:
        events = kwargs.get("events", [])

        messages: list[str] = []
        for event in events:
            if event.type != "PushEvent":
                continue
            for commit in event.payload.get("commits", []):
                msg = commit.get("message", "")
                if msg.startswith("Merge "):
                    continue
                messages.append(msg)

        if not messages:
            return None

        commits_analyzed = len(messages)
        avg_message_length = sum(len(m) for m in messages) / commits_analyzed
        conventional_count = sum(1 for m in messages if _CONVENTIONAL_RE.match(m))
        multiline_count = sum(1 for m in messages if "\n" in m)

        return CommitQuality(
            avg_message_length=round(avg_message_length, 1),
            conventional_commits_pct=round(conventional_count / commits_analyzed * 100, 1),
            multiline_pct=round(multiline_count / commits_analyzed * 100, 1),
            commits_analyzed=commits_analyzed,
        )
    except Exception:
        logger.warning(
            "Failed to extract commit quality for %s",
            user.login,
            exc_info=True,
        )
        return None
