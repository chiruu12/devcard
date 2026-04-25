from __future__ import annotations

import pytest

from devcard.extractors.identity import extract_identity
from devcard.github.models import GitHubUser


@pytest.fixture
def user():
    return GitHubUser(
        login="testdev",
        name="Test Developer",
        bio="Builds things",
        avatar_url="https://example.com/avatar.png",
        location="SF",
        company="TestCorp",
        blog="https://test.dev",
        twitter_username="testdev",
        hireable=True,
        public_repos=25,
        public_gists=3,
        followers=150,
        following=42,
        created_at="2018-03-15T10:00:00Z",
        type="User",
    )


async def test_identity_maps_all_fields(user):
    result = await extract_identity(client=None, user=user, repos=[])
    assert result is not None
    assert result.username == "testdev"
    assert result.name == "Test Developer"
    assert result.bio == "Builds things"
    assert result.location == "SF"
    assert result.company == "TestCorp"
    assert result.followers == 150
    assert result.created_at == "2018-03-15T10:00:00Z"


async def test_identity_minimal_user():
    user = GitHubUser(login="minimal", type="User")
    result = await extract_identity(client=None, user=user, repos=[])
    assert result is not None
    assert result.username == "minimal"
    assert result.name is None
    assert result.bio is None
