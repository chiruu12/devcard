from __future__ import annotations

import logging

from devcard.github.client import GitHubClient
from devcard.github.models import GitHubRepo, GitHubUser
from devcard.models import Collaboration

logger = logging.getLogger(__name__)


async def extract_collaboration(
    client: GitHubClient,
    user: GitHubUser,
    repos: list[GitHubRepo],
    **kwargs,
) -> Collaboration | None:
    try:
        events = kwargs.get("events") or await client.get_user_events(user.login)
        orgs = await client.get_user_orgs(user.login)

        pr_count = 0
        issue_count = 0
        external_count = 0

        for event in events:
            repo_name = event.repo.get("name", "")
            is_external = "/" in repo_name and not repo_name.startswith(f"{user.login}/")

            if event.type == "PullRequestEvent":
                action = event.payload.get("action", "")
                if action == "opened":
                    pr_count += 1
                    if is_external:
                        external_count += 1
            elif event.type == "IssuesEvent":
                action = event.payload.get("action", "")
                if action == "opened":
                    issue_count += 1
                    if is_external:
                        external_count += 1

        return Collaboration(
            organizations=orgs,
            pull_requests_opened=pr_count,
            issues_opened=issue_count,
            external_contributions=external_count,
        )
    except Exception:
        logger.warning("Failed to extract collaboration for %s", user.login, exc_info=True)
        return None
