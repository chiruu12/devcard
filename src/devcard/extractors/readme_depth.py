from __future__ import annotations

import asyncio
import base64
import logging
import re

from devcard.github.client import GitHubClient
from devcard.github.models import GitHubContent, GitHubRepo, GitHubUser
from devcard.models import ReadmeDepth

logger = logging.getLogger(__name__)

_HEADING_RE = re.compile(r"^#{1,6}\s", re.MULTILINE)
_INSTALL_HEADING_RE = re.compile(
    r"^#{1,6}\s.*(install|getting\s+started|usage|setup|quick\s+start)",
    re.MULTILINE | re.IGNORECASE,
)
_IMAGE_RE = re.compile(r"!\[|shields\.io|img\.shields\.io")


def _analyze_readme(text: str) -> dict:
    """Analyze a single README's content and return per-file metrics."""
    return {
        "word_count": len(text.split()),
        "heading_count": len(_HEADING_RE.findall(text)),
        "has_code_blocks": "```" in text,
        "has_images": bool(_IMAGE_RE.search(text)),
        "has_install_section": bool(_INSTALL_HEADING_RE.search(text)),
    }


def _find_readme_in_listing(listing: list[GitHubContent]) -> bool:
    """Check if a README.md file exists in the root listing (case-insensitive)."""
    return any(item.name.lower() == "readme.md" for item in listing)


async def extract_readme_depth(
    client: GitHubClient,
    user: GitHubUser,
    repos: list[GitHubRepo],
    **kwargs,
) -> ReadmeDepth | None:
    try:
        root_listings: dict[str, list[GitHubContent]] = kwargs.get("root_listings", {})

        # Limit to first 10 repos (already sorted by stars)
        candidates = repos[:10]

        # Find repos that have a README.md in their root listing
        repos_with_readme = [
            repo for repo in candidates
            if _find_readme_in_listing(root_listings.get(repo.name, []))
        ]

        if not repos_with_readme:
            return None

        async def _fetch_readme(repo: GitHubRepo) -> dict | None:
            try:
                contents = await client.get_repo_contents(
                    user.login, repo.name, "README.md",
                )
                if not contents:
                    return None
                item = contents[0]
                if not item.content or item.encoding != "base64":
                    return None
                text = base64.b64decode(item.content).decode("utf-8", errors="replace")
                return _analyze_readme(text)
            except Exception:
                logger.warning(
                    "Failed to fetch README for %s/%s", user.login, repo.name,
                    exc_info=True,
                )
                return None

        results = await asyncio.gather(
            *[_fetch_readme(repo) for repo in repos_with_readme],
            return_exceptions=True,
        )

        analyses = [r for r in results if isinstance(r, dict)]

        if not analyses:
            return None

        count = len(analyses)
        avg_word_count = round(
            sum(a["word_count"] for a in analyses) / count, 1,
        )
        avg_heading_count = round(
            sum(a["heading_count"] for a in analyses) / count, 1,
        )
        has_code_blocks_pct = round(
            sum(1 for a in analyses if a["has_code_blocks"]) / count * 100, 1,
        )
        has_images_pct = round(
            sum(1 for a in analyses if a["has_images"]) / count * 100, 1,
        )
        has_install_section_pct = round(
            sum(1 for a in analyses if a["has_install_section"]) / count * 100, 1,
        )

        return ReadmeDepth(
            avg_word_count=avg_word_count,
            avg_heading_count=avg_heading_count,
            has_code_blocks_pct=has_code_blocks_pct,
            has_images_pct=has_images_pct,
            has_install_section_pct=has_install_section_pct,
            repos_analyzed=count,
        )
    except Exception:
        logger.warning(
            "Failed to extract readme depth for %s", user.login, exc_info=True,
        )
        return None
