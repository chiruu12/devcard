"""Tests for the LLM-powered advisor summary generator."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from devcard.advisor.llm_advisor import (
    AdvisorLLM,
    AdvisorSummaryResponse,
    _load_advisor_prompt,
    _serialize_for_llm,
)
from devcard.config import DevCardConfig
from devcard.enrichment.provider import ModelConfig
from devcard.models import (
    Activity,
    CommitQuality,
    DevCard,
    Generator,
    Identity,
    Language,
    Project,
    Quality,
    Verdict,
)


def _make_devcard(**overrides) -> DevCard:
    """Build a DevCard with sensible defaults for advisor tests."""
    defaults = dict(
        generated_at=datetime.now(UTC),
        generator=Generator(name="devcard", version="0.1.0"),
        identity=Identity(
            username="testdev",
            name="Test Dev",
            bio="I build things",
            followers=50,
            public_repos=10,
        ),
        languages=[
            Language(name="Python", percentage=65.0, category="logic"),
            Language(name="TypeScript", percentage=20.0, category="logic"),
            Language(name="Go", percentage=10.0, category="logic"),
            Language(name="Rust", percentage=3.0, category="logic"),
            Language(name="Shell", percentage=1.5, category="logic"),
            Language(name="Dockerfile", percentage=0.5, category="build"),
        ],
        projects=[
            Project(name="ml-toolkit", stars=120, language="Python", status="active"),
            Project(name="web-app", stars=45, language="TypeScript", status="maintained"),
            Project(name="go-server", stars=30, language="Go", status="active"),
            Project(name="rust-cli", stars=5, language="Rust", status="inactive"),
        ],
        activity=Activity(status="active", commits_last_year=400, consistency_score=60),
        quality=Quality(
            score=0.6,
            ci_adoption=0.4,
            test_adoption=0.3,
            docs_adoption=0.7,
            license_adoption=0.8,
            linter_adoption=0.2,
        ),
        commit_quality=CommitQuality(
            avg_message_length=45.0,
            conventional_commits_pct=25.0,
        ),
    )
    defaults.update(overrides)
    return DevCard(**defaults)


def _sample_verdicts() -> list[Verdict]:
    return [
        Verdict(
            category="activity",
            type="praise",
            message="Active contributor with 400 commits last year.",
            severity="info",
        ),
        Verdict(
            category="quality",
            type="critique",
            message="Test adoption is low at 30%.",
            action="Add tests to your top 3 repos.",
            severity="medium",
        ),
        Verdict(
            category="documentation",
            type="suggestion",
            message="Good docs adoption at 70%, but no code blocks in READMEs.",
            severity="low",
        ),
    ]


_MOCK_LLM_RESPONSE = json.dumps({
    "summary": (
        "A prolific Python developer with strong ML focus (65% Python, ml-toolkit at 120 stars). "
        "Test coverage across repos is the biggest gap. "
        "This week, add pytest to ml-toolkit to protect your most visible project."
    ),
    "gaps": [
        "No linter configuration despite 10 repos - adding ruff would improve code consistency.",
    ],
})

_MOCK_LLM_NO_GAPS = json.dumps({
    "summary": "Solid developer profile with consistent activity.",
    "gaps": [],
})


class TestAdvisorSummaryResponse:
    def test_parses_valid_response(self):
        result = AdvisorSummaryResponse.model_validate_json(_MOCK_LLM_RESPONSE)
        assert "ml-toolkit" in result.summary
        assert len(result.gaps) == 1
        assert "ruff" in result.gaps[0]

    def test_parses_response_without_gaps(self):
        result = AdvisorSummaryResponse.model_validate_json(_MOCK_LLM_NO_GAPS)
        assert result.summary == "Solid developer profile with consistent activity."
        assert result.gaps == []

    def test_gaps_max_length(self):
        """Gaps list allows at most 2 entries."""
        data = {
            "summary": "Test",
            "gaps": ["gap1", "gap2", "gap3"],
        }
        with pytest.raises(Exception):  # noqa: B017
            AdvisorSummaryResponse.model_validate(data)


class TestSerializeForLLM:
    def test_includes_identity(self):
        dc = _make_devcard()
        data = json.loads(_serialize_for_llm(dc))
        assert data["identity"]["username"] == "testdev"
        assert data["identity"]["name"] == "Test Dev"
        assert data["identity"]["followers"] == 50

    def test_limits_languages_to_five(self):
        dc = _make_devcard()
        data = json.loads(_serialize_for_llm(dc))
        assert len(data["languages"]) == 5
        assert data["languages"][0]["name"] == "Python"
        assert data["languages"][4]["name"] == "Shell"

    def test_limits_projects_to_three(self):
        dc = _make_devcard()
        data = json.loads(_serialize_for_llm(dc))
        assert len(data["projects"]) == 3
        assert data["projects"][0]["name"] == "ml-toolkit"

    def test_includes_quality_scores(self):
        dc = _make_devcard()
        data = json.loads(_serialize_for_llm(dc))
        assert data["quality"]["score"] == 0.6
        assert data["quality"]["ci_adoption"] == 0.4

    def test_includes_activity(self):
        dc = _make_devcard()
        data = json.loads(_serialize_for_llm(dc))
        assert data["activity"]["status"] == "active"
        assert data["activity"]["commits_last_year"] == 400

    def test_includes_commit_quality(self):
        dc = _make_devcard()
        data = json.loads(_serialize_for_llm(dc))
        assert data["commit_quality"]["avg_message_length"] == 45.0

    def test_minimal_devcard(self):
        dc = DevCard(
            generated_at=datetime.now(UTC),
            generator=Generator(name="devcard", version="0.1.0"),
            identity=Identity(username="minimal"),
        )
        data = json.loads(_serialize_for_llm(dc))
        assert data["identity"]["username"] == "minimal"
        assert "languages" not in data
        assert "projects" not in data
        assert "quality" not in data
        assert "activity" not in data
        assert "commit_quality" not in data


class TestLoadAdvisorPrompt:
    def test_loads_prompt_template(self):
        prompt = _load_advisor_prompt()
        assert "{devcard_data}" in prompt
        assert "{verdicts_data}" in prompt
        assert "{output_schema}" in prompt
        assert "career coach" in prompt

    def test_prompt_has_no_empty_content(self):
        prompt = _load_advisor_prompt()
        assert len(prompt) > 100


class TestAdvisorLLMFromConfig:
    def test_returns_none_without_api_key(self):
        config = DevCardConfig(fireworks_api_key=None)
        advisor = AdvisorLLM.from_config(config)
        assert advisor is None

    def test_returns_instance_with_api_key(self):
        config = DevCardConfig(fireworks_api_key="fake-key")
        advisor = AdvisorLLM.from_config(config)
        assert advisor is not None
        assert isinstance(advisor, AdvisorLLM)

    def test_uses_correct_model_config(self):
        config = DevCardConfig(
            fireworks_api_key="fake-key",
            llm_model="accounts/fireworks/models/test-model",
        )
        advisor = AdvisorLLM.from_config(config)
        assert advisor is not None
        assert advisor._model_config.model == "accounts/fireworks/models/test-model"
        assert advisor._model_config.temperature == 0.4
        assert advisor._model_config.max_tokens == 512


class TestAdvisorLLMGenerateSummary:
    async def test_generate_summary_with_gaps(self):
        advisor = AdvisorLLM(
            api_key="fake-key",
            base_url="https://fake.api/v1",
            model_config=ModelConfig(model="test-model", temperature=0.4, max_tokens=512),
        )
        advisor._call_llm = AsyncMock(return_value=_MOCK_LLM_RESPONSE)

        devcard = _make_devcard()
        verdicts = _sample_verdicts()
        result = await advisor.generate_summary(devcard, verdicts)

        assert result is not None
        assert "ml-toolkit" in result
        assert "Additional observations:" in result
        assert "ruff" in result

    async def test_generate_summary_without_gaps(self):
        advisor = AdvisorLLM(
            api_key="fake-key",
            base_url="https://fake.api/v1",
            model_config=ModelConfig(model="test-model", temperature=0.4, max_tokens=512),
        )
        advisor._call_llm = AsyncMock(return_value=_MOCK_LLM_NO_GAPS)

        devcard = _make_devcard()
        verdicts = _sample_verdicts()
        result = await advisor.generate_summary(devcard, verdicts)

        assert result is not None
        assert "Additional observations:" not in result
        assert "Solid developer profile" in result

    async def test_returns_none_on_llm_failure(self):
        advisor = AdvisorLLM(
            api_key="fake-key",
            base_url="https://fake.api/v1",
            model_config=ModelConfig(model="test-model", temperature=0.4, max_tokens=512),
        )
        advisor._call_llm = AsyncMock(side_effect=RuntimeError("API down"))

        devcard = _make_devcard()
        verdicts = _sample_verdicts()
        result = await advisor.generate_summary(devcard, verdicts)

        assert result is None

    async def test_returns_none_on_invalid_json(self):
        advisor = AdvisorLLM(
            api_key="fake-key",
            base_url="https://fake.api/v1",
            model_config=ModelConfig(model="test-model", temperature=0.4, max_tokens=512),
        )
        advisor._call_llm = AsyncMock(return_value="not valid json at all")

        devcard = _make_devcard()
        verdicts = _sample_verdicts()
        result = await advisor.generate_summary(devcard, verdicts)

        assert result is None

    async def test_cleans_llm_text_in_summary(self):
        """Smart quotes and markdown bold should be cleaned from the summary."""
        response_with_formatting = json.dumps({
            "summary": "**Strong** developer with “smart quotes” and em—dashes.",
            "gaps": ["“Gap with **bold**”"],
        })
        advisor = AdvisorLLM(
            api_key="fake-key",
            base_url="https://fake.api/v1",
            model_config=ModelConfig(model="test-model", temperature=0.4, max_tokens=512),
        )
        advisor._call_llm = AsyncMock(return_value=response_with_formatting)

        devcard = _make_devcard()
        result = await advisor.generate_summary(devcard, [])

        assert result is not None
        assert "**" not in result
        assert "“" not in result
        assert "—" not in result
        assert '"smart quotes"' in result
        assert "em-dashes" in result

    async def test_handles_markdown_wrapped_json(self):
        """LLM response wrapped in ```json fences should still parse."""
        wrapped = f"```json\n{_MOCK_LLM_RESPONSE}\n```"
        advisor = AdvisorLLM(
            api_key="fake-key",
            base_url="https://fake.api/v1",
            model_config=ModelConfig(model="test-model", temperature=0.4, max_tokens=512),
        )
        advisor._call_llm = AsyncMock(return_value=wrapped)

        devcard = _make_devcard()
        result = await advisor.generate_summary(devcard, _sample_verdicts())

        assert result is not None
        assert "ml-toolkit" in result

    async def test_passes_correct_prompt_context(self):
        """Verify the system prompt contains devcard data and verdicts."""
        advisor = AdvisorLLM(
            api_key="fake-key",
            base_url="https://fake.api/v1",
            model_config=ModelConfig(model="test-model", temperature=0.4, max_tokens=512),
        )
        advisor._call_llm = AsyncMock(return_value=_MOCK_LLM_RESPONSE)

        devcard = _make_devcard()
        verdicts = _sample_verdicts()
        await advisor.generate_summary(devcard, verdicts)

        # Inspect the system prompt that was passed to _call_llm
        call_args = advisor._call_llm.call_args
        system_prompt = call_args[0][0]
        user_message = call_args[0][1]

        # System prompt should contain serialized devcard data
        assert "testdev" in system_prompt
        assert "Python" in system_prompt
        # System prompt should contain verdicts
        assert "Active contributor" in system_prompt
        assert "Test adoption is low" in system_prompt
        # User message references the username
        assert "testdev" in user_message

    async def test_close_cleans_up_client(self):
        advisor = AdvisorLLM(
            api_key="fake-key",
            base_url="https://fake.api/v1",
            model_config=ModelConfig(model="test-model", temperature=0.4, max_tokens=512),
        )
        mock_client = AsyncMock()
        advisor._client = mock_client

        await advisor.close()

        mock_client.close.assert_awaited_once()
        assert advisor._client is None

    async def test_close_noop_without_client(self):
        advisor = AdvisorLLM(
            api_key="fake-key",
            base_url="https://fake.api/v1",
            model_config=ModelConfig(model="test-model", temperature=0.4, max_tokens=512),
        )
        # Should not raise
        await advisor.close()
