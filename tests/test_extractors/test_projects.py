from __future__ import annotations

import pytest

from devcard.extractors.projects import extract_projects
from devcard.github.models import GitHubRepo, GitHubUser


@pytest.fixture
def user():
    return GitHubUser(login="testdev")


@pytest.fixture
def repos():
    return [
        GitHubRepo(
            name="popular",
            full_name="testdev/popular",
            html_url="https://github.com/testdev/popular",
            stargazers_count=500,
            forks_count=100,
            language="Python",
            pushed_at="2026-04-20T00:00:00Z",
            created_at="2020-01-01T00:00:00Z",
            topics=["python", "framework"],
        ),
        GitHubRepo(
            name="small",
            full_name="testdev/small",
            html_url="https://github.com/testdev/small",
            stargazers_count=5,
            forks_count=0,
            language="JavaScript",
            pushed_at="2024-01-01T00:00:00Z",
            created_at="2023-06-01T00:00:00Z",
        ),
        GitHubRepo(
            name="forked",
            full_name="testdev/forked",
            html_url="https://github.com/testdev/forked",
            stargazers_count=1000,
            fork=True,
        ),
    ]


async def test_projects_ranked_by_score(user, repos):
    result = await extract_projects(None, user, repos)
    assert result is not None
    assert result[0].name == "popular"
    assert result[1].name == "small"


async def test_projects_excludes_forks(user, repos):
    result = await extract_projects(None, user, repos)
    names = [p.name for p in result]
    assert "forked" not in names


async def test_projects_status_labels(user, repos):
    result = await extract_projects(None, user, repos)
    popular = next(p for p in result if p.name == "popular")
    assert popular.status in ("active", "maintained")

    small = next(p for p in result if p.name == "small")
    assert small.status in ("inactive", "archived")


async def test_projects_maturity(user, repos):
    result = await extract_projects(None, user, repos)
    popular = next(p for p in result if p.name == "popular")
    assert popular.maturity == "mature"


async def test_projects_empty(user):
    result = await extract_projects(None, user, repos=[])
    assert result is None
