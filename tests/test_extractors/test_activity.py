from __future__ import annotations

import pytest

from devcard.extractors.activity import extract_activity
from devcard.github.models import GitHubEvent, GitHubRepo, GitHubUser


@pytest.fixture
def user():
    return GitHubUser(login="testdev")


@pytest.fixture
def recent_events():
    return [
        GitHubEvent(
            type="PushEvent",
            created_at="2026-04-24T14:00:00Z",
            repo={"name": "testdev/repo"},
            payload={"size": 3},
        ),
        GitHubEvent(
            type="PushEvent",
            created_at="2026-04-23T10:00:00Z",
            repo={"name": "testdev/repo"},
            payload={"size": 2},
        ),
        GitHubEvent(
            type="PushEvent",
            created_at="2026-04-22T15:00:00Z",
            repo={"name": "testdev/repo"},
            payload={"size": 1},
        ),
    ]


@pytest.fixture
def old_events():
    return [
        GitHubEvent(
            type="PushEvent",
            created_at="2025-01-01T12:00:00Z",
            repo={"name": "testdev/repo"},
            payload={"size": 1},
        ),
    ]


async def test_activity_active_status(user, recent_events):
    result = await extract_activity(None, user, [], events=recent_events)
    assert result is not None
    assert result.status == "active"


async def test_activity_dormant_status(user, old_events):
    result = await extract_activity(None, user, [], events=old_events)
    assert result is not None
    assert result.status == "dormant"


async def test_activity_peak_hours(user, recent_events):
    result = await extract_activity(None, user, [], events=recent_events)
    assert result is not None
    assert len(result.peak_hours) > 0
    assert all(0 <= h <= 23 for h in result.peak_hours)


async def test_activity_heatmap_shape(user, recent_events):
    result = await extract_activity(None, user, [], events=recent_events)
    assert result is not None
    assert result.heatmap is not None
    assert len(result.heatmap) == 7
    assert all(len(row) == 24 for row in result.heatmap)


async def test_activity_commits_uses_payload_size(user, recent_events):
    repos = [
        GitHubRepo(
            name="repo",
            full_name="testdev/repo",
            html_url="https://github.com/testdev/repo",
            pushed_at="2026-04-24T00:00:00Z",
        ),
    ]
    result = await extract_activity(None, user, repos, events=recent_events)
    assert result is not None
    assert result.commits_last_year is not None
    assert result.commits_last_year > 100


async def test_activity_no_events(user):
    repos = [
        GitHubRepo(
            name="old",
            full_name="testdev/old",
            html_url="https://github.com/testdev/old",
            pushed_at="2023-01-01T00:00:00Z",
        ),
    ]
    result = await extract_activity(None, user, repos, events=[])
    assert result is not None
    assert result.status == "dormant"
