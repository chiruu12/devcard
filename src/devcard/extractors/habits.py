from __future__ import annotations

import asyncio
import logging

from devcard.github.client import GitHubClient
from devcard.github.models import GitHubRepo, GitHubUser
from devcard.models import CodingHabits

logger = logging.getLogger(__name__)

MAX_COMMITS = 10


async def extract_coding_habits(
    client: GitHubClient,
    user: GitHubUser,
    repos: list[GitHubRepo],
    **kwargs,
) -> CodingHabits | None:
    try:
        events = kwargs.get("events", [])

        commit_refs: list[tuple[str, str, str]] = []  # (owner, repo, sha)
        for event in events:
            if event.type != "PushEvent":
                continue
            repo_name = event.repo.get("name", "")
            if "/" not in repo_name:
                continue
            owner, repo = repo_name.split("/", 1)

            commits = event.payload.get("commits", [])
            if commits:
                for commit in commits:
                    sha = commit.get("sha")
                    if sha:
                        commit_refs.append((owner, repo, sha))
                    if len(commit_refs) >= MAX_COMMITS:
                        break
            else:
                head_sha = event.payload.get("head")
                if head_sha:
                    commit_refs.append((owner, repo, head_sha))

            if len(commit_refs) >= MAX_COMMITS:
                break

        if not commit_refs:
            return None

        # Fetch commit details concurrently
        results = await asyncio.gather(
            *(
                client.get_commit_detail(owner, repo, sha)
                for owner, repo, sha in commit_refs
            ),
            return_exceptions=True,
        )

        spaces_count = 0
        tabs_count = 0
        total_line_length = 0
        lines_analyzed = 0

        for result in results:
            if isinstance(result, BaseException) or result is None:
                continue
            files = result.get("files")
            if not files:
                continue
            for file_entry in files:
                patch = file_entry.get("patch")
                if not patch:
                    continue
                for line in patch.splitlines():
                    if not line.startswith("+"):
                        continue
                    # Skip the unified diff header line (e.g. +++ b/file.py)
                    if line.startswith("+++"):
                        continue
                    # Strip the leading '+' to get the actual code line
                    code_line = line[1:]
                    lines_analyzed += 1
                    total_line_length += len(code_line)

                    if code_line.startswith("\t"):
                        tabs_count += 1
                    elif code_line.startswith("  "):
                        spaces_count += 1

        if lines_analyzed == 0:
            return None

        # Determine indentation style
        if tabs_count > 0 and spaces_count > 0:
            indentation = "mixed"
        elif tabs_count > 0:
            indentation = "tabs"
        elif spaces_count > 0:
            indentation = "spaces"
        else:
            indentation = None

        avg_line_length = total_line_length / lines_analyzed

        return CodingHabits(
            indentation=indentation,
            spaces_count=spaces_count,
            tabs_count=tabs_count,
            avg_line_length=round(avg_line_length, 1),
            lines_analyzed=lines_analyzed,
        )
    except Exception:
        logger.warning(
            "Failed to extract coding habits for %s",
            user.login,
            exc_info=True,
        )
        return None
