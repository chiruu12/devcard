from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from devcard.analyzers.contribution_style import analyze_contribution_style
from devcard.analyzers.developer_type import analyze_developer_type
from devcard.analyzers.project_classifier import classify_projects
from devcard.analyzers.scoring import compute_quality_score
from devcard.config import DevCardConfig
from devcard.extractors.activity import extract_activity
from devcard.extractors.collaboration import extract_collaboration
from devcard.extractors.expertise import extract_expertise
from devcard.extractors.identity import extract_identity
from devcard.extractors.languages import extract_languages
from devcard.extractors.projects import extract_projects
from devcard.extractors.quality import extract_quality
from devcard.extractors.stack import extract_stack
from devcard.github.client import GitHubClient
from devcard.github.models import GitHubContent
from devcard.models import DevCard, Generator

logger = logging.getLogger(__name__)

DEVCARD_VERSION = "0.1.0"


async def _fetch_root_listings(
    client: GitHubClient, owner: str, repos: list,
) -> dict[str, list[GitHubContent]]:
    async def _fetch_one(repo_name: str) -> tuple[str, list[GitHubContent]]:
        try:
            return repo_name, await client.get_repo_contents(owner, repo_name)
        except Exception:
            logger.warning("Failed to fetch root listing for %s/%s", owner, repo_name)
            return repo_name, []

    non_fork = [r for r in repos if not r.fork]
    results = await asyncio.gather(*[_fetch_one(r.name) for r in non_fork])
    return dict(results)


async def generate_devcard(username: str, config: DevCardConfig) -> DevCard:
    client = GitHubClient(config)
    try:
        user = await client.get_user(username)
        repos = await client.get_repos(username)
        logger.info("Fetched %d repos for %s", len(repos), username)

        root_listings = await _fetch_root_listings(client, username, repos)

        identity_result, languages_result, activity_result, projects_result, \
            collaboration_result, quality_result, stack_result = await asyncio.gather(
                extract_identity(client, user, repos),
                extract_languages(client, user, repos),
                extract_activity(client, user, repos),
                extract_projects(client, user, repos),
                extract_collaboration(client, user, repos),
                extract_quality(client, user, repos, root_listings=root_listings),
                extract_stack(client, user, repos, root_listings=root_listings),
            )

        if identity_result is None:
            raise RuntimeError(f"Failed to extract identity for {username}")

        expertise_result = await extract_expertise(
            client, user, repos,
            languages=languages_result,
            stack=stack_result,
        )

        devcard = DevCard(
            generated_at=datetime.now(timezone.utc),
            generator=Generator(name="devcard", version=DEVCARD_VERSION),
            identity=identity_result,
            languages=languages_result or [],
            stack=stack_result,
            activity=activity_result,
            projects=projects_result or [],
            collaboration=collaboration_result,
            quality=quality_result,
            expertise=expertise_result,
        )

        devcard.expertise.profile_type = analyze_developer_type(devcard) if devcard.expertise else None
        classify_projects(devcard)
        if devcard.collaboration:
            devcard.collaboration.contribution_style = analyze_contribution_style(devcard)
        compute_quality_score(devcard)

        return devcard
    finally:
        await client.close()
