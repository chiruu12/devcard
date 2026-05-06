from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ConditionOp(StrEnum):
    eq = "eq"
    gt = "gt"
    gte = "gte"
    lt = "lt"
    lte = "lte"
    is_true = "is_true"
    is_false = "is_false"


class VerdictType(StrEnum):
    praise = "praise"
    critique = "critique"
    suggestion = "suggestion"


class Severity(StrEnum):
    high = "high"
    medium = "medium"
    low = "low"
    info = "info"


class AdvisorCategory(StrEnum):
    profile = "profile"
    repos = "repos"
    activity = "activity"
    documentation = "documentation"
    quality = "quality"
    collaboration = "collaboration"


class Condition(BaseModel):
    field: str = Field(description="Context key to evaluate")
    operator: ConditionOp = Field(description="Comparison operator")
    value: Any = Field(default=None, description="Value to compare against")


class AdvisorRule(BaseModel):
    category: AdvisorCategory
    conditions: list[Condition]
    type: VerdictType
    severity: Severity | None = None
    message: str = Field(description="Advice text with {placeholder} support")
    action: str | None = None
