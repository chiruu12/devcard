from __future__ import annotations

import asyncio
import base64
import json
import logging
import re
import tomllib

from devcard.github.client import GitHubClient, GitHubAPIError
from devcard.github.models import GitHubContent, GitHubRepo, GitHubUser
from devcard.mappings import DEPENDENCIES
from devcard.models import Stack, StackItem

logger = logging.getLogger(__name__)


def _parse_package_json(content: str) -> list[str]:
    try:
        data = json.loads(content)
        deps = set()
        for key in ("dependencies", "devDependencies"):
            for pkg in data.get(key, {}):
                name = pkg.split("/")[-1] if pkg.startswith("@") else pkg
                deps.add(name)
        return list(deps)
    except (json.JSONDecodeError, AttributeError):
        return []


def _parse_requirements_txt(content: str) -> list[str]:
    pkgs = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        name = re.split(r"[><=!~\[]", line)[0].strip()
        if name:
            pkgs.append(name.lower())
    return pkgs


def _parse_pyproject_toml(content: str) -> list[str]:
    try:
        data = tomllib.loads(content)
    except Exception:
        return []

    pkgs = []
    for dep in data.get("project", {}).get("dependencies", []):
        name = re.split(r"[><=!~\[; ]", dep)[0].strip()
        if name:
            pkgs.append(name.lower())

    poetry_deps = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
    for name in poetry_deps:
        if name.lower() != "python":
            pkgs.append(name.lower())

    pdm_deps = data.get("tool", {}).get("pdm", {}).get("dependencies", {})
    for name in pdm_deps:
        pkgs.append(name.lower())

    return pkgs


def _parse_go_mod(content: str) -> list[str]:
    pkgs = []
    in_require = False
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("require ("):
            in_require = True
            continue
        if in_require and line == ")":
            in_require = False
            continue
        if in_require and line:
            parts = line.split()
            if parts:
                module = parts[0]
                name = module.split("/")[-1]
                pkgs.append(name)
        elif line.startswith("require "):
            parts = line.split()
            if len(parts) >= 2:
                name = parts[1].split("/")[-1]
                pkgs.append(name)
    return pkgs


def _parse_cargo_toml(content: str) -> list[str]:
    try:
        data = tomllib.loads(content)
    except Exception:
        return []
    pkgs = []
    for section in ("dependencies", "dev-dependencies", "build-dependencies"):
        for name in data.get(section, {}):
            pkgs.append(name)
    return pkgs


def _parse_gemfile(content: str) -> list[str]:
    pkgs = []
    for match in re.finditer(r'''gem\s+['"]([^'"]+)['"]''', content):
        pkgs.append(match.group(1))
    return pkgs


def _parse_pom_xml(content: str) -> list[str]:
    return re.findall(r"<artifactId>([^<]+)</artifactId>", content)


def _parse_composer_json(content: str) -> list[str]:
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, AttributeError):
        return []
    pkgs = []
    for key in ("require", "require-dev"):
        for name in data.get(key, {}):
            if name == "php" or name.startswith("ext-"):
                continue
            short = name.split("/")[-1]
            pkgs.append(short)
    return pkgs


DEP_FILE_PARSERS: dict[str, callable] = {
    "package.json": _parse_package_json,
    "requirements.txt": _parse_requirements_txt,
    "pyproject.toml": _parse_pyproject_toml,
    "go.mod": _parse_go_mod,
    "Cargo.toml": _parse_cargo_toml,
    "Gemfile": _parse_gemfile,
    "pom.xml": _parse_pom_xml,
    "composer.json": _parse_composer_json,
}

CATEGORY_TO_FIELD = {
    "framework": "frameworks",
    "library": "libraries",
    "database": "databases",
    "tool": "tools",
    "platform": "platforms",
    "ci_cd": "ci_cd",
    "testing": "testing",
    "other": "other",
}


async def extract_stack(
    client: GitHubClient,
    user: GitHubUser,
    repos: list[GitHubRepo],
    *,
    root_listings: dict[str, list[GitHubContent]] | None = None,
    **kwargs,
) -> Stack | None:
    try:
        non_fork = [r for r in repos if not r.fork]
        if not non_fork:
            return None

        if root_listings is None:
            root_listings = await _fetch_root_listings(client, user.login, non_fork)

        all_items: dict[str, StackItem] = {}

        for repo in non_fork:
            listing = root_listings.get(repo.name, [])
            file_names = {item.name for item in listing}

            dep_files = [f for f in DEP_FILE_PARSERS if f in file_names]
            if not dep_files:
                continue

            fetch_tasks = [
                _fetch_and_parse(client, user.login, repo.name, filename)
                for filename in dep_files
            ]
            results = await asyncio.gather(*fetch_tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    continue
                for pkg_name in result:
                    pkg_lower = pkg_name.lower()
                    if pkg_lower in DEPENDENCIES and pkg_lower not in all_items:
                        mapping = DEPENDENCIES[pkg_lower]
                        all_items[pkg_lower] = StackItem(
                            name=mapping["name"],
                            category=mapping["category"],
                            source=repo.name,
                        )

        if not all_items:
            return None

        grouped: dict[str, list[StackItem]] = {f: [] for f in CATEGORY_TO_FIELD.values()}
        for item in all_items.values():
            field = CATEGORY_TO_FIELD.get(item.category, "other")
            grouped[field].append(item)

        return Stack(**grouped)
    except Exception:
        logger.warning("Failed to extract stack for %s", user.login, exc_info=True)
        return None


async def _fetch_and_parse(
    client: GitHubClient, owner: str, repo: str, filename: str
) -> list[str]:
    try:
        contents = await client.get_repo_contents(owner, repo, filename)
        if not contents:
            return []
        item = contents[0]
        if not item.content:
            return []
        decoded = base64.b64decode(item.content).decode("utf-8")
        parser = DEP_FILE_PARSERS.get(filename)
        if parser:
            return parser(decoded)
    except (GitHubAPIError, Exception):
        logger.warning("Failed to parse %s from %s/%s", filename, owner, repo)
    return []


async def _fetch_root_listings(
    client: GitHubClient, owner: str, repos: list[GitHubRepo]
) -> dict[str, list[GitHubContent]]:
    async def _fetch_one(repo_name: str) -> tuple[str, list[GitHubContent]]:
        try:
            return repo_name, await client.get_repo_contents(owner, repo_name)
        except Exception:
            return repo_name, []

    results = await asyncio.gather(*[_fetch_one(r.name) for r in repos])
    return dict(results)
