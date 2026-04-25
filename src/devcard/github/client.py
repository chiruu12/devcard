from __future__ import annotations

import asyncio
import logging
import re
import time

import httpx

from devcard.config import DevCardConfig
from devcard.github.cache import GitHubCache
from devcard.github.models import GitHubContent, GitHubEvent, GitHubRepo, GitHubUser

logger = logging.getLogger(__name__)


class GitHubAPIError(Exception):
    def __init__(self, status_code: int, endpoint: str, message: str):
        self.status_code = status_code
        self.endpoint = endpoint
        super().__init__(f"GitHub API error {status_code} on {endpoint}: {message}")


class GitHubClient:
    def __init__(self, config: DevCardConfig):
        self._config = config
        self._semaphore = asyncio.Semaphore(10)
        self._cache = GitHubCache(
            cache_dir=config.cache_dir,
            ttl=config.cache_ttl,
            enabled=not config.no_cache,
        )

        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if config.github_token:
            headers["Authorization"] = f"Bearer {config.github_token}"

        self._http = httpx.AsyncClient(
            base_url=config.base_url,
            headers=headers,
            timeout=30.0,
        )

    async def _request(self, url: str) -> dict | list:
        async with self._semaphore:
            cached = self._cache.get(url)
            if cached is not None:
                return cached

            full_url = url if url.startswith("http") else f"{self._config.base_url}{url}"
            response = await self._http.get(full_url)

            remaining = response.headers.get("X-RateLimit-Remaining")
            if remaining is not None:
                remaining_int = int(remaining)
                if remaining_int == 0:
                    reset_at = int(response.headers.get("X-RateLimit-Reset", "0"))
                    wait = max(reset_at - int(time.time()), 1)
                    logger.warning("Rate limit exhausted. Sleeping %d seconds.", wait)
                    await asyncio.sleep(wait)
                    response = await self._http.get(full_url)
                elif remaining_int < 10:
                    logger.warning("Rate limit low: %d requests remaining.", remaining_int)

            if response.status_code != 200:
                raise GitHubAPIError(
                    response.status_code,
                    url,
                    response.text[:200],
                )

            data = response.json()
            self._cache.set(url, data)
            return data

    async def _paginate(self, url: str, max_pages: int = 10) -> list[dict]:
        results: list[dict] = []
        current_url = url
        for _ in range(max_pages):
            data = await self._request(current_url)
            if isinstance(data, list):
                results.extend(data)
            else:
                results.append(data)
                break

            link_header = None
            cached = self._cache.get(current_url)
            if cached is not None and current_url != url:
                pass

            full_url = (
                current_url
                if current_url.startswith("http")
                else f"{self._config.base_url}{current_url}"
            )
            resp = await self._http.get(full_url)
            link_header = resp.headers.get("Link", "")

            next_match = re.search(r'<([^>]+)>;\s*rel="next"', link_header)
            if not next_match:
                break
            current_url = next_match.group(1)

        return results

    async def get_user(self, username: str) -> GitHubUser:
        data = await self._request(f"/users/{username}")
        return GitHubUser.model_validate(data)

    async def get_repos(self, username: str) -> list[GitHubRepo]:
        all_repos: list[GitHubRepo] = []
        page = 1
        while True:
            url = f"/users/{username}/repos?per_page=100&sort=stars&direction=desc&page={page}"
            data = await self._request(url)
            if not isinstance(data, list) or len(data) == 0:
                break
            for repo_data in data:
                repo = GitHubRepo.model_validate(repo_data)
                if not repo.fork:
                    all_repos.append(repo)
            if len(data) < 100:
                break
            page += 1

        all_repos.sort(key=lambda r: r.stargazers_count, reverse=True)
        return all_repos[: self._config.max_repos]

    async def get_repo_languages(self, owner: str, repo: str) -> dict[str, int]:
        data = await self._request(f"/repos/{owner}/{repo}/languages")
        return data if isinstance(data, dict) else {}

    async def get_repo_contents(
        self, owner: str, repo: str, path: str = ""
    ) -> list[GitHubContent]:
        url = f"/repos/{owner}/{repo}/contents/{path}"
        data = await self._request(url)
        if isinstance(data, list):
            return [GitHubContent.model_validate(item) for item in data]
        if isinstance(data, dict):
            return [GitHubContent.model_validate(data)]
        return []

    async def get_repo_topics(self, owner: str, repo: str) -> list[str]:
        data = await self._request(f"/repos/{owner}/{repo}/topics")
        if isinstance(data, dict):
            return data.get("names", [])
        return []

    async def get_user_events(self, username: str) -> list[GitHubEvent]:
        events: list[GitHubEvent] = []
        for page in range(1, 4):
            url = f"/users/{username}/events/public?per_page=100&page={page}"
            try:
                data = await self._request(url)
            except GitHubAPIError:
                break
            if not isinstance(data, list) or len(data) == 0:
                break
            events.extend(GitHubEvent.model_validate(e) for e in data)
            if len(data) < 100:
                break
        return events

    async def get_user_orgs(self, username: str) -> list[str]:
        try:
            data = await self._request(f"/users/{username}/orgs")
        except GitHubAPIError:
            return []
        if isinstance(data, list):
            return [org["login"] for org in data if "login" in org]
        return []

    async def close(self) -> None:
        await self._http.aclose()
        self._cache.close()
