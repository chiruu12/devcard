from __future__ import annotations

import asyncio
import logging
from fnmatch import fnmatch

from devcard.github.client import GitHubClient
from devcard.github.models import GitHubContent, GitHubRepo, GitHubUser
from devcard.mappings import FILE_PATTERNS
from devcard.models import Quality, QualityDetail

logger = logging.getLogger(__name__)


async def extract_quality(
    client: GitHubClient,
    user: GitHubUser,
    repos: list[GitHubRepo],
    *,
    root_listings: dict[str, list[GitHubContent]] | None = None,
    **kwargs,
) -> Quality | None:
    try:
        non_fork = [r for r in repos if not r.fork]
        if not non_fork:
            return None

        if root_listings is None:
            async def _fetch(name: str) -> tuple[str, list[GitHubContent]]:
                try:
                    return name, await client.get_repo_contents(user.login, name)
                except Exception:
                    return name, []

            results = await asyncio.gather(*[_fetch(r.name) for r in non_fork])
            root_listings = dict(results)

        signal_counts: dict[str, int] = {
            "ci": 0, "testing": 0, "docs": 0, "license": 0, "linting": 0,
        }
        details: list[QualityDetail] = []

        for repo in non_fork:
            listing = root_listings.get(repo.name, [])
            names = {item.name for item in listing}
            found_signals: list[str] = []

            for signal_type, patterns in FILE_PATTERNS.items():
                if signal_type not in signal_counts:
                    continue
                for pattern in patterns:
                    if any(fnmatch(name, pattern) or name == pattern for name in names):
                        signal_counts[signal_type] += 1
                        found_signals.append(signal_type)
                        break

            if found_signals:
                details.append(QualityDetail(repo=repo.name, signals=found_signals))

        total = len(non_fork)
        ci = signal_counts["ci"] / total
        test = signal_counts["testing"] / total
        docs = signal_counts["docs"] / total
        lic = signal_counts["license"] / total
        lint = signal_counts["linting"] / total

        score = round(test * 0.3 + ci * 0.25 + docs * 0.2 + lic * 0.15 + lint * 0.1, 3)

        return Quality(
            score=score,
            ci_adoption=round(ci, 3),
            test_adoption=round(test, 3),
            docs_adoption=round(docs, 3),
            license_adoption=round(lic, 3),
            linter_adoption=round(lint, 3),
            details=details,
        )
    except Exception:
        logger.warning("Failed to extract quality for %s", user.login, exc_info=True)
        return None


