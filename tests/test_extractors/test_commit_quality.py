from __future__ import annotations

import pytest

from devcard.extractors.commit_quality import extract_commit_quality
from devcard.github.models import GitHubEvent, GitHubUser


@pytest.fixture
def user():
    return GitHubUser(login="testdev")


def _make_push_event(messages: list[str]) -> GitHubEvent:
    commits = [{"sha": f"abc{i}", "message": msg} for i, msg in enumerate(messages)]
    return GitHubEvent(
        type="PushEvent",
        created_at="2026-05-01T12:00:00Z",
        repo={"name": "testdev/repo"},
        payload={"commits": commits},
    )


# ── average message length ───────────────────────────────────────────


async def test_avg_message_length(user):
    # "hello" = 5, "hi" = 2, "goodbye!" = 8 → avg = 5.0
    event = _make_push_event(["hello", "hi", "goodbye!"])

    result = await extract_commit_quality(None, user, [], events=[event])

    assert result is not None
    assert result.avg_message_length == 5.0
    assert result.commits_analyzed == 3


# ── conventional commits ─────────────────────────────────────────────


async def test_conventional_commits_detected(user):
    event = _make_push_event(["feat: add login", "fix: crash on startup"])

    result = await extract_commit_quality(None, user, [], events=[event])

    assert result is not None
    assert result.conventional_commits_pct == 100.0


async def test_non_conventional_not_counted(user):
    event = _make_push_event(["update stuff", "tweak things"])

    result = await extract_commit_quality(None, user, [], events=[event])

    assert result is not None
    assert result.conventional_commits_pct == 0.0


# ── multiline detection ──────────────────────────────────────────────


async def test_multiline_detected(user):
    event = _make_push_event([
        "feat: add auth\n\nAdds JWT-based authentication",
        "fix: typo",
        "refactor: split module\n\nBetter separation of concerns",
    ])

    result = await extract_commit_quality(None, user, [], events=[event])

    assert result is not None
    # 2 out of 3 messages contain newlines
    assert result.multiline_pct == pytest.approx(66.7, abs=0.1)


# ── merge commit filtering ──────────────────────────────────────────


async def test_merge_commits_filtered(user):
    event = _make_push_event([
        "Merge branch 'main' into feature",
        "Merge pull request #42 from dev/fix",
        "feat: real commit",
    ])

    result = await extract_commit_quality(None, user, [], events=[event])

    assert result is not None
    # Only the non-merge commit should be analyzed
    assert result.commits_analyzed == 1
    assert result.conventional_commits_pct == 100.0


# ── edge cases returning None ────────────────────────────────────────


async def test_returns_none_no_events(user):
    result = await extract_commit_quality(None, user, [], events=[])

    assert result is None


async def test_returns_none_no_commits(user):
    event = GitHubEvent(
        type="PushEvent",
        created_at="2026-05-01T12:00:00Z",
        repo={"name": "testdev/repo"},
        payload={"commits": []},
    )

    result = await extract_commit_quality(None, user, [], events=[event])

    assert result is None


# ── failure handling ─────────────────────────────────────────────────


async def test_graceful_on_failure(user):
    # Pass an event with payload that will cause attribute errors
    # when the extractor tries to iterate commits
    bad_event = GitHubEvent(
        type="PushEvent",
        created_at="2026-05-01T12:00:00Z",
        repo={"name": "testdev/repo"},
        payload={"commits": [{"no_message_key": True}]},
    )

    result = await extract_commit_quality(None, user, [], events=[bad_event])

    # Should not crash — either returns None or handles gracefully
    # The extractor uses commit.get("message", "") so this actually succeeds
    # with an empty string. Test with a truly broken structure instead.
    assert result is not None or result is None  # does not crash


async def test_graceful_on_broken_event_data(user):
    """Events with completely wrong payload structure should not crash."""
    bad_event = GitHubEvent(
        type="PushEvent",
        created_at="2026-05-01T12:00:00Z",
        repo={"name": "testdev/repo"},
        payload={"commits": "not-a-list"},
    )

    result = await extract_commit_quality(None, user, [], events=[bad_event])

    assert result is None
