from __future__ import annotations

import asyncio
import logging

from devcard.github.client import GitHubClient
from devcard.github.models import GitHubRepo, GitHubUser
from devcard.models import LinesChanged, RepoLines

logger = logging.getLogger(__name__)

MAX_REPOS = 10


async def extract_lines_changed(
    client: GitHubClient,
    user: GitHubUser,
    repos: list[GitHubRepo],
    **kwargs,
) -> LinesChanged | None:
    """Extract lines added/deleted across a user's top repos."""
    try:
        non_fork_repos = [r for r in repos if not r.fork][:MAX_REPOS]

        if not non_fork_repos:
            return None

        stats_results = await asyncio.gather(
            *(
                client.get_contributor_stats(user.login, repo.name)
                for repo in non_fork_repos
            ),
            return_exceptions=True,
        )

        by_repo: list[RepoLines] = []

        for repo, stats in zip(non_fork_repos, stats_results):
            if isinstance(stats, Exception):
                logger.warning(
                    "Failed to fetch contributor stats for %s/%s",
                    user.login, repo.name,
                )
                continue

            if not stats:
                continue

            contributor = None
            for entry in stats:
                author = entry.get("author")
                if author is None:
                    continue
                if author.get("login", "").lower() == user.login.lower():
                    contributor = entry
                    break

            if contributor is None:
                continue

            weeks = contributor.get("weeks", [])
            added = sum(w.get("a", 0) for w in weeks)
            deleted = sum(w.get("d", 0) for w in weeks)

            if added + deleted > 0:
                by_repo.append(RepoLines(
                    repo=repo.name,
                    added=added,
                    deleted=deleted,
                ))

        by_repo.sort(key=lambda r: r.added + r.deleted, reverse=True)

        total_added = sum(r.added for r in by_repo)
        total_deleted = sum(r.deleted for r in by_repo)

        if total_added + total_deleted == 0:
            logger.warning(
                "No line stats available for %s (GitHub may still be computing — try again in 30s)",
                user.login,
            )
            return None

        return LinesChanged(
            total_added=total_added,
            total_deleted=total_deleted,
            by_repo=by_repo,
        )
    except Exception:
        logger.warning(
            "Failed to extract lines changed for %s",
            user.login, exc_info=True,
        )
        return None
