from __future__ import annotations

import asyncio
import logging
import re

from devcard.github.client import GitHubClient
from devcard.github.models import GitHubRepo, GitHubUser
from devcard.models import CommitQuality

logger = logging.getLogger(__name__)

_CONVENTIONAL_RE = re.compile(
    r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(.+\))?!?:"
)
_MAX_HEAD_FETCHES = 15


async def extract_commit_quality(
    client: GitHubClient,
    user: GitHubUser,
    repos: list[GitHubRepo],
    **kwargs,
) -> CommitQuality | None:
    try:
        events = kwargs.get("events", [])

        messages: list[str] = []
        head_refs: list[tuple[str, str, str]] = []  # (owner, repo, sha)

        for event in events:
            if event.type != "PushEvent":
                continue
            commits = event.payload.get("commits", [])
            if commits:
                for commit in commits:
                    msg = commit.get("message", "").strip()
                    if not msg or msg.startswith("Merge "):
                        continue
                    messages.append(msg)
            else:
                head_sha = event.payload.get("head")
                repo_name = event.repo.get("name", "")
                if head_sha and "/" in repo_name and len(head_refs) < _MAX_HEAD_FETCHES:
                    owner, repo = repo_name.split("/", 1)
                    head_refs.append((owner, repo, head_sha))

        if head_refs:
            results = await asyncio.gather(
                *(client.get_commit_detail(o, r, s) for o, r, s in head_refs),
                return_exceptions=True,
            )
            for result in results:
                if isinstance(result, BaseException) or result is None:
                    continue
                commit_data = result.get("commit", {})
                msg = commit_data.get("message", "")
                if msg and not msg.startswith("Merge "):
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
