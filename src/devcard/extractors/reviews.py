from __future__ import annotations

import logging

from devcard.github.client import GitHubClient
from devcard.github.models import GitHubRepo, GitHubUser
from devcard.models import ReviewActivity

logger = logging.getLogger(__name__)

KNOWN_REVIEW_STATES = {"approved", "changes_requested", "commented", "dismissed"}


async def extract_review_activity(
    client: GitHubClient,
    user: GitHubUser,
    repos: list[GitHubRepo],
    **kwargs,
) -> ReviewActivity | None:
    """Count PR review activity from the events feed.

    Pure event parsing — makes zero API calls.
    """
    try:
        events = kwargs.get("events", [])

        approved = 0
        changes_requested = 0
        commented = 0
        repos_reviewed: set[str] = set()

        for event in events:
            if event.type != "PullRequestReviewEvent":
                continue

            review = event.payload.get("review", {})
            state = review.get("state", "").lower() if isinstance(review, dict) else ""

            if state not in KNOWN_REVIEW_STATES:
                continue

            # Extract repo name safely
            repo_info = event.repo
            if isinstance(repo_info, dict):
                repo_name = repo_info.get("name", "")
            else:
                continue

            if state == "approved":
                approved += 1
            elif state == "changes_requested":
                changes_requested += 1
            elif state == "commented":
                commented += 1
            # "dismissed" is a known state but doesn't increment any counter

            if repo_name:
                repos_reviewed.add(repo_name)

        reviews_given = approved + changes_requested + commented
        if reviews_given == 0:
            return None

        return ReviewActivity(
            reviews_given=reviews_given,
            approved=approved,
            changes_requested=changes_requested,
            commented=commented,
            repos_reviewed=sorted(repos_reviewed),
        )
    except Exception:
        logger.warning(
            "Failed to extract review activity for %s",
            user.login,
            exc_info=True,
        )
        return None
