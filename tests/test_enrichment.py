from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from devcard.config import DevCardConfig
from devcard.enrichment import _serialize_devcard_for_llm, enrich_devcard
from devcard.enrichment.models import EnrichmentResponse
from devcard.enrichment.provider import _clean_json_response, _safe_format
from devcard.enrichment.text_cleaner import clean_llm_text
from devcard.models import (
    Activity,
    DevCard,
    Domain,
    Enriched,
    Expertise,
    FocusArea,
    Generator,
    Identity,
    Language,
    Project,
    Quality,
    Stack,
    StackItem,
)


def _make_devcard(**overrides) -> DevCard:
    defaults = dict(
        generated_at=datetime.now(UTC),
        generator=Generator(name="devcard", version="0.1.0"),
        identity=Identity(username="testdev", name="Test Dev", bio="I build things"),
        languages=[
            Language(name="Python", percentage=70.0, category="logic"),
            Language(name="TypeScript", percentage=30.0, category="logic"),
        ],
        projects=[
            Project(name="cool-ml", stars=100, language="Python",
                    topics=["machine-learning"], status="active"),
            Project(name="web-app", stars=20, language="TypeScript", status="maintained"),
        ],
        stack=Stack(
            frameworks=[StackItem(name="PyTorch", category="framework")],
            libraries=[StackItem(name="NumPy", category="library")],
        ),
        expertise=Expertise(
            domains=[Domain(name="Machine Learning", confidence=0.9)],
            profile_type="ml",
            focus_areas=[FocusArea(name="ML")],
        ),
        activity=Activity(status="active", commits_last_year=500, consistency_score=40),
        quality=Quality(score=0.5, ci_adoption=0.3, test_adoption=0.2,
                         docs_adoption=0.8, license_adoption=0.7, linter_adoption=0.1),
    )
    defaults.update(overrides)
    return DevCard(**defaults)


_MOCK_LLM_RESPONSE = json.dumps({
    "summary": "ML-focused Python developer building neural network tools",
    "archetype": "ML Craftsman",
    "strengths": [
        "Deep learning with PyTorch across multiple projects",
        "Strong documentation practices (80% adoption)",
        "Active contributor with 500+ commits/year",
    ],
    "suggestions": [
        "Add CI workflow to cool-ml - no GitHub Actions found",
        "Improve test coverage - only 20% of repos have tests",
        "Add linter config for consistent code style",
    ],
    "project_highlights": [
        {
            "name": "cool-ml",
            "reason": "Core ML project with custom training",
            "significance": "flagship",
        },
        {"name": "web-app", "reason": "Shows full-stack versatility", "significance": "growing"},
    ],
})


class TestTextCleaner:
    def test_cleans_smart_quotes(self):
        assert clean_llm_text("“Hello”") == '"Hello"'

    def test_cleans_em_dash(self):
        assert clean_llm_text("foo—bar") == "foo-bar"

    def test_cleans_markdown_bold(self):
        assert clean_llm_text("**bold text**") == "bold text"

    def test_empty_string(self):
        assert clean_llm_text("") == ""

    def test_strips_extra_spaces(self):
        assert clean_llm_text("hello   world") == "hello world"


class TestProviderHelpers:
    def test_safe_format_replaces_placeholders(self):
        result = _safe_format("Hello {name}!", name="World")
        assert result == "Hello World!"

    def test_safe_format_preserves_json_braces(self):
        result = _safe_format('Schema: {schema} {"type": "object"}', schema="test")
        assert '{"type": "object"}' in result

    def test_clean_json_response_strips_markdown(self):
        raw = '```json\n{"key": "value"}\n```'
        assert _clean_json_response(raw) == '{"key": "value"}'

    def test_clean_json_response_plain(self):
        raw = '{"key": "value"}'
        assert _clean_json_response(raw) == '{"key": "value"}'


class TestEnrichmentResponse:
    def test_parses_valid_response(self):
        result = EnrichmentResponse.model_validate_json(_MOCK_LLM_RESPONSE)
        assert result.archetype == "ML Craftsman"
        assert len(result.strengths) == 3
        assert len(result.project_highlights) == 2
        assert result.project_highlights[0].significance == "flagship"


class TestSerializeForLLM:
    def test_includes_all_sections(self):
        dc = _make_devcard()
        data = json.loads(_serialize_devcard_for_llm(dc))
        assert "identity" in data
        assert "languages" in data
        assert "stack" in data
        assert "projects" in data
        assert "expertise" in data
        assert "activity" in data
        assert "quality" in data

    def test_minimal_devcard(self):
        dc = DevCard(
            generated_at=datetime.now(UTC),
            generator=Generator(name="devcard", version="0.1.0"),
            identity=Identity(username="minimal"),
        )
        data = json.loads(_serialize_devcard_for_llm(dc))
        assert data["identity"]["username"] == "minimal"
        assert "languages" not in data


class TestEnrichDevcard:
    async def test_returns_none_without_api_key(self):
        config = DevCardConfig(fireworks_api_key=None)
        result = await enrich_devcard(_make_devcard(), config)
        assert result is None

    @patch("devcard.enrichment.FireworksProvider.get_structured_output")
    @patch("devcard.enrichment.FireworksProvider.close", new_callable=AsyncMock)
    async def test_returns_enriched_with_mock(self, mock_close, mock_llm):
        mock_llm.return_value = EnrichmentResponse.model_validate_json(
            _MOCK_LLM_RESPONSE
        )
        config = DevCardConfig(fireworks_api_key="fake-key")
        result = await enrich_devcard(_make_devcard(), config)
        assert result is not None
        assert isinstance(result, Enriched)
        assert result.archetype == "ML Craftsman"
        assert len(result.strengths) == 3
        assert len(result.project_highlights) == 2

    @patch("devcard.enrichment.FireworksProvider.get_structured_output")
    @patch("devcard.enrichment.FireworksProvider.close", new_callable=AsyncMock)
    async def test_returns_none_on_failure(self, mock_close, mock_llm):
        mock_llm.side_effect = RuntimeError("API down")
        config = DevCardConfig(fireworks_api_key="fake-key")
        result = await enrich_devcard(_make_devcard(), config)
        assert result is None
