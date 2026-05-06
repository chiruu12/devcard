from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from devcard.models import (
    AuditResult,
    DevCard,
    Generator,
    Identity,
    Issue,
    ProfileRepoData,
    Project,
    Quality,
)
from devcard.pipeline import audit_pipeline


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


class TestAuditPipeline:
    @pytest.mark.asyncio
    async def test_returns_audit_result(self, mock_config):
        """audit_pipeline returns an AuditResult with scores and issues."""
        card = _make_devcard(
            identity=Identity(username="testuser", bio="I build things"),
            projects=[
                Project(name="proj1", description="A project", topics=["python"]),
            ],
            quality=Quality(license_adoption=0.8, docs_adoption=0.8),
        )
        profile = ProfileRepoData(
            has_profile_readme=True,
            readme_length=200,
            has_devcard_json=True,
            has_llms_txt=True,
        )

        with (
            patch(
                "devcard.pipeline.generate_devcard",
                new_callable=AsyncMock,
                return_value=card,
            ),
            patch(
                "devcard.pipeline._fetch_profile_repo_data",
                new_callable=AsyncMock,
                return_value=profile,
            ),
            patch("devcard.pipeline.GitHubClient") as mock_client_cls,
        ):
            mock_client_cls.return_value.close = AsyncMock()
            result = await audit_pipeline("testuser", mock_config)

        assert isinstance(result, AuditResult)
        assert result.username == "testuser"
        assert 0 <= result.human_visibility_score <= 100
        assert 0 <= result.agent_readiness_score <= 100
        assert isinstance(result.issues, list)
        assert isinstance(result.summary, dict)
        assert "total_repos" in result.summary

    @pytest.mark.asyncio
    async def test_includes_issues(self, mock_config):
        """Issues are detected from the devcard."""
        card = _make_devcard(
            identity=Identity(username="testuser", bio=None),
            projects=[
                Project(name="no-desc"),
            ],
        )
        profile = ProfileRepoData(has_profile_readme=False)

        with (
            patch(
                "devcard.pipeline.generate_devcard",
                new_callable=AsyncMock,
                return_value=card,
            ),
            patch(
                "devcard.pipeline._fetch_profile_repo_data",
                new_callable=AsyncMock,
                return_value=profile,
            ),
            patch("devcard.pipeline.GitHubClient") as mock_client_cls,
        ):
            mock_client_cls.return_value.close = AsyncMock()
            result = await audit_pipeline("testuser", mock_config)

        assert len(result.issues) > 0
        issue_types = [i.type for i in result.issues]
        assert "missing_bio" in issue_types
        assert "missing_profile_readme" in issue_types
        for issue in result.issues:
            assert isinstance(issue, Issue)

    @pytest.mark.asyncio
    async def test_recommendations_from_issues(self, mock_config):
        """Recommendations are derived from top issues."""
        card = _make_devcard(
            identity=Identity(username="testuser", bio=None),
            projects=[
                Project(name="a"),
                Project(name="b"),
            ],
        )
        profile = ProfileRepoData(has_profile_readme=False)

        with (
            patch(
                "devcard.pipeline.generate_devcard",
                new_callable=AsyncMock,
                return_value=card,
            ),
            patch(
                "devcard.pipeline._fetch_profile_repo_data",
                new_callable=AsyncMock,
                return_value=profile,
            ),
            patch("devcard.pipeline.GitHubClient") as mock_client_cls,
        ):
            mock_client_cls.return_value.close = AsyncMock()
            result = await audit_pipeline("testuser", mock_config)

        assert len(result.recommendations) > 0
        assert len(result.recommendations) <= 5
        # Recommendations should be the messages from the top issues
        for rec in result.recommendations:
            assert any(issue.message == rec for issue in result.issues)
