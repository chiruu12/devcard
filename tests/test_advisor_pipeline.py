from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from devcard.advisor import advise_pipeline
from devcard.config import DevCardConfig
from devcard.models import (
    DevCard,
    Generator,
    Identity,
    ProfileAdvice,
    ProfileRepoData,
)


def _minimal_devcard(**identity_kwargs) -> DevCard:
    """Build a minimal DevCard with optional identity overrides."""
    return DevCard(
        generated_at=datetime.now(UTC),
        generator=Generator(name="test", version="0.1"),
        identity=Identity(username="testdev", **identity_kwargs),
    )


def _minimal_profile(**kwargs) -> ProfileRepoData:
    """Build a minimal ProfileRepoData with optional overrides."""
    return ProfileRepoData(**kwargs)


@pytest.fixture()
def config() -> DevCardConfig:
    return DevCardConfig(github_token="fake-token")


@pytest.fixture()
def _patch_pipeline(request):
    """Patch generate_devcard and _fetch_profile_repo_data for all tests.

    Tests can override the devcard or profile via indirect parametrization
    by setting ``request.param`` to a dict with ``devcard`` and/or ``profile``
    keys.  Falls back to bare-minimum defaults.
    """
    params = getattr(request, "param", {}) or {}
    devcard = params.get("devcard", _minimal_devcard())
    profile = params.get("profile", _minimal_profile())

    with (
        patch(
            "devcard.advisor.generate_devcard",
            new_callable=AsyncMock,
            return_value=devcard,
        ),
        patch(
            "devcard.advisor._fetch_profile_repo_data",
            new_callable=AsyncMock,
            return_value=profile,
        ),
    ):
        yield


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.usefixtures("_patch_pipeline")
async def test_advise_returns_profile_advice(config: DevCardConfig):
    """Basic call returns a ProfileAdvice with verdicts."""
    result = await advise_pipeline("testdev", config)

    assert isinstance(result, ProfileAdvice)
    assert result.username == "testdev"
    assert isinstance(result.verdicts, list)
    # Rules YAML always produces at least one verdict for a minimal card
    assert len(result.verdicts) > 0


@pytest.mark.asyncio
@pytest.mark.usefixtures("_patch_pipeline")
async def test_advise_includes_scores(config: DevCardConfig):
    """human_score and agent_score are populated integers."""
    result = await advise_pipeline("testdev", config)

    assert isinstance(result.human_score, int)
    assert isinstance(result.agent_score, int)
    assert 0 <= result.human_score <= 100
    assert 0 <= result.agent_score <= 100


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "_patch_pipeline",
    [{"devcard": _minimal_devcard()}],  # bio=None → bio_empty=True
    indirect=True,
)
async def test_advise_verdicts_bio_empty_critique(
    config: DevCardConfig,
    _patch_pipeline,  # noqa: PT019 — indirect fixture
):
    """A DevCard with empty bio triggers the bio_empty critique."""
    result = await advise_pipeline("testdev", config)

    bio_verdicts = [
        v for v in result.verdicts if "bio" in v.message.lower() and v.type == "critique"
    ]
    assert len(bio_verdicts) >= 1, "Expected a bio-empty critique verdict"


@pytest.mark.asyncio
@pytest.mark.usefixtures("_patch_pipeline")
async def test_advise_no_llm_without_enrich(config: DevCardConfig):
    """summary is None when enrich=False (the default)."""
    result = await advise_pipeline("testdev", config)

    assert result.summary is None


@pytest.mark.asyncio
@pytest.mark.usefixtures("_patch_pipeline")
async def test_advise_with_enrich_calls_llm(config: DevCardConfig):
    """When enrich=True and LLM is available, summary is populated."""
    mock_llm = AsyncMock()
    mock_llm.generate_summary.return_value = "Great developer, keep it up."
    mock_llm.close = AsyncMock()

    with patch(
        "devcard.advisor.AdvisorLLM.from_config",
        return_value=mock_llm,
    ):
        result = await advise_pipeline("testdev", config, enrich=True)

    assert result.summary == "Great developer, keep it up."
    mock_llm.generate_summary.assert_awaited_once()
    mock_llm.close.assert_awaited_once()
