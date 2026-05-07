"""LLM-powered advisor summary generator.

Loads the advisor prompt template, serializes DevCard + verdicts into
compact context, calls the LLM directly via AsyncOpenAI, and parses the
structured response into a cohesive summary string.
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from devcard.config import DevCardConfig
from devcard.enrichment.provider import ModelConfig, _clean_json_response, _safe_format
from devcard.enrichment.text_cleaner import clean_llm_text
from devcard.models import DevCard, Verdict

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).resolve().parent.parent / "enrichment" / "prompts" / "advisor.md"

_MAX_RETRIES = 1
_BACKOFF_BASE = 0.5


class AdvisorSummaryResponse(BaseModel):
    """Structured response from the LLM advisor."""

    summary: str = Field(
        description="2-3 sentence cohesive profile summary, under 80 words",
    )
    gaps: list[str] = Field(
        default_factory=list,
        max_length=2,
        description="1-2 gaps the rule-based verdicts missed",
    )


def _load_advisor_prompt() -> str:
    """Load the advisor system prompt template."""
    return _PROMPT_PATH.read_text(encoding="utf-8")


def _serialize_for_llm(devcard: DevCard) -> str:
    """Serialize DevCard into compact JSON for LLM context.

    Includes identity, top 5 languages, top 3 projects, quality scores,
    activity status, and commit quality. Keeps the payload small to stay
    within token budgets.
    """
    data: dict[str, Any] = {}

    data["identity"] = {
        "username": devcard.identity.username,
        "name": devcard.identity.name,
        "bio": devcard.identity.bio,
        "followers": devcard.identity.followers,
        "public_repos": devcard.identity.public_repos,
    }

    if devcard.languages:
        data["languages"] = [
            {"name": lang.name, "percentage": lang.percentage}
            for lang in devcard.languages[:5]
        ]

    if devcard.projects:
        data["projects"] = [
            {
                "name": p.name,
                "description": p.description,
                "stars": p.stars,
                "language": p.language,
                "status": p.status,
            }
            for p in devcard.projects[:3]
        ]

    if devcard.quality:
        data["quality"] = {
            "score": devcard.quality.score,
            "ci_adoption": devcard.quality.ci_adoption,
            "test_adoption": devcard.quality.test_adoption,
            "docs_adoption": devcard.quality.docs_adoption,
        }

    if devcard.activity:
        data["activity"] = {
            "status": devcard.activity.status,
            "commits_last_year": devcard.activity.commits_last_year,
            "consistency_score": devcard.activity.consistency_score,
        }

    if devcard.commit_quality:
        data["commit_quality"] = {
            "avg_message_length": devcard.commit_quality.avg_message_length,
            "conventional_commits_pct": devcard.commit_quality.conventional_commits_pct,
        }

    return json.dumps(data, indent=2, default=str)


class AdvisorLLM:
    """LLM-powered advice summary generator.

    Creates its own AsyncOpenAI client to call the LLM with the advisor
    prompt template, independent of the enrichment prompt used by
    FireworksProvider.get_structured_output.
    """

    def __init__(self, api_key: str, base_url: str, model_config: ModelConfig):
        self._api_key = api_key
        self._base_url = base_url
        self._model_config = model_config
        self._client: Any = None
        self._lock = asyncio.Lock()

    async def _get_client(self) -> Any:
        """Lazy-init the AsyncOpenAI client (same pattern as FireworksProvider)."""
        if self._client is None:
            async with self._lock:
                if self._client is None:
                    try:
                        from openai import AsyncOpenAI
                    except ImportError:
                        raise RuntimeError(
                            "openai package required for LLM advisor. "
                            "Install with: uv sync --extra enrich"
                        )
                    self._client = AsyncOpenAI(
                        api_key=self._api_key,
                        base_url=self._base_url,
                    )
        return self._client

    async def _call_llm(self, system: str, message: str) -> str:
        """Call the LLM with retry logic."""
        client = await self._get_client()
        last_err: Exception | None = None
        system_content = system + "\n\nRespond with valid JSON only."

        for attempt in range(_MAX_RETRIES + 1):
            try:
                response = await client.chat.completions.create(
                    model=self._model_config.model,
                    temperature=self._model_config.temperature,
                    max_tokens=self._model_config.max_tokens,
                    messages=[
                        {"role": "system", "content": system_content},
                        {"role": "user", "content": message},
                    ],
                    response_format={"type": "json_object"},
                )
                return response.choices[0].message.content or ""
            except Exception as exc:
                last_err = exc
                if attempt < _MAX_RETRIES:
                    delay = _BACKOFF_BASE * (2**attempt)
                    logger.warning(
                        "Advisor LLM attempt %d failed (%s), retrying in %.1fs",
                        attempt + 1,
                        exc,
                        delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "Advisor LLM failed after %d attempts: %s",
                        _MAX_RETRIES + 1,
                        exc,
                    )

        raise last_err  # type: ignore[misc]

    async def generate_summary(
        self,
        devcard: DevCard,
        verdicts: list[Verdict],
    ) -> str | None:
        """Generate a cohesive summary from DevCard + verdicts.

        Returns the summary string (with optional gap observations appended),
        or None on failure.
        """
        try:
            devcard_data = _serialize_for_llm(devcard)
            verdicts_data = json.dumps(
                [v.model_dump(exclude_none=True) for v in verdicts],
                indent=2,
            )
            schema_str = json.dumps(
                AdvisorSummaryResponse.model_json_schema(), indent=2,
            )

            template = _load_advisor_prompt()
            system = _safe_format(
                template,
                devcard_data=devcard_data,
                verdicts_data=verdicts_data,
                output_schema=schema_str,
            )

            raw = await self._call_llm(
                system,
                f"Analyze the GitHub profile for {devcard.identity.username} and generate advice.",
            )
            cleaned = _clean_json_response(raw)

            try:
                parsed = json.loads(cleaned)
            except json.JSONDecodeError:
                start = cleaned.find("{")
                end = cleaned.rfind("}") + 1
                if start >= 0 and end > start:
                    parsed = json.loads(cleaned[start:end])
                else:
                    logger.error("Advisor LLM returned invalid JSON: %s", cleaned[:200])
                    raise

            result = AdvisorSummaryResponse.model_validate(parsed)
            summary = clean_llm_text(result.summary)

            if result.gaps:
                gap_text = " ".join(clean_llm_text(g) for g in result.gaps)
                summary = f"{summary}\n\nAdditional observations: {gap_text}"

            return summary

        except Exception:
            logger.warning("LLM advisor failed", exc_info=True)
            return None

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client:
            await self._client.close()
            self._client = None

    @classmethod
    def from_config(cls, config: DevCardConfig) -> AdvisorLLM | None:
        """Factory: returns None if no API key is configured."""
        if not config.fireworks_api_key:
            return None
        model_config = ModelConfig(
            model=config.llm_model,
            temperature=0.4,
            max_tokens=512,
        )
        return cls(
            api_key=config.fireworks_api_key,
            base_url=config.fireworks_base_url,
            model_config=model_config,
        )
