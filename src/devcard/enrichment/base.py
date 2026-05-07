"""Abstract LLM provider protocol for dependency injection."""

from __future__ import annotations

from typing import Any, Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel

from devcard.enrichment.provider import ModelConfig

T = TypeVar("T", bound=BaseModel)


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for LLM providers that return structured Pydantic output.

    Any class implementing ``get_structured_output`` and ``close`` with
    compatible signatures satisfies this protocol.  ``FireworksProvider``
    already does so — no changes required.
    """

    async def get_structured_output(
        self,
        output_model: type[T],
        context: dict[str, Any],
        message: str,
        model_config: ModelConfig,
    ) -> T: ...

    async def close(self) -> None: ...
