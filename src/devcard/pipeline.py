from __future__ import annotations

import logging
from datetime import datetime, timezone

from devcard.config import DevCardConfig
from devcard.extractors.identity import extract_identity
from devcard.github.client import GitHubClient
from devcard.models import DevCard, Generator

logger = logging.getLogger(__name__)

DEVCARD_VERSION = "0.1.0"


async def generate_devcard(username: str, config: DevCardConfig) -> DevCard:
    client = GitHubClient(config)
    try:
        user = await client.get_user(username)
        repos = await client.get_repos(username)
        logger.info("Fetched %d repos for %s", len(repos), username)

        identity = await extract_identity(client, user, repos)
        if identity is None:
            raise RuntimeError(f"Failed to extract identity for {username}")

        return DevCard(
            generated_at=datetime.now(timezone.utc),
            generator=Generator(
                name="devcard",
                version=DEVCARD_VERSION,
            ),
            identity=identity,
        )
    finally:
        await client.close()
