from __future__ import annotations

import logging

from devcard.github.client import GitHubClient
from devcard.github.models import GitHubRepo, GitHubUser
from devcard.models import Responsiveness

logger = logging.getLogger(__name__)


async def extract_responsiveness(
    client: GitHubClient,
    user: GitHubUser,
    repos: list[GitHubRepo],
    **kwargs,
) -> Responsiveness | None:
    """Extract community engagement metrics from the events feed.

    Counts issue comments and PR review comments. Zero extra API calls
    when events are passed via kwargs.
    """
    try:
        events = kwargs.get("events", [])

        issue_comments = 0
        pr_comment_count = 0

        for event in events:
            if event.type == "IssueCommentEvent":
                issue_comments += 1
            elif event.type == "PullRequestReviewCommentEvent":
                pr_comment_count += 1

        if issue_comments == 0 and pr_comment_count == 0:
            return None

        return Responsiveness(
            issue_comments=issue_comments,
            pr_comment_count=pr_comment_count,
            avg_response_hours=None,
        )
    except Exception:
        logger.warning(
            "Failed to extract responsiveness for %s",
            user.login,
            exc_info=True,
        )
        return None
