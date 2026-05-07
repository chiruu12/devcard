from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from devcard.extractors.activity import (
    _compute_consistency,
    extract_activity,
    heatmap_sparkline,
)
from devcard.github.models import GitHubEvent, GitHubRepo, GitHubUser


@pytest.fixture
def user():
    return GitHubUser(login="testdev")


@pytest.fixture
def recent_events():
    now = datetime.now(UTC)
    return [
        GitHubEvent(
            type="PushEvent",
            created_at=(now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            repo={"name": "testdev/repo"},
            payload={"size": 3},
        ),
        GitHubEvent(
            type="PushEvent",
            created_at=(now - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            repo={"name": "testdev/repo"},
            payload={"size": 2},
        ),
        GitHubEvent(
            type="PushEvent",
            created_at=(now - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            repo={"name": "testdev/repo"},
            payload={"size": 1},
        ),
    ]


@pytest.fixture
def old_events():
    now = datetime.now(UTC)
    return [
        GitHubEvent(
            type="PushEvent",
            created_at=(now - timedelta(days=200)).strftime("%Y-%m-%dT%H:%M:%SZ"),
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
    now = datetime.now(UTC)
    repos = [
        GitHubRepo(
            name="repo",
            full_name="testdev/repo",
            html_url="https://github.com/testdev/repo",
            pushed_at=(now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
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


async def test_consistency_score_computed(user, recent_events):
    result = await extract_activity(None, user, [], events=recent_events)
    assert result is not None
    assert result.consistency_score is not None
    assert 0 <= result.consistency_score <= 100


async def test_consistency_description_computed(user, recent_events):
    result = await extract_activity(None, user, [], events=recent_events)
    assert result is not None
    assert result.consistency_description is not None
    assert len(result.consistency_description) > 0


def test_compute_consistency_even():
    heatmap = [[10] * 24 for _ in range(7)]
    score, desc = _compute_consistency(heatmap, "active", active_day_count=20, longest_gap=0)
    assert score >= 80
    assert "steady" in desc


def test_compute_consistency_bursty():
    heatmap = [[0] * 24 for _ in range(7)]
    heatmap[0] = [100] * 24  # Only Monday
    score, desc = _compute_consistency(heatmap, "active", active_day_count=3, longest_gap=5)
    assert score <= 30
    assert "bursty" in desc


def test_compute_consistency_three_days():
    """3/7 days active with uneven totals should score low-moderate."""
    heatmap = [[0] * 24 for _ in range(7)]
    heatmap[4] = [1] * 15  # Friday: 15
    heatmap[5] = [1] * 3   # Saturday: 3
    heatmap[6] = [1] * 1   # Sunday: 1
    score, desc = _compute_consistency(heatmap, "active", active_day_count=5, longest_gap=3)
    assert 15 <= score <= 50
    assert "bursty" in desc or "moderate" in desc


def test_compute_consistency_no_heatmap():
    score, desc = _compute_consistency(None, "active")
    assert score == 70


def test_sparkline_output():
    heatmap = [[10, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
               for _ in range(7)]
    heatmap[0] = [50] * 24  # Monday is busiest
    result = heatmap_sparkline(heatmap)
    assert "Mon" in result
    assert "Sun" in result
    assert len(result) > 0


def test_sparkline_empty():
    assert heatmap_sparkline(None) == ""
