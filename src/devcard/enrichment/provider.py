"""Fireworks AI provider with structured output support.

Follows the Sofia workspace pattern: AsyncOpenAI client with Fireworks
base URL, Pydantic structured output via JSON schema injection, retry
with exponential backoff.
"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from devcard.enrichment.text_cleaner import clean_llm_text

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_MAX_RETRIES = 2
_BACKOFF_BASE = 0.5
_PROMPT_PATH = Path(__file__).parent / "prompt.md"


@dataclass(frozen=True)
class ModelConfig:
    model: str
    temperature: float = 0.3
    max_tokens: int = 1024


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def _safe_format(template: str, **kwargs: Any) -> str:
    content = template
    for key, value in kwargs.items():
        placeholder = f"{{{key}}}"
        if placeholder in content:
            content = content.replace(placeholder, str(value) if value is not None else "")
    return content


def _clean_json_response(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [line for line in lines[1:] if not line.strip().startswith("```")]
        cleaned = "\n".join(lines)
    return cleaned.strip()


class FireworksProvider:

    def __init__(self, api_key: str, base_url: str):
        self._api_key = api_key
        self._base_url = base_url
        self._client = None
        self._lock = asyncio.Lock()

    async def _get_client(self):
        if self._client is None:
            async with self._lock:
                if self._client is None:
                    try:
                        from openai import AsyncOpenAI
                    except ImportError:
                        raise RuntimeError(
                            "openai package required for enrichment. "
                            "Install with: uv sync --extra enrich"
                        )
                    self._client = AsyncOpenAI(
                        api_key=self._api_key,
                        base_url=self._base_url,
                    )
        return self._client

    def _clean_model(self, model: T) -> T:
        for field_name in model.model_fields:
            value = getattr(model, field_name)
            if isinstance(value, str):
                object.__setattr__(model, field_name, clean_llm_text(value))
            elif isinstance(value, list):
                cleaned = []
                for v in value:
                    if isinstance(v, str):
                        cleaned.append(clean_llm_text(v))
                    elif isinstance(v, BaseModel):
                        cleaned.append(self._clean_model(v))
                    else:
                        cleaned.append(v)
                object.__setattr__(model, field_name, cleaned)
            elif isinstance(value, BaseModel):
                self._clean_model(value)
        return model

    async def _call_llm(
        self,
        system: str,
        message: str,
        model_config: ModelConfig,
    ) -> str:
        client = await self._get_client()
        last_err: Exception | None = None

        system_content = system + "\n\nRespond with valid JSON only."

        for attempt in range(_MAX_RETRIES + 1):
            try:
                response = await client.chat.completions.create(
                    model=model_config.model,
                    temperature=model_config.temperature,
                    max_tokens=model_config.max_tokens,
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
                    delay = _BACKOFF_BASE * (2 ** attempt)
                    logger.warning(
                        "LLM call attempt %d failed (%s), retrying in %.1fs",
                        attempt + 1, exc, delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error("LLM call failed after %d attempts: %s", _MAX_RETRIES + 1, exc)

        raise last_err  # type: ignore[misc]

    async def get_structured_output(
        self,
        output_model: type[T],
        context: dict[str, Any],
        message: str,
        model_config: ModelConfig,
    ) -> T:
        template = _load_prompt()
        schema_str = json.dumps(output_model.model_json_schema(), indent=2)
        system = _safe_format(template, output_schema=schema_str, **context)

        raw = await self._call_llm(system, message, model_config)
        cleaned = _clean_json_response(raw)

        try:
            result = output_model.model_validate_json(cleaned)
        except ValidationError:
            start = cleaned.find("{")
            end = cleaned.rfind("}") + 1
            if start >= 0 and end > start:
                result = output_model.model_validate_json(cleaned[start:end])
            else:
                logger.error("LLM returned invalid JSON: %s", cleaned[:200])
                raise
        return self._clean_model(result)

    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None
