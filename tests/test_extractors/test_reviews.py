from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from devcard.extractors.reviews import extract_review_activity
from devcard.github.models import GitHubEvent, GitHubUser


@pytest.fixture
def user():
    return GitHubUser(login="testdev")


@pytest.fixture
def mock_client():
    return AsyncMock()


def _make_review_event(repo_name: str, state: str) -> GitHubEvent:
    return GitHubEvent(
        type="PullRequestReviewEvent",
        created_at="2026-05-01T12:00:00Z",
        repo={"name": repo_name},
        payload={"review": {"state": state}},
    )


async def test_counts_approved_reviews(mock_client, user):
    events = [
        _make_review_event("org/repo-a", "approved"),
        _make_review_event("org/repo-b", "approved"),
    ]
    result = await extract_review_activity(mock_client, user, [], events=events)
    assert result is not None
    assert result.approved == 2
    assert result.reviews_given == 2


async def test_counts_changes_requested(mock_client, user):
    events = [_make_review_event("org/repo", "changes_requested")]
    result = await extract_review_activity(mock_client, user, [], events=events)
    assert result is not None
    assert result.changes_requested == 1
    assert result.reviews_given == 1


async def test_counts_commented(mock_client, user):
    events = [_make_review_event("org/repo", "commented")]
    result = await extract_review_activity(mock_client, user, [], events=events)
    assert result is not None
    assert result.commented == 1
    assert result.reviews_given == 1


async def test_tracks_unique_repos(mock_client, user):
    events = [
        _make_review_event("org/repo-x", "approved"),
        _make_review_event("org/repo-x", "commented"),
        _make_review_event("org/repo-x", "changes_requested"),
    ]
    result = await extract_review_activity(mock_client, user, [], events=events)
    assert result is not None
    assert result.repos_reviewed == ["org/repo-x"]


async def test_returns_none_with_no_review_events(mock_client, user):
    events = [
        GitHubEvent(
            type="PushEvent",
            created_at="2026-05-01T12:00:00Z",
            repo={"name": "org/repo"},
            payload={"size": 3},
        ),
        GitHubEvent(
            type="PushEvent",
            created_at="2026-05-02T12:00:00Z",
            repo={"name": "org/repo"},
            payload={"size": 1},
        ),
    ]
    result = await extract_review_activity(mock_client, user, [], events=events)
    assert result is None


async def test_ignores_unknown_states(mock_client, user):
    events = [_make_review_event("org/repo", "bogus_state")]
    result = await extract_review_activity(mock_client, user, [], events=events)
    assert result is None


async def test_dismissed_not_counted_in_total(mock_client, user):
    events = [
        _make_review_event("org/repo", "dismissed"),
        _make_review_event("org/repo", "dismissed"),
    ]
    result = await extract_review_activity(mock_client, user, [], events=events)
    # dismissed is a known state (not ignored) but doesn't increment any counter,
    # so reviews_given stays 0 and the extractor returns None
    assert result is None
