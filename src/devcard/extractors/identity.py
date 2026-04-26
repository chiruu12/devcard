from __future__ import annotations

import logging

from devcard.github.client import GitHubClient
from devcard.github.models import GitHubRepo, GitHubUser
from devcard.models import Identity

logger = logging.getLogger(__name__)


async def extract_identity(
    client: GitHubClient,
    user: GitHubUser,
    repos: list[GitHubRepo],
    **kwargs,
) -> Identity | None:
    try:
        return Identity(
            username=user.login,
            name=user.name,
            bio=user.bio,
            avatar_url=user.avatar_url,
            location=user.location,
            company=user.company,
            blog=user.blog,
            twitter_username=user.twitter_username,
            hireable=user.hireable,
            public_repos=user.public_repos,
            public_gists=user.public_gists,
            followers=user.followers,
            following=user.following,
            created_at=user.created_at,
        )
    except Exception:
        logger.warning("Failed to extract identity for %s", user.login, exc_info=True)
        return None
