from __future__ import annotations

import asyncio
import base64
import logging
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

    @property
    def has_token(self) -> bool:
        return self._config.github_token is not None

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

    async def search_user_prs_in_org(
        self, username: str, org: str
    ) -> dict[str, int]:
        try:
            url = (
                f"/search/issues?q=author:{username}+org:{org}"
                f"+type:pr&per_page=1"
            )
            data = await self._request(url)
            total = data.get("total_count", 0) if isinstance(data, dict) else 0
            merged_url = (
                f"/search/issues?q=author:{username}+org:{org}"
                f"+type:pr+is:merged&per_page=1"
            )
            merged_data = await self._request(merged_url)
            merged = (
                merged_data.get("total_count", 0)
                if isinstance(merged_data, dict) else 0
            )
            return {"total": total, "merged": merged}
        except GitHubAPIError:
            return {"total": 0, "merged": 0}

    async def search_user_issues_in_org(
        self, username: str, org: str
    ) -> int:
        try:
            url = (
                f"/search/issues?q=author:{username}+org:{org}"
                f"+type:issue&per_page=1"
            )
            data = await self._request(url)
            return data.get("total_count", 0) if isinstance(data, dict) else 0
        except GitHubAPIError:
            return 0

    async def get_starred_repos(
        self, username: str, limit: int = 100
    ) -> list[GitHubRepo]:
        repos: list[GitHubRepo] = []
        pages = (limit + 99) // 100
        for page in range(1, pages + 1):
            try:
                url = f"/users/{username}/starred?per_page=100&page={page}"
                data = await self._request(url)
            except GitHubAPIError:
                break
            if not isinstance(data, list) or len(data) == 0:
                break
            repos.extend(GitHubRepo.model_validate(r) for r in data)
            if len(data) < 100:
                break
        return repos[:limit]

    async def search_user_commit_count(self, username: str, since_date: str) -> int | None:
        """Count total commits by a user since a date via the search API.

        Returns None on failure (preserves existing estimate as fallback).
        """
        try:
            url = (
                f"/search/commits?q=author:{username}+author-date:>{since_date}"
                f"&per_page=1"
            )
            data = await self._request(url)
            if isinstance(data, dict):
                return data.get("total_count")
            return None
        except GitHubAPIError:
            return None

    async def search_user_merged_prs(
        self, username: str, max_pages: int = 3,
    ) -> list[dict]:
        """Search for merged PRs by the user across all of GitHub."""
        try:
            repo_counts: dict[str, int] = {}
            for page in range(1, max_pages + 1):
                url = (
                    f"/search/issues?q=author:{username}+type:pr+is:merged"
                    f"&sort=created&order=desc&per_page=100&page={page}"
                )
                data = await self._request(url)
                if not isinstance(data, dict):
                    break

                items = data.get("items", [])
                if not items:
                    break

                for item in items:
                    repo_url = item.get("repository_url", "")
                    parts = repo_url.rstrip("/").split("/")
                    if len(parts) >= 2:
                        full_name = f"{parts[-2]}/{parts[-1]}"
                        repo_counts[full_name] = repo_counts.get(full_name, 0) + 1

                if len(items) < 100:
                    break

            return [
                {"repo": repo, "merged_prs": count}
                for repo, count in repo_counts.items()
            ]
        except GitHubAPIError:
            return []

    async def get_repo_info(self, owner: str, repo: str) -> dict | None:
        """Fetch basic info for a single repo (stars, description, url)."""
        try:
            data = await self._request(f"/repos/{owner}/{repo}")
            if isinstance(data, dict):
                return {
                    "full_name": data.get("full_name", f"{owner}/{repo}"),
                    "stars": data.get("stargazers_count", 0),
                    "description": data.get("description"),
                    "html_url": data.get("html_url", f"https://github.com/{owner}/{repo}"),
                }
            return None
        except GitHubAPIError:
            return None

    async def get_commit_detail(
        self, owner: str, repo: str, sha: str,
    ) -> dict | None:
        """Fetch a single commit with file patches."""
        try:
            data = await self._request(f"/repos/{owner}/{repo}/commits/{sha}")
            return data if isinstance(data, dict) else None
        except GitHubAPIError:
            return None

    async def get_contributor_stats(
        self, owner: str, repo: str, max_retries: int = 1,
    ) -> list[dict]:
        """Fetch contributor stats (weekly additions/deletions per contributor).

        GitHub returns 202 while computing stats. Best-effort: one retry then give up.
        """
        url = f"/repos/{owner}/{repo}/stats/contributors"
        for attempt in range(max_retries + 1):
            try:
                data = await self._request(url)
                if isinstance(data, list) and data:
                    return data
                return []
            except GitHubAPIError as exc:
                if exc.status_code == 202 and attempt < max_retries:
                    logger.info(
                        "Stats computing for %s/%s (202), will retry once in 2s",
                        owner, repo,
                    )
                    await asyncio.sleep(2.0)
                    continue
                return []
        return []

    async def _mutate(self, method: str, url: str, body: dict) -> dict:
        """Base write method for PUT/PATCH/POST. Like _request but for mutations."""
        async with self._semaphore:
            full_url = url if url.startswith("http") else f"{self._config.base_url}{url}"
            response = await self._http.request(method, full_url, json=body)

            remaining = response.headers.get("X-RateLimit-Remaining")
            if remaining is not None:
                remaining_int = int(remaining)
                if remaining_int == 0:
                    reset_at = int(response.headers.get("X-RateLimit-Reset", "0"))
                    wait = max(reset_at - int(time.time()), 1)
                    logger.warning("Rate limit exhausted. Sleeping %d seconds.", wait)
                    await asyncio.sleep(wait)
                    response = await self._http.request(method, full_url, json=body)
                elif remaining_int < 10:
                    logger.warning("Rate limit low: %d requests remaining.", remaining_int)

            if response.status_code not in (200, 201):
                raise GitHubAPIError(
                    response.status_code,
                    url,
                    response.text[:200],
                )

            return response.json()

    async def create_or_update_file(
        self,
        owner: str,
        repo: str,
        path: str,
        content: str,
        commit_message: str,
    ) -> dict:
        """Create or update a file via the GitHub Contents API."""
        url = f"/repos/{owner}/{repo}/contents/{path}"

        # Check if file already exists (to get its SHA for updates)
        sha: str | None = None
        try:
            data = await self._request(url)
            if isinstance(data, dict):
                sha = data.get("sha")
        except GitHubAPIError as exc:
            if exc.status_code != 404:
                raise

        body: dict = {
            "message": commit_message,
            "content": base64.b64encode(content.encode()).decode(),
        }
        if sha is not None:
            body["sha"] = sha

        return await self._mutate("PUT", url, body)

    async def update_repo_description(
        self, owner: str, repo: str, description: str
    ) -> dict:
        """Update a repository's description via the GitHub Repos API."""
        url = f"/repos/{owner}/{repo}"
        return await self._mutate("PATCH", url, {"description": description})

    async def update_repo_topics(
        self, owner: str, repo: str, topics: list[str]
    ) -> dict:
        """Replace a repository's topics via the GitHub Topics API."""
        url = f"/repos/{owner}/{repo}/topics"
        return await self._mutate("PUT", url, {"names": topics})

    async def close(self) -> None:
        await self._http.aclose()
        self._cache.close()
