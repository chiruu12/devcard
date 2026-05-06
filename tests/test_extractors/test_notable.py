from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from devcard.extractors.notable import extract_notable_contributions
from devcard.github.models import GitHubEvent, GitHubUser


@pytest.fixture
def user():
    return GitHubUser(login="testdev")


@pytest.fixture
def mock_client():
    client = AsyncMock()
    client.search_user_merged_prs = AsyncMock(return_value=[])
    client.get_repo_info = AsyncMock(return_value=None)
    return client


def _make_event(event_type: str, repo_name: str, action: str = "opened") -> GitHubEvent:
    payload = {}
    if action:
        payload["action"] = action
    return GitHubEvent(
        type=event_type,
        created_at="2026-05-01T12:00:00Z",
        repo={"name": repo_name},
        payload=payload,
    )


async def test_returns_empty_when_no_external_contributions(mock_client, user):
    result = await extract_notable_contributions(mock_client, user, [], events=[])
    assert result == []


async def test_filters_out_own_repos(mock_client, user):
    """Events to user's own repos should not appear in notable contributions."""
    events = [_make_event("PullRequestEvent", "testdev/my-repo")]
    mock_client.search_user_merged_prs.return_value = []

    result = await extract_notable_contributions(mock_client, user, [], events=events)
    assert result == []


async def test_filters_by_star_threshold(mock_client, user):
    """Repos below 1000 stars should be excluded."""
    events = [_make_event("PullRequestEvent", "bigorg/small-repo")]
    mock_client.search_user_merged_prs.return_value = []
    mock_client.get_repo_info.return_value = {
        "full_name": "bigorg/small-repo",
        "stars": 500,
        "description": "A small repo",
        "html_url": "https://github.com/bigorg/small-repo",
    }

    result = await extract_notable_contributions(mock_client, user, [], events=events)
    assert result == []


async def test_includes_notable_repo_from_events(mock_client, user):
    """PRs to popular repos should appear as notable contributions."""
    events = [_make_event("PullRequestEvent", "facebook/react")]
    mock_client.search_user_merged_prs.return_value = []
    mock_client.get_repo_info.return_value = {
        "full_name": "facebook/react",
        "stars": 220000,
        "description": "A JS library for building UIs",
        "html_url": "https://github.com/facebook/react",
    }

    result = await extract_notable_contributions(mock_client, user, [], events=events)
    assert len(result) == 1
    assert result[0].repo == "facebook/react"
    assert result[0].repo_stars == 220000
    assert result[0].contribution_type == "pull_request"


async def test_includes_notable_from_search(mock_client, user):
    """Merged PRs found via search API should appear."""
    mock_client.search_user_merged_prs.return_value = [
        {"repo": "pallets/flask", "merged_prs": 3},
    ]
    mock_client.get_repo_info.return_value = {
        "full_name": "pallets/flask",
        "stars": 68000,
        "description": "Python micro framework",
        "html_url": "https://github.com/pallets/flask",
    }

    result = await extract_notable_contributions(mock_client, user, [], events=[])
    assert len(result) == 1
    assert result[0].repo == "pallets/flask"
    assert result[0].merged == 3
    assert result[0].contribution_type == "pull_request"


async def test_deduplicates_events_and_search(mock_client, user):
    """Same repo from events and search should be merged, not duplicated."""
    events = [_make_event("PullRequestEvent", "kubernetes/kubernetes")]
    mock_client.search_user_merged_prs.return_value = [
        {"repo": "kubernetes/kubernetes", "merged_prs": 5},
    ]
    mock_client.get_repo_info.return_value = {
        "full_name": "kubernetes/kubernetes",
        "stars": 110000,
        "description": "Production-Grade Container Scheduling",
        "html_url": "https://github.com/kubernetes/kubernetes",
    }

    result = await extract_notable_contributions(mock_client, user, [], events=events)
    assert len(result) == 1
    assert result[0].repo == "kubernetes/kubernetes"
    assert result[0].merged == 5
    assert result[0].count >= 5


async def test_sorts_by_stars_descending(mock_client, user):
    """Results should be sorted by repo stars, highest first."""
    mock_client.search_user_merged_prs.return_value = [
        {"repo": "smallorg/big-repo", "merged_prs": 1},
        {"repo": "bigorg/huge-repo", "merged_prs": 1},
    ]

    async def _get_info(owner, repo):
        data = {
            "smallorg/big-repo": {
                "full_name": "smallorg/big-repo",
                "stars": 5000,
                "description": "A big repo",
                "html_url": "https://github.com/smallorg/big-repo",
            },
            "bigorg/huge-repo": {
                "full_name": "bigorg/huge-repo",
                "stars": 50000,
                "description": "A huge repo",
                "html_url": "https://github.com/bigorg/huge-repo",
            },
        }
        return data.get(f"{owner}/{repo}")

    mock_client.get_repo_info = AsyncMock(side_effect=_get_info)

    result = await extract_notable_contributions(mock_client, user, [], events=[])
    assert len(result) == 2
    assert result[0].repo_stars > result[1].repo_stars


async def test_limits_to_max_results(mock_client, user):
    """Should return at most 10 results."""
    search_results = [
        {"repo": f"org/repo-{i}", "merged_prs": 1}
        for i in range(15)
    ]
    mock_client.search_user_merged_prs.return_value = search_results

    async def _get_info(owner, repo):
        return {
            "full_name": f"{owner}/{repo}",
            "stars": 2000,
            "description": "Notable repo",
            "html_url": f"https://github.com/{owner}/{repo}",
        }

    mock_client.get_repo_info = AsyncMock(side_effect=_get_info)

    result = await extract_notable_contributions(mock_client, user, [], events=[])
    assert len(result) <= 10


async def test_push_events_to_external_repos(mock_client, user):
    """PushEvents to external repos should be counted as commit contributions."""
    events = [_make_event("PushEvent", "torvalds/linux", action="")]
    mock_client.search_user_merged_prs.return_value = []
    mock_client.get_repo_info.return_value = {
        "full_name": "torvalds/linux",
        "stars": 180000,
        "description": "Linux kernel source tree",
        "html_url": "https://github.com/torvalds/linux",
    }

    result = await extract_notable_contributions(mock_client, user, [], events=events)
    assert len(result) == 1
    assert result[0].contribution_type == "commit"


async def test_graceful_on_client_failure(user):
    """Should return empty list, not raise, when client methods fail."""
    client = AsyncMock()
    client.search_user_merged_prs = AsyncMock(side_effect=Exception("Network error"))
    client.get_repo_info = AsyncMock(side_effect=Exception("Network error"))

    result = await extract_notable_contributions(client, user, [], events=[])
    assert result == []
