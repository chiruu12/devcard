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

    return json.dumps({
        user1: c1,
        user2: c2,
        "comparison": {
            "shared_languages": sorted(l1 & l2),
            "shared_stack": sorted(s1 & s2),
            f"{user1}_only_stack": sorted(s1 - s2),
            f"{user2}_only_stack": sorted(s2 - s1),
        },
    }, indent=2, default=str)


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


def main():
    mcp.run()
