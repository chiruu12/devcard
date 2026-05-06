from __future__ import annotations

import asyncio
import logging

from devcard.github.client import GitHubClient
from devcard.github.models import GitHubRepo, GitHubUser
from devcard.models import NotableContribution

logger = logging.getLogger(__name__)

MIN_STARS = 1000
MAX_RESULTS = 10


async def extract_notable_contributions(
    client: GitHubClient,
    user: GitHubUser,
    repos: list[GitHubRepo],
    **kwargs,
) -> list[NotableContribution]:
    """Extract contributions to popular repos (1000+ stars) the user doesn't own.

    Combines two sources:
    1. Recent events (PushEvent/PullRequestEvent to external repos)
    2. Search API (merged PRs by the user across GitHub)
    """
    try:
        events = kwargs.get("events", [])
        username = user.login.lower()

        # Source 1: contributions from recent events
        event_repos = _extract_from_events(events, username)

        # Source 2: merged PRs from search API
        search_results = await client.search_user_merged_prs(user.login)
        search_repos: dict[str, int] = {}
        for item in search_results:
            repo_name = item["repo"]
            owner = repo_name.split("/")[0].lower() if "/" in repo_name else ""
            if owner != username:
                search_repos[repo_name] = item["merged_prs"]

        # Merge: deduplicate by repo, prefer search data for PR counts
        all_repos: dict[str, dict] = {}
        for repo_name, info in event_repos.items():
            all_repos[repo_name] = {
                "contribution_type": info["type"],
                "count": info["count"],
                "merged": None,
            }

        for repo_name, merged_count in search_repos.items():
            if repo_name in all_repos:
                all_repos[repo_name]["contribution_type"] = "pull_request"
                all_repos[repo_name]["merged"] = merged_count
                all_repos[repo_name]["count"] = max(
                    all_repos[repo_name]["count"], merged_count
                )
            else:
                all_repos[repo_name] = {
                    "contribution_type": "pull_request",
                    "count": merged_count,
                    "merged": merged_count,
                }

        if not all_repos:
            return []

        # Fetch repo info (stars, description) for candidates
        async def _fetch_info(repo_name: str) -> tuple[str, dict | None]:
            parts = repo_name.split("/")
            if len(parts) != 2:
                return repo_name, None
            return repo_name, await client.get_repo_info(parts[0], parts[1])

        info_results = await asyncio.gather(
            *[_fetch_info(name) for name in all_repos]
        )

        # Filter by star threshold and build results
        contributions: list[NotableContribution] = []
        for repo_name, info in info_results:
            if info is None:
                continue
            if info["stars"] < MIN_STARS:
                continue

            entry = all_repos[repo_name]
            contributions.append(NotableContribution(
                repo=repo_name,
                repo_stars=info["stars"],
                contribution_type=entry["contribution_type"],
                count=entry["count"],
                merged=entry.get("merged"),
                description=info.get("description"),
                url=info["html_url"],
            ))

        contributions.sort(key=lambda c: c.repo_stars, reverse=True)
        return contributions[:MAX_RESULTS]
    except Exception:
        logger.warning(
            "Failed to extract notable contributions for %s",
            user.login, exc_info=True,
        )
        return []


def _extract_from_events(
    events: list, username: str,
) -> dict[str, dict]:
    """Extract external repo contributions from events feed."""
    repos: dict[str, dict] = {}
    for event in events:
        repo_info = event.repo if hasattr(event, "repo") else {}
        if isinstance(repo_info, dict):
            repo_name = repo_info.get("name", "")
        else:
            repo_name = ""

        if not repo_name or "/" not in repo_name:
            continue

        owner = repo_name.split("/")[0].lower()
        if owner == username:
            continue

        if event.type == "PullRequestEvent":
            action = event.payload.get("action", "")
            if action == "opened":
                existing = repos.get(repo_name)
                if existing:
                    existing["count"] += 1
                else:
                    repos[repo_name] = {"type": "pull_request", "count": 1}

        elif event.type == "PushEvent":
            commit_count = event.payload.get("size", 1)
            existing = repos.get(repo_name)
            if existing:
                existing["count"] += commit_count
            else:
                repos[repo_name] = {"type": "commit", "count": commit_count}

        elif event.type == "IssuesEvent":
            action = event.payload.get("action", "")
            if action == "opened":
                existing = repos.get(repo_name)
                if existing:
                    existing["count"] += 1
                else:
                    repos[repo_name] = {"type": "issue", "count": 1}

    return repos
