from __future__ import annotations

import asyncio
import logging

from devcard.github.client import GitHubClient
from devcard.github.models import GitHubRepo, GitHubUser
from devcard.models import Language

logger = logging.getLogger(__name__)

LINGUIST_COLORS: dict[str, str] = {
    "Assembly": "#6E4C13",
    "C": "#555555",
    "C#": "#178600",
    "C++": "#f34b7d",
    "CSS": "#563d7c",
    "Clojure": "#db5855",
    "Dart": "#00B4AB",
    "Elixir": "#6e4a7e",
    "Go": "#00ADD8",
    "HTML": "#e34c26",
    "Haskell": "#5e5086",
    "Java": "#b07219",
    "JavaScript": "#f1e05a",
    "Jupyter Notebook": "#DA5B0B",
    "Kotlin": "#A97BFF",
    "Lua": "#000080",
    "Makefile": "#427819",
    "Objective-C": "#438eff",
    "PHP": "#4F5D95",
    "Perl": "#0298c3",
    "Python": "#3572A5",
    "R": "#198CE7",
    "Ruby": "#701516",
    "Rust": "#dea584",
    "Scala": "#c22d40",
    "Shell": "#89e051",
    "Swift": "#F05138",
    "TypeScript": "#3178c6",
    "Vue": "#41b883",
    "Zig": "#ec915c",
}


LANGUAGE_BYTE_WEIGHTS: dict[str, float] = {
    "Jupyter Notebook": 0.05,
    "HTML": 0.1,
    "CSS": 0.1,
    "SCSS": 0.1,
    "Less": 0.1,
    "Roff": 0.0,
    "TeX": 0.1,
    "Dockerfile": 0.0,
    "Makefile": 0.2,
    "CMake": 0.2,
    "Batchfile": 0.2,
    "Procfile": 0.0,
}

LANGUAGE_CATEGORIES: dict[str, str] = {
    "HTML": "presentation",
    "CSS": "presentation",
    "SCSS": "presentation",
    "Less": "presentation",
    "Svelte": "presentation",
    "Vue": "presentation",
    "Jupyter Notebook": "data",
    "R": "data",
    "MATLAB": "data",
    "TeX": "markup",
    "Roff": "markup",
    "Markdown": "markup",
    "reStructuredText": "markup",
    "Dockerfile": "build",
    "Makefile": "build",
    "CMake": "build",
    "Batchfile": "build",
    "Shell": "build",
    "Procfile": "build",
    "Nix": "build",
}


def _classify_language(name: str) -> str:
    return LANGUAGE_CATEGORIES.get(name, "logic")


def compute_coding_ratio(languages: list[Language]) -> float:
    if not languages:
        return 0.0
    logic_pct = sum(
        lang.percentage for lang in languages
        if (lang.category or _classify_language(lang.name)) == "logic"
    )
    return round(logic_pct, 1)


async def extract_languages(
    client: GitHubClient,
    user: GitHubUser,
    repos: list[GitHubRepo],
    **kwargs,
) -> list[Language] | None:
    try:
        non_fork = [r for r in repos if not r.fork]
        tasks = [client.get_repo_languages(user.login, r.name) for r in non_fork]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        totals: dict[str, int] = {}
        for result in results:
            if isinstance(result, Exception):
                continue
            for lang, bytes_count in result.items():
                weight = LANGUAGE_BYTE_WEIGHTS.get(lang, 1.0)
                weighted = int(bytes_count * weight)
                totals[lang] = totals.get(lang, 0) + weighted

        if not totals:
            return None

        grand_total = sum(totals.values())
        languages = []
        for name, byte_count in sorted(totals.items(), key=lambda x: x[1], reverse=True):
            pct = round(byte_count / grand_total * 100, 1)
            if pct < 0.1:
                continue
            languages.append(Language(
                name=name,
                percentage=pct,
                color=LINGUIST_COLORS.get(name),
                bytes=byte_count,
                category=_classify_language(name),
            ))

        return languages or None
    except Exception:
        logger.warning("Failed to extract languages for %s", user.login, exc_info=True)
        return None
