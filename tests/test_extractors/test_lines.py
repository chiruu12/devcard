from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from devcard.extractors.lines import extract_lines_changed
from devcard.github.models import GitHubRepo, GitHubUser


@pytest.fixture
def user():
    return GitHubUser(login="testdev")


def _repo(name: str, *, stars: int = 100, fork: bool = False) -> GitHubRepo:
    return GitHubRepo(
        name=name,
        full_name=f"testdev/{name}",
        html_url=f"https://github.com/testdev/{name}",
        stargazers_count=stars,
        fork=fork,
    )


def _stats(login: str, weeks: list[dict]) -> dict:
    total = sum(w.get("a", 0) + w.get("d", 0) for w in weeks)
    return {
        "author": {"login": login},
        "total": total,
        "weeks": weeks,
    }


@pytest.fixture
def mock_client():
    return AsyncMock()


async def test_sums_additions_and_deletions(user, mock_client):
    """Verify total_added and total_deleted are correct sums of weekly data."""
    weeks = [
        {"w": 1620000000, "a": 100, "d": 50, "c": 0},
        {"w": 1620604800, "a": 200, "d": 30, "c": 0},
    ]
    mock_client.get_contributor_stats = AsyncMock(
        return_value=[_stats("testdev", weeks)],
    )

    repos = [_repo("repo1")]
    result = await extract_lines_changed(mock_client, user, repos)

    assert result is not None
    assert result.total_added == 300
    assert result.total_deleted == 80
    assert len(result.by_repo) == 1
    assert result.by_repo[0].repo == "repo1"
    assert result.by_repo[0].added == 300
    assert result.by_repo[0].deleted == 80


async def test_filters_for_user(user, mock_client):
    """Only count contributions from the matching user, ignore others."""
    user_weeks = [{"w": 1620000000, "a": 50, "d": 10, "c": 0}]
    other_weeks = [{"w": 1620000000, "a": 9999, "d": 9999, "c": 0}]

    mock_client.get_contributor_stats = AsyncMock(
        return_value=[
            _stats("otheruser", other_weeks),
            _stats("testdev", user_weeks),
        ],
    )

    repos = [_repo("repo1")]
    result = await extract_lines_changed(mock_client, user, repos)

    assert result is not None
    assert result.total_added == 50
    assert result.total_deleted == 10


async def test_sorts_by_total_activity(user, mock_client):
    """Repos should be sorted by added+deleted descending."""
    small_weeks = [{"w": 1620000000, "a": 10, "d": 5, "c": 0}]
    large_weeks = [{"w": 1620000000, "a": 500, "d": 200, "c": 0}]
    medium_weeks = [{"w": 1620000000, "a": 100, "d": 50, "c": 0}]

    async def _get_stats(owner: str, repo: str) -> list[dict]:
        mapping = {
            "small-repo": [_stats("testdev", small_weeks)],
            "large-repo": [_stats("testdev", large_weeks)],
            "medium-repo": [_stats("testdev", medium_weeks)],
        }
        return mapping.get(repo, [])

    mock_client.get_contributor_stats = AsyncMock(side_effect=_get_stats)

    repos = [_repo("small-repo"), _repo("large-repo"), _repo("medium-repo")]
    result = await extract_lines_changed(mock_client, user, repos)

    assert result is not None
    assert len(result.by_repo) == 3
    assert result.by_repo[0].repo == "large-repo"
    assert result.by_repo[1].repo == "medium-repo"
    assert result.by_repo[2].repo == "small-repo"


async def test_returns_none_with_no_repos(user, mock_client):
    """Empty repos list should return None."""
    result = await extract_lines_changed(mock_client, user, [])
    assert result is None


async def test_returns_none_with_zero_lines(user, mock_client):
    """All zeros in weekly data should return None."""
    zero_weeks = [{"w": 1620000000, "a": 0, "d": 0, "c": 0}]
    mock_client.get_contributor_stats = AsyncMock(
        return_value=[_stats("testdev", zero_weeks)],
    )

    repos = [_repo("repo1")]
    result = await extract_lines_changed(mock_client, user, repos)

    assert result is None


async def test_handles_missing_author(user, mock_client):
    """Contributor entries with author=None should be skipped gracefully."""
    valid_weeks = [{"w": 1620000000, "a": 40, "d": 20, "c": 0}]

    mock_client.get_contributor_stats = AsyncMock(
        return_value=[
            {"author": None, "total": 999, "weeks": [{"w": 1, "a": 999, "d": 999, "c": 0}]},
            _stats("testdev", valid_weeks),
        ],
    )

    repos = [_repo("repo1")]
    result = await extract_lines_changed(mock_client, user, repos)

    assert result is not None
    assert result.total_added == 40
    assert result.total_deleted == 20


async def test_limits_to_max_repos(user, mock_client):
    """Only the first 10 non-fork repos should be processed."""
    weeks = [{"w": 1620000000, "a": 10, "d": 5, "c": 0}]
    mock_client.get_contributor_stats = AsyncMock(
        return_value=[_stats("testdev", weeks)],
    )

    repos = [_repo(f"repo-{i}") for i in range(15)]
    result = await extract_lines_changed(mock_client, user, repos)

    assert result is not None
    # Should have called get_contributor_stats exactly 10 times
    assert mock_client.get_contributor_stats.call_count == 10
    assert len(result.by_repo) == 10


async def test_graceful_on_failure(user):
    """Client raising an exception should return None, not propagate."""
    client = AsyncMock()
    client.get_contributor_stats = AsyncMock(
        side_effect=Exception("Network error"),
    )

    repos = [_repo("repo1")]
    result = await extract_lines_changed(client, user, repos)

    # gather with return_exceptions=True catches per-repo errors;
    # all repos failing means no data, so result is None
    assert result is None
