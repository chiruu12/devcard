"""Pydantic schemas for structured LLM responses."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ProjectHighlightResponse(BaseModel):
    name: str = Field(description="Repository name (must match an existing project)")
    reason: str = Field(description="1 sentence: why this project matters")
    significance: Literal["flagship", "growing", "hidden gem"] = Field(
        description="flagship=best work, growing=rising potential, hidden gem=underrated"
    )


class EnrichmentResponse(BaseModel):
    summary: str = Field(
        description="1-2 sentence developer narrative. Be specific, cite evidence."
    )
    archetype: str = Field(
        description="Creative 2-3 word developer label (e.g. 'ML Craftsman', 'Full-Stack Polyglot')"
    )
    strengths: list[str] = Field(
        description="Exactly 3 strengths. Each is 1 short sentence with evidence."
    )
    suggestions: list[str] = Field(
        description="Exactly 3 growth areas. Each is 1 actionable sentence."
    )
    project_highlights: list[ProjectHighlightResponse] = Field(
        description="Top 3 projects ranked by actual significance, not just stars."
    )
