from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from devcard.github.models import GitHubContent, GitHubRepo
from devcard.models import (
    DevCard,
    FixResult,
    Generator,
    Identity,
    Project,
)
from devcard.pipeline import fix_profile_pipeline, fix_repo_pipeline


def _make_devcard(**overrides) -> DevCard:
    defaults = dict(
        generated_at=datetime.now(UTC),
        generator=Generator(name="test", version="0.0.1"),
        identity=Identity(username="testuser"),
    )
    defaults.update(overrides)
    return DevCard(**defaults)


@pytest.fixture()
def mock_config():
    from devcard.config import DevCardConfig

    return DevCardConfig.create(token="fake-token")


class TestFixProfilePipeline:
    @pytest.mark.asyncio
    async def test_fix_profile_dry_run(self, mock_config):
        """Dry run previews changes without writing anything."""
        card = _make_devcard(
            identity=Identity(username="testuser"),
            projects=[
                Project(name="proj-no-desc", language="Python"),
                Project(name="proj-with-desc", description="Has one", language="Go"),
                Project(name="proj-no-topics", language="Rust"),
            ],
        )

        mock_client = AsyncMock()
        mock_client.close = AsyncMock()
        mock_client.create_or_update_file = AsyncMock()
        mock_client.update_repo_description = AsyncMock()
        mock_client.update_repo_topics = AsyncMock()

        with (
            patch(
                "devcard.pipeline.generate_devcard",
                new_callable=AsyncMock,
                return_value=card,
            ),
            patch(
                "devcard.pipeline.GitHubClient",
                return_value=mock_client,
            ),
        ):
            result = await fix_profile_pipeline(
                "testuser", mock_config, ["all"], dry_run=True,
            )

        assert isinstance(result, FixResult)
        assert result.dry_run is True
        assert result.username == "testuser"
        assert len(result.changes) > 0
        assert "Preview" in result.message

        # No actual writes should have been made
        mock_client.create_or_update_file.assert_not_awaited()
        mock_client.update_repo_description.assert_not_awaited()
        mock_client.update_repo_topics.assert_not_awaited()

        # Should have changes for devcard_json, profile_readme,
        # missing_descriptions (2 repos without), and missing_topics (3 repos without)
        change_types = [c.type for c in result.changes]
        assert "create_file" in change_types
        assert "update_description" in change_types
        assert "update_topics" in change_types


class TestFixRepoPipeline:
    @pytest.mark.asyncio
    async def test_fix_repo_dry_run(self, mock_config):
        """Dry run previews repo fixes without writing anything."""
        target_repo = GitHubRepo(
            name="my-project",
            full_name="testuser/my-project",
            html_url="https://github.com/testuser/my-project",
            description=None,  # Missing description
            language="Python",
        )

        mock_client = AsyncMock()
        mock_client.close = AsyncMock()
        mock_client.get_repos = AsyncMock(return_value=[target_repo])
        mock_client.get_repo_topics = AsyncMock(return_value=[])
        mock_client.get_repo_contents = AsyncMock(
            return_value=[
                GitHubContent(
                    name="src",
                    path="src",
                    type="dir",
                    sha="abc123",
                    url="https://api.github.com/repos/testuser/my-project/contents/src",
                ),
                GitHubContent(
                    name="pyproject.toml",
                    path="pyproject.toml",
                    type="file",
                    sha="def456",
                    url="https://api.github.com/repos/testuser/my-project/contents/pyproject.toml",
                ),
            ],
        )
        mock_client.create_or_update_file = AsyncMock()
        mock_client.update_repo_description = AsyncMock()
        mock_client.update_repo_topics = AsyncMock()

        with patch(
            "devcard.pipeline.GitHubClient",
            return_value=mock_client,
        ):
            result = await fix_repo_pipeline(
                "testuser", "my-project", mock_config, ["all"], dry_run=True,
            )

        assert isinstance(result, FixResult)
        assert result.dry_run is True
        assert result.username == "testuser"
        assert len(result.changes) > 0
        assert "Preview" in result.message

        # No actual writes should have been made
        mock_client.create_or_update_file.assert_not_awaited()
        mock_client.update_repo_description.assert_not_awaited()
        mock_client.update_repo_topics.assert_not_awaited()

        # Should have description, topics, and agents_md changes
        change_types = [c.type for c in result.changes]
        assert "update_description" in change_types
        assert "update_topics" in change_types
        assert "create_file" in change_types

        # Verify AGENTS.md change
        agents_change = next(c for c in result.changes if c.path == "AGENTS.md")
        assert agents_change.repo == "testuser/my-project"
        assert agents_change.content is not None
