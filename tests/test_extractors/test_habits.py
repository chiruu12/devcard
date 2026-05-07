from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from devcard.extractors.habits import extract_coding_habits
from devcard.github.models import GitHubEvent, GitHubUser


@pytest.fixture
def user():
    return GitHubUser(login="testdev")


@pytest.fixture
def push_event():
    """A single PushEvent with one commit."""
    return GitHubEvent(
        type="PushEvent",
        created_at="2026-05-01T12:00:00Z",
        repo={"name": "testdev/repo"},
        payload={"commits": [{"sha": "abc123"}]},
    )


def _make_client(commit_detail: dict | None = None, side_effect=None):
    """Build a mock GitHubClient with a stubbed get_commit_detail."""
    client = AsyncMock()
    if side_effect is not None:
        client.get_commit_detail.side_effect = side_effect
    else:
        client.get_commit_detail.return_value = commit_detail
    return client


# ── indentation detection ─────────────────────────────────────────────


async def test_detects_spaces_indentation(user, push_event):
    patch = (
        "@@ -1,3 +1,6 @@\n"
        "+    def greet():\n"
        "+        print('hello')\n"
        "+        return True\n"
    )
    client = _make_client({"files": [{"filename": "main.py", "patch": patch}]})

    result = await extract_coding_habits(client, user, [], events=[push_event])

    assert result is not None
    assert result.indentation == "spaces"
    assert result.spaces_count > 0
    assert result.tabs_count == 0


async def test_detects_tabs_indentation(user, push_event):
    patch = (
        "@@ -1,2 +1,5 @@\n"
        "+\tdef greet():\n"
        "+\t\tprint('hello')\n"
        "+\t\treturn True\n"
    )
    client = _make_client({"files": [{"filename": "main.go", "patch": patch}]})

    result = await extract_coding_habits(client, user, [], events=[push_event])

    assert result is not None
    assert result.indentation == "tabs"
    assert result.tabs_count > 0
    assert result.spaces_count == 0


async def test_detects_mixed_indentation(user, push_event):
    patch = (
        "@@ -1,3 +1,6 @@\n"
        "+    def greet():\n"
        "+        print('hello')\n"
        "+\tvar x = 1\n"
    )
    client = _make_client({"files": [{"filename": "mixed.py", "patch": patch}]})

    result = await extract_coding_habits(client, user, [], events=[push_event])

    assert result is not None
    assert result.indentation == "mixed"
    assert result.spaces_count > 0
    assert result.tabs_count > 0


# ── avg line length ───────────────────────────────────────────────────


async def test_avg_line_length_calculated(user, push_event):
    # Three added lines (after stripping the leading '+'):
    #   "aaaa"       -> 4 chars
    #   "bbbbbb"     -> 6 chars
    #   "cc"         -> 2 chars
    # average = (4 + 6 + 2) / 3 = 4.0
    patch = (
        "@@ -0,0 +1,3 @@\n"
        "+aaaa\n"
        "+bbbbbb\n"
        "+cc\n"
    )
    client = _make_client({"files": [{"filename": "data.txt", "patch": patch}]})

    result = await extract_coding_habits(client, user, [], events=[push_event])

    assert result is not None
    assert result.avg_line_length == 4.0
    assert result.lines_analyzed == 3


# ── edge cases returning None ─────────────────────────────────────────


async def test_returns_none_with_no_events(user):
    client = _make_client()

    result = await extract_coding_habits(client, user, [], events=[])

    assert result is None


async def test_returns_none_with_no_patches(user, push_event):
    # Commit exists but has no files / no patches
    client = _make_client({"files": []})

    result = await extract_coding_habits(client, user, [], events=[push_event])

    assert result is None


async def test_returns_none_with_no_files_key(user, push_event):
    # Commit detail has no 'files' key at all
    client = _make_client({"sha": "abc123", "stats": {"total": 0}})

    result = await extract_coding_habits(client, user, [], events=[push_event])

    assert result is None


# ── failure handling ──────────────────────────────────────────────────


async def test_graceful_on_failure(user, push_event):
    client = _make_client(side_effect=RuntimeError("API exploded"))

    result = await extract_coding_habits(client, user, [], events=[push_event])

    assert result is None
