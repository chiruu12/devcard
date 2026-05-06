from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from devcard.extractors.responsiveness import extract_responsiveness
from devcard.github.models import GitHubEvent, GitHubUser


@pytest.fixture
def user():
    return GitHubUser(login="testdev")


@pytest.fixture
def mock_client():
    return AsyncMock()


def _make_event(event_type: str) -> GitHubEvent:
    return GitHubEvent(
        type=event_type,
        created_at="2026-05-01T12:00:00Z",
        repo={"name": "testdev/repo"},
        payload={},
    )


async def test_counts_issue_comments(mock_client, user):
    events = [
        _make_event("IssueCommentEvent"),
        _make_event("IssueCommentEvent"),
        _make_event("IssueCommentEvent"),
    ]
    result = await extract_responsiveness(mock_client, user, [], events=events)
    assert result is not None
    assert result.issue_comments == 3
    assert result.pr_comment_count == 0


async def test_counts_pr_comments(mock_client, user):
    events = [
        _make_event("PullRequestReviewCommentEvent"),
        _make_event("PullRequestReviewCommentEvent"),
    ]
    result = await extract_responsiveness(mock_client, user, [], events=events)
    assert result is not None
    assert result.pr_comment_count == 2
    assert result.issue_comments == 0


async def test_counts_both_types(mock_client, user):
    events = [
        _make_event("IssueCommentEvent"),
        _make_event("PullRequestReviewCommentEvent"),
        _make_event("IssueCommentEvent"),
        _make_event("PullRequestReviewCommentEvent"),
        _make_event("PullRequestReviewCommentEvent"),
    ]
    result = await extract_responsiveness(mock_client, user, [], events=events)
    assert result is not None
    assert result.issue_comments == 2
    assert result.pr_comment_count == 3


async def test_returns_none_no_comment_events(mock_client, user):
    events = [
        _make_event("PushEvent"),
        _make_event("PushEvent"),
        _make_event("CreateEvent"),
    ]
    result = await extract_responsiveness(mock_client, user, [], events=events)
    assert result is None


async def test_avg_response_hours_is_none(mock_client, user):
    events = [_make_event("IssueCommentEvent")]
    result = await extract_responsiveness(mock_client, user, [], events=events)
    assert result is not None
    assert result.avg_response_hours is None


async def test_graceful_on_failure(mock_client, user):
    with patch(
        "devcard.extractors.responsiveness.extract_responsiveness",
        wraps=extract_responsiveness,
    ):
        # Pass a non-iterable as events to trigger the except branch
        result = await extract_responsiveness(
            mock_client, user, [], events="not-a-list"
        )
    assert result is None
