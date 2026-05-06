"""DevCard MCP server — let AI agents query developer profiles."""
from __future__ import annotations

import asyncio
import json
import logging
import os

from devcard.config import DevCardConfig
from devcard.output.curated import curate_for_agent
from devcard.pipeline import generate_devcard
from fastmcp import FastMCP

from devcard_mcp.cache import DevCardCache

logger = logging.getLogger(__name__)

mcp = FastMCP(
    name="DevCard",
    instructions=(
        "DevCard generates structured developer identity cards from "
        "GitHub profiles. Use these tools to look up developers, "
        "compare profiles, and check technology stacks."
    ),
)

_cache = DevCardCache(ttl_seconds=1800)


def _get_config() -> DevCardConfig:
    return DevCardConfig.create(token=os.environ.get("GITHUB_TOKEN"))


async def _get_or_generate(username: str, force_refresh: bool = False):
    if not force_refresh:
        cached = _cache.get(username)
        if cached is not None:
            logger.debug("Cache hit for %s", username)
            return cached
    config = _get_config()
    devcard = await generate_devcard(username, config)
    _cache.set(username, devcard)
    return devcard


def _all_stack_names(devcard) -> set[str]:
    names: set[str] = set()
    if not devcard.stack:
        return names
    for field in ("frameworks", "libraries", "databases", "tools",
                  "platforms", "ci_cd", "testing", "other"):
        for item in getattr(devcard.stack, field, []):
            names.add(item.name)
    return names


def _build_stack_lookup(devcard) -> dict[str, dict]:
    lookup: dict[str, dict] = {}
    if not devcard.stack:
        return lookup
    for field in ("frameworks", "libraries", "databases", "tools",
                  "platforms", "ci_cd", "testing", "other"):
        for item in getattr(devcard.stack, field, []):
            lookup[item.name.lower()] = {
                "name": item.name,
                "category": item.category,
                "source": item.source,
            }
    return lookup


@mcp.tool()
async def get_devcard(username: str, force_refresh: bool = False) -> str:
    """Get a full DevCard for a GitHub user.

    Returns a structured JSON developer profile including identity,
    languages, tech stack, activity patterns, top projects, expertise
    domains, collaboration style, and quality scores.

    Results are cached for 30 minutes. Use force_refresh=True to bypass cache.
    """
    devcard = await _get_or_generate(username, force_refresh)
    return devcard.model_dump_json(indent=2, exclude_none=True)


@mcp.tool()
async def get_developer_summary(username: str) -> str:
    """Get a concise, agent-friendly summary of a GitHub developer.

    Returns curated highlights: identity, top languages with coding ratio,
    stack (frameworks/libraries/tools), expertise domains with confidence
    and skill levels, activity status with consistency score, and quality
    metrics. Lighter than get_devcard — use this for quick context.
    """
    devcard = await _get_or_generate(username)
    curated = curate_for_agent(devcard)
    return json.dumps(curated, indent=2, default=str)


@mcp.tool()
async def compare_developers(user1: str, user2: str) -> str:
    """Compare two GitHub developers side by side.

    Returns structured comparison including both developer summaries,
    shared and unique languages, shared and unique stack items
    (frameworks, libraries, tools), expertise domain overlap, and
    quality/activity metrics for both.
    """
    card1, card2 = await asyncio.gather(
        _get_or_generate(user1),
        _get_or_generate(user2),
    )
    c1 = curate_for_agent(card1)
    c2 = curate_for_agent(card2)

    s1 = _all_stack_names(card1)
    s2 = _all_stack_names(card2)

    l1 = {lang.name for lang in card1.languages}
    l2 = {lang.name for lang in card2.languages}

    result = {
        user1: c1,
        user2: c2,
        "comparison": {
            "shared_languages": sorted(l1 & l2),
            "shared_stack": sorted(s1 & s2),
            f"{user1}_only_stack": sorted(s1 - s2),
            f"{user2}_only_stack": sorted(s2 - s1),
        },
    }

    # Add scores for both users
    try:
        from devcard.analyzers.scoring import (
            compute_agent_readiness_score,
            compute_human_visibility_score,
        )
        from devcard.github.client import GitHubClient
        from devcard.pipeline import _fetch_profile_repo_data

        config = _get_config()
        client = GitHubClient(config)
        try:
            p1, p2 = await asyncio.gather(
                _fetch_profile_repo_data(client, user1),
                _fetch_profile_repo_data(client, user2),
            )
        finally:
            await client.close()

        result["scores"] = {
            user1: {
                "human_visibility": compute_human_visibility_score(card1, p1),
                "agent_readiness": compute_agent_readiness_score(card1, p1),
            },
            user2: {
                "human_visibility": compute_human_visibility_score(card2, p2),
                "agent_readiness": compute_agent_readiness_score(card2, p2),
            },
        }
    except Exception:
        logger.warning("Could not compute scores for comparison")

    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def check_developer_stack(
    username: str, technologies: list[str]
) -> str:
    """Check if a developer uses specific technologies.

    Pass a list of technology names (e.g. ["PyTorch", "React", "Docker"]).
    Returns which technologies were found in the developer's stack,
    which were not found, and details (category + source repo) for
    each match. Case-insensitive matching.
    """
    devcard = await _get_or_generate(username)
    stack_lookup = _build_stack_lookup(devcard)

    found: dict[str, dict] = {}
    not_found: list[str] = []
    for tech in technologies:
        match = stack_lookup.get(tech.lower())
        if match:
            found[match["name"]] = {
                "category": match["category"],
                "source": match.get("source"),
            }
        else:
            not_found.append(tech)

    return json.dumps({
        "username": username,
        "found": list(found.keys()),
        "not_found": not_found,
        "details": found,
    }, indent=2)


@mcp.tool()
async def audit_profile(username: str, token: str | None = None) -> str:
    """Audit a developer's GitHub profile for visibility and agent-readiness.

    Returns human visibility score (0-100), agent readiness score (0-100),
    detected issues with severity levels, and actionable recommendations.
    This is the entry point — use this to understand what needs fixing.
    """
    from devcard.pipeline import audit_pipeline

    config = _get_config()
    if token:
        config = DevCardConfig.create(token=token)
    result = await audit_pipeline(username, config)
    return result.model_dump_json(indent=2, exclude_none=True)


@mcp.tool()
async def analyze_repo(owner: str, repo: str, token: str | None = None) -> str:
    """Analyze a single GitHub repository in depth.

    Returns classification, primary language, detected issues,
    suggested description, and suggested topics.
    """
    from devcard.fixers.description_generator import generate_description
    from devcard.fixers.topic_suggester import suggest_topics

    config = _get_config()
    if token:
        config = DevCardConfig.create(token=token)

    from devcard.github.client import GitHubClient

    client = GitHubClient(config)
    try:
        repo_data = await client.get_repos(owner)
        target = next((r for r in repo_data if r.name == repo), None)
        if not target:
            return json.dumps({"error": f"Repository {owner}/{repo} not found"})

        topics = await client.get_repo_topics(owner, repo)

        repo_info = {
            "name": target.name,
            "language": target.language,
            "classification": None,
            "readme_first_paragraph": target.description,
            "stack": [],
            "readme_keywords": [],
            "existing_topics": topics,
        }

        from devcard.models import RepoAnalysis

        return RepoAnalysis(
            owner=owner,
            repo=repo,
            language=target.language,
            suggested_description=generate_description(repo_info),
            suggested_topics=suggest_topics(repo_info),
        ).model_dump_json(indent=2, exclude_none=True)
    finally:
        await client.close()


@mcp.tool()
async def fix_profile(
    username: str,
    token: str,
    fixes: list[str] | None = None,
    dry_run: bool = True,
) -> str:
    """Fix profile-level issues on GitHub.

    Fixes available: devcard_json, profile_readme, missing_descriptions,
    missing_topics, all. Use dry_run=True (default) to preview changes
    before applying. Requires a GitHub token with repo scope.
    """
    from devcard.pipeline import fix_profile_pipeline

    config = DevCardConfig.create(token=token)
    result = await fix_profile_pipeline(
        username,
        config,
        fixes or ["all"],
        dry_run,
    )
    return result.model_dump_json(indent=2, exclude_none=True)


@mcp.tool()
async def fix_repo(
    owner: str,
    repo: str,
    token: str,
    fixes: list[str] | None = None,
    dry_run: bool = True,
) -> str:
    """Fix issues on a specific GitHub repository.

    Fixes available: description, topics, agents_md, all.
    Use dry_run=True (default) to preview changes before applying.
    Requires a GitHub token with repo scope.
    """
    from devcard.pipeline import fix_repo_pipeline

    config = DevCardConfig.create(token=token)
    result = await fix_repo_pipeline(
        owner,
        repo,
        config,
        fixes or ["all"],
        dry_run,
    )
    return result.model_dump_json(indent=2, exclude_none=True)


@mcp.tool()
async def agent_ready(
    username: str,
    token: str,
    scope: str = "all",
) -> str:
    """Make a developer's GitHub profile fully agent-ready in one command.

    Runs a full audit, applies all fixes, then re-audits to show improvement.
    Scope options: all, profile, top_repos.
    Always previews first -- returns dry_run results. Call fix_profile or
    fix_repo with dry_run=False to apply.
    """
    from devcard.pipeline import audit_pipeline, fix_profile_pipeline

    config = DevCardConfig.create(token=token)

    # Before audit
    before = await audit_pipeline(username, config)

    # Preview all fixes
    fixes = await fix_profile_pipeline(
        username,
        config,
        ["all"],
        dry_run=True,
    )

    return json.dumps(
        {
            "before": {
                "human_visibility_score": before.human_visibility_score,
                "agent_readiness_score": before.agent_readiness_score,
            },
            "preview": json.loads(fixes.model_dump_json(exclude_none=True)),
            "message": (
                f"Found {len(before.issues)} issues. "
                f"Preview shows {len(fixes.changes)} fixes. "
                f"Use fix_profile with dry_run=False to apply."
            ),
        },
        indent=2,
    )


@mcp.tool()
async def render_card(
    username: str,
    theme: str = "default",
    force_refresh: bool = False,
) -> str:
    """Generate a visual SVG DevCard for a GitHub developer.

    Available themes: default, dark, minimal, neon, terminal_green.
    Returns the SVG content string and markdown embed code.
    The SVG is GitHub README-compatible (no foreignObject, no external resources).
    """
    from devcard.renderers.svg_card import render_svg

    devcard = await _get_or_generate(username, force_refresh)
    theme_obj = _load_theme(theme)
    svg = render_svg(devcard, theme=theme_obj)

    return json.dumps({
        "username": username,
        "theme": theme,
        "svg": svg,
        "embed_markdown": f"![DevCard for {username}](devcard.svg)",
        "size_bytes": len(svg.encode()),
    }, indent=2)


_THEMES = {
    "default": "devcard.renderers.themes.default",
    "dark": "devcard.renderers.themes.dark",
    "minimal": "devcard.renderers.themes.minimal",
    "neon": "devcard.renderers.themes.neon",
    "terminal_green": "devcard.renderers.themes.terminal_green",
}


def _load_theme(name: str):
    import importlib

    module_path = _THEMES.get(name)
    if module_path is None:
        module_path = _THEMES["default"]
    mod = importlib.import_module(module_path)
    return mod.THEME


def main():
    mcp.run()
