from __future__ import annotations

import pytest

from devcard.extractors.quality import extract_quality
from devcard.github.models import GitHubContent, GitHubRepo, GitHubUser


@pytest.fixture
def user():
    return GitHubUser(login="testdev")


def _content(name: str, type: str = "file") -> GitHubContent:
    return GitHubContent(name=name, path=name, type=type, sha="abc", url="https://x")


@pytest.fixture
def repos():
    return [
        GitHubRepo(name="repo-a", full_name="testdev/repo-a", html_url="https://x"),
        GitHubRepo(name="repo-b", full_name="testdev/repo-b", html_url="https://x"),
    ]


@pytest.fixture
def root_listings():
    return {
        "repo-a": [
            _content(".github", "dir"),
            _content("tests", "dir"),
            _content("README.md"),
            _content("LICENSE"),
            _content(".flake8"),
            _content("Dockerfile"),
        ],
        "repo-b": [
            _content("README.md"),
            _content("LICENSE"),
        ],
    }


async def test_quality_adoption_rates(user, repos, root_listings):
    result = await extract_quality(None, user, repos, root_listings=root_listings)
    assert result is not None
    assert result.ci_adoption == 0.5
    assert result.test_adoption == 0.5
    assert result.docs_adoption == 1.0
    assert result.license_adoption == 1.0
    assert result.linter_adoption == 0.5


async def test_quality_composite_score(user, repos, root_listings):
    result = await extract_quality(None, user, repos, root_listings=root_listings)
    assert result is not None
    expected = round(0.5 * 0.3 + 0.5 * 0.25 + 1.0 * 0.2 + 1.0 * 0.15 + 0.5 * 0.1, 3)
    assert result.score == expected


async def test_quality_details_per_repo(user, repos, root_listings):
    result = await extract_quality(None, user, repos, root_listings=root_listings)
    assert result is not None
    assert len(result.details) >= 1
    repo_a_detail = next((d for d in result.details if d.repo == "repo-a"), None)
    assert repo_a_detail is not None
    assert "ci" in repo_a_detail.signals
    assert "testing" in repo_a_detail.signals


async def test_quality_empty_repos(user):
    result = await extract_quality(None, user, repos=[], root_listings={})
    assert result is None


async def test_quality_recommendations_generated(user, repos, root_listings):
    result = await extract_quality(None, user, repos, root_listings=root_listings)
    assert result is not None
    assert len(result.recommendations) > 0
    assert any("repo-b" in r for r in result.recommendations)


async def test_quality_recommendations_capped_at_5(user):
    many_repos = [
        GitHubRepo(name=f"repo-{i}", full_name=f"testdev/repo-{i}",
                    html_url="https://x", stargazers_count=10 - i)
        for i in range(10)
    ]
    listings = {f"repo-{i}": [] for i in range(10)}
    result = await extract_quality(None, user, many_repos, root_listings=listings)
    assert result is not None
    assert len(result.recommendations) <= 5
