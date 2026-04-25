from __future__ import annotations

import logging
from datetime import UTC, datetime

from devcard.github.client import GitHubClient
from devcard.github.models import GitHubRepo, GitHubUser
from devcard.models import Project

logger = logging.getLogger(__name__)

_NOISE_KEYWORDS = {
    "assignment", "homework", "tutorial", "starter", "template", "boilerplate",
}


def _is_noise(repo: GitHubRepo, now: datetime) -> bool:
    name_lower = repo.name.lower().replace("-", " ").replace("_", " ")
    if repo.stargazers_count == 0 and any(kw in name_lower for kw in _NOISE_KEYWORDS):
        return True
    if (
        not repo.description
        and repo.stargazers_count == 0
        and _days_since(repo.pushed_at, now) > 365
    ):
        return True
    return False


async def extract_projects(
    client: GitHubClient,
    user: GitHubUser,
    repos: list[GitHubRepo],
    **kwargs,
) -> list[Project] | None:
    try:
        now = datetime.now(UTC)
        scored: list[tuple[float, GitHubRepo]] = []

        for repo in repos:
            if repo.fork or _is_noise(repo, now):
                continue
            recency = _recency_bonus(repo, now)
            desc_bonus = 5 if repo.description else 0
            topic_bonus = 3 if repo.topics else 0
            score = (
                repo.stargazers_count * 3
                + repo.forks_count * 2
                + recency
                + desc_bonus
                + topic_bonus
            )
            scored.append((score, repo))

        scored.sort(key=lambda x: x[0], reverse=True)

        projects = []
        for _, repo in scored[:5]:
            projects.append(Project(
                name=repo.name,
                description=repo.description,
                url=repo.html_url,
                stars=repo.stargazers_count,
                forks=repo.forks_count,
                language=repo.language,
                topics=repo.topics,
                status=_status(repo, now),
                maturity=_maturity(repo, now),
            ))

        return projects or None
    except Exception:
        logger.warning("Failed to extract projects for %s", user.login, exc_info=True)
        return None


def _recency_bonus(repo: GitHubRepo, now: datetime) -> int:
    days = _days_since(repo.pushed_at, now)
    if days < 30:
        return 10
    if days < 90:
        return 5
    return 0


def _status(repo: GitHubRepo, now: datetime) -> str:
    if repo.archived:
        return "archived"
    days = _days_since(repo.pushed_at, now)
    if days < 30:
        return "active"
    if days < 90:
        return "maintained"
    if days < 365:
        return "inactive"
    return "archived"


def _maturity(repo: GitHubRepo, now: datetime) -> str:
    age_days = _days_since(repo.created_at, now)
    stars = repo.stargazers_count
    push_days = _days_since(repo.pushed_at, now)

    if age_days > 730 and stars > 50:
        return "mature"
    if age_days < 180:
        return "new"
    if stars > 10:
        return "growing"
    if push_days > 365:
        return "stale"
    return "growing"


def _days_since(iso_date: str | None, now: datetime) -> int:
    if not iso_date:
        return 9999
    try:
        dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        return (now - dt).days
    except (ValueError, AttributeError):
        return 9999
