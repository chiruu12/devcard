from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from devcard.analyzers.contribution_style import analyze_contribution_style
from devcard.analyzers.developer_type import analyze_developer_type
from devcard.analyzers.issue_detector import detect_issues
from devcard.analyzers.project_classifier import classify_projects
from devcard.analyzers.scoring import (
    compute_agent_readiness_score,
    compute_human_visibility_score,
    compute_quality_score,
)
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
from devcard.models import AuditResult, DevCard, Generator, ProfileRepoData

logger = logging.getLogger(__name__)

DEVCARD_VERSION = "0.1.0"


def _generate_summary(devcard: DevCard) -> str:
    parts = []

    profile = (
        devcard.expertise.profile_type
        if devcard.expertise and devcard.expertise.profile_type
        else "developer"
    )
    _SPECIAL_CASE = {"ml": "ML", "devops": "DevOps", "full_stack": "Full Stack"}
    profile_display = _SPECIAL_CASE.get(profile, profile.replace("_", " ").title())

    skip_langs = {"Jupyter Notebook"}
    primary_lang = next(
        (lang.name for lang in devcard.languages if lang.name not in skip_langs),
        devcard.languages[0].name if devcard.languages else None,
    )

    if primary_lang:
        parts.append(f"{profile_display} specializing in {primary_lang}")
    else:
        parts.append(profile_display)

    top_projects = [
        p for p in devcard.projects[:2]
        if p.stars > 0 or p.description
    ]
    if top_projects:
        proj_strs = []
        for p in top_projects:
            desc = p.description or ""
            if desc and len(desc) < 60:
                proj_strs.append(f"{p.name} ({desc.rstrip('.')})")
            else:
                proj_strs.append(p.name)
        parts.append(f"Builds {', '.join(proj_strs)}")

    if devcard.collaboration and devcard.collaboration.org_contributions:
        top_org = devcard.collaboration.org_contributions[0]
        parts.append(
            f"Contributor at {top_org.org} ({top_org.prs_opened} PRs)"
        )

    if devcard.activity:
        status = devcard.activity.status.title()
        commits = devcard.activity.commits_last_year
        if commits:
            parts.append(f"{status}, ~{commits:,} commits/year")
        else:
            parts.append(status)

    return ". ".join(parts) + "."


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


async def generate_devcard(
    username: str, config: DevCardConfig, *, enrich: bool = False,
) -> DevCard:
    client = GitHubClient(config)
    try:
        user = await client.get_user(username)
        repos = await client.get_repos(username)
        logger.info("Fetched %d repos for %s", len(repos), username)

        root_listings = await _fetch_root_listings(client, username, repos)
        events_task = client.get_user_events(username)
        starred_task = client.get_starred_repos(username, limit=100)
        events, starred_repos = await asyncio.gather(events_task, starred_task)

        identity_result, languages_result, activity_result, projects_result, \
            collaboration_result, quality_result, stack_result = await asyncio.gather(
                extract_identity(client, user, repos),
                extract_languages(client, user, repos),
                extract_activity(client, user, repos, events=events),
                extract_projects(client, user, repos),
                extract_collaboration(client, user, repos, events=events),
                extract_quality(client, user, repos, root_listings=root_listings),
                extract_stack(client, user, repos, root_listings=root_listings),
            )

        if identity_result is None:
            raise RuntimeError(f"Failed to extract identity for {username}")

        expertise_result = await extract_expertise(
            client, user, repos,
            languages=languages_result,
            stack=stack_result,
            starred_repos=starred_repos,
            root_listings=root_listings,
        )

        devcard = DevCard(
            generated_at=datetime.now(UTC),
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

        if devcard.expertise:
            devcard.expertise.profile_type = analyze_developer_type(devcard)
        classify_projects(devcard)
        if devcard.collaboration:
            devcard.collaboration.contribution_style = analyze_contribution_style(devcard)
        compute_quality_score(devcard)
        devcard.summary = _generate_summary(devcard)

        if enrich and config.fireworks_api_key:
            from devcard.enrichment import enrich_devcard

            enriched = await enrich_devcard(devcard, config)
            if enriched:
                devcard.enriched = enriched
                logger.info("Enrichment complete for %s", username)

        return devcard
    finally:
        await client.close()


async def _fetch_profile_repo_data(client: GitHubClient, username: str) -> ProfileRepoData:
    """Fetch profile repo (username/username) data for scoring."""
    try:
        contents = await client.get_repo_contents(username, username)
        file_names = [c.name for c in contents]

        has_readme = any(c.name.lower() == "readme.md" for c in contents)
        readme_length = 0
        if has_readme:
            # Get readme content length (approximate from size field)
            readme_item = next(
                (c for c in contents if c.name.lower() == "readme.md"), None
            )
            if readme_item and readme_item.size:
                readme_length = readme_item.size

        return ProfileRepoData(
            has_profile_readme=has_readme,
            readme_length=readme_length,
            has_devcard_json="devcard.json" in file_names,
            has_llms_txt="llms.txt" in file_names,
            files=file_names,
        )
    except Exception:
        logger.warning("Could not fetch profile repo for %s", username)
        return ProfileRepoData()


async def audit_pipeline(username: str, config: DevCardConfig) -> AuditResult:
    """Audit a developer's GitHub profile — scoring + issue detection."""
    devcard = await generate_devcard(username, config)

    client = GitHubClient(config)
    try:
        profile = await _fetch_profile_repo_data(client, username)
    finally:
        await client.close()

    human_score = compute_human_visibility_score(devcard, profile)
    agent_score = compute_agent_readiness_score(devcard, profile)
    issues = detect_issues(devcard, profile)

    # Generate recommendations from issues
    recommendations = [issue.message for issue in issues[:5]]

    # Build summary stats
    total_repos = len(devcard.projects)
    summary = {
        "total_repos": total_repos,
        "repos_with_descriptions": sum(1 for p in devcard.projects if p.description),
        "repos_with_topics": sum(1 for p in devcard.projects if p.topics),
    }

    return AuditResult(
        username=username,
        human_visibility_score=human_score,
        agent_readiness_score=agent_score,
        issues=issues,
        recommendations=recommendations,
        summary=summary,
    )
