from __future__ import annotations

import logging

from devcard.github.client import GitHubClient
from devcard.github.models import GitHubRepo, GitHubUser
from devcard.models import Collaboration, OrgContribution

logger = logging.getLogger(__name__)


async def extract_collaboration(
    client: GitHubClient,
    user: GitHubUser,
    repos: list[GitHubRepo],
    **kwargs,
) -> Collaboration | None:
    try:
        events = kwargs.get("events")
        if events is None:
            events = await client.get_user_events(user.login)
        orgs = await client.get_user_orgs(user.login)

        pr_count = 0
        issue_count = 0
        external_count = 0

        for event in events:
            repo_name = event.repo.get("name", "")
            is_external = (
                "/" in repo_name
                and not repo_name.startswith(f"{user.login}/")
            )

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

        org_contribs: list[OrgContribution] = []
        for org in orgs:
            try:
                pr_data = await client.search_user_prs_in_org(user.login, org)
                org_issues = await client.search_user_issues_in_org(
                    user.login, org
                )
                if pr_data["total"] > 0 or org_issues > 0:
                    org_contribs.append(OrgContribution(
                        org=org,
                        prs_opened=pr_data["total"],
                        prs_merged=pr_data["merged"],
                        issues_opened=org_issues,
                    ))
            except Exception:
                logger.warning(
                    "Failed to fetch org contributions for %s/%s",
                    user.login, org,
                )

        return Collaboration(
            organizations=orgs,
            pull_requests_opened=pr_count,
            issues_opened=issue_count,
            external_contributions=external_count,
            org_contributions=org_contribs,
        )
    except Exception:
        logger.warning(
            "Failed to extract collaboration for %s",
            user.login, exc_info=True,
        )
        return None
