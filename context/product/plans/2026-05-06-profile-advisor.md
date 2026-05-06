# Profile Advisor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add `devcard advise <username>` — a YAML-rules-driven profile advisor that praises strengths, critiques weaknesses, and gives specific fix instructions, with optional LLM gap-filling via a proper provider abstraction.

**Architecture:** Three clean layers: (1) Typed Pydantic rule models loaded from YAML, (2) Pure-function rule engine operating on typed data, (3) LLM provider with proper ABC/Protocol base class. The advisor pipeline orchestrates these layers. All rendering is pure functions on typed output models.

**Tech Stack:** Python 3.12, Pydantic v2, PyYAML, Fireworks AI (via `openai` SDK), Typer CLI, Rich.

---

## Structural Principles

### Provider Abstraction
The current `FireworksProvider` is a concrete class with no base type. We'll introduce a `LLMProvider` Protocol so the advisor (and existing enrichment) can work with any compatible provider — Fireworks, OpenAI, local models, or mocks for testing.

```python
# src/devcard/enrichment/base.py
class LLMProvider(Protocol):
    async def get_structured_output(
        self, output_model: type[T], context: dict[str, Any],
        message: str, model_config: ModelConfig,
    ) -> T: ...
    async def close(self) -> None: ...
```

`FireworksProvider` already satisfies this — we just need to declare it as an explicit Protocol.

### Typed Rule Models
Rules aren't loose dicts — they're Pydantic models loaded from YAML:

```python
# src/devcard/advisor/models.py
class Condition(BaseModel):
    field: str              # context key to check
    operator: ConditionOp   # eq, gt, gte, lt, lte, is_true, is_false
    value: Any = None       # comparison value (None for is_true/is_false)

class AdvisorRule(BaseModel):
    category: AdvisorCategory
    conditions: list[Condition]  # ALL must match (AND logic)
    type: VerdictType
    severity: Severity | None = None
    message: str            # with {placeholder} support
    action: str | None = None
```

### Pure Functions Over Typed Data
- `build_context(devcard, scores) → AdvisorContext` — typed dataclass, not a loose dict
- `evaluate_rule(rule, context) → Verdict | None` — single rule, pure
- `evaluate_all_rules(rules, context) → list[Verdict]` — map over rules
- `format_message(template, context) → str` — placeholder substitution

---

## Task 1: LLM Provider Protocol + Refactor

**Files:**
- Create: `src/devcard/enrichment/base.py`
- Modify: `src/devcard/enrichment/provider.py` (minimal — just add Protocol awareness)
- Test: `tests/test_enrichment.py` (verify existing tests still pass)

**What to build:**

`base.py`:
```python
from __future__ import annotations
from typing import Any, Protocol, TypeVar
from pydantic import BaseModel
from devcard.enrichment.provider import ModelConfig

T = TypeVar("T", bound=BaseModel)

class LLMProvider(Protocol):
    async def get_structured_output(
        self, output_model: type[T], context: dict[str, Any],
        message: str, model_config: ModelConfig,
    ) -> T: ...

    async def close(self) -> None: ...
```

No changes to `FireworksProvider` needed — it already satisfies this Protocol structurally. The Protocol is for type-checking and dependency injection in the advisor.

**Verify:** `uv run pytest tests/test_enrichment.py -v` — all existing enrichment tests still pass.

**Commit:** `refactor: add LLMProvider protocol for provider abstraction`

---

## Task 2: Advisor Domain Models

**Files:**
- Create: `src/devcard/advisor/models.py` — typed rule + verdict models
- Create: `src/devcard/advisor/__init__.py` — package marker
- Modify: `src/devcard/models.py` — add `ProfileAdvice` output model

**What to build:**

`src/devcard/advisor/models.py` — internal typed models for rules:
```python
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
```

`src/devcard/models.py` — public output models (add before `DevCard`):
```python
class Verdict(BaseModel):
    category: str = Field(description="Advice category")
    type: Literal["praise", "critique", "suggestion"] = Field(description="Verdict type")
    message: str = Field(description="The advice text")
    action: str | None = Field(default=None, description="Specific fix instruction")
    severity: Literal["high", "medium", "low", "info"] | None = Field(default=None)

class ProfileAdvice(BaseModel):
    username: str = Field(description="GitHub username")
    human_score: int = Field(description="Human visibility score 0-100")
    agent_score: int = Field(description="Agent readiness score 0-100")
    verdicts: list[Verdict] = Field(default_factory=list)
    summary: str | None = Field(default=None, description="LLM-generated summary")
```

**Commit:** `feat: add typed advisor domain models and ProfileAdvice output model`

---

## Task 3: Advisor Rules YAML

**Files:**
- Create: `mappings/advisor_rules.yaml`

**Structure:** ~30 rules across 6 categories. Each rule is a typed `AdvisorRule` when loaded.

Categories and example rules:

**profile** (6 rules): bio empty/present, followers thresholds, hireable flag, social links
**repos** (5 rules): no repos, few stars, signature project, many forks
**activity** (5 rules): dormant/active status, consistency score, streaks
**documentation** (5 rules): README depth, install sections, code blocks, images
**quality** (5 rules): test adoption, CI adoption, linter adoption, commit quality, conventional commits
**collaboration** (5 rules): reviews given, notable contributions, org membership, external contributions

Each rule uses condition operators matching the `ConditionOp` enum.

**Commit:** `feat: add advisor rules YAML with ~30 rules across 6 categories`

---

## Task 4: Rule Engine (Pure Functions)

**Files:**
- Create: `src/devcard/advisor/context.py` — build typed context from DevCard
- Create: `src/devcard/advisor/engine.py` — evaluate rules against context
- Test: `tests/test_advisor_engine.py`

**What to build:**

`context.py`:
```python
from dataclasses import dataclass
from devcard.models import DevCard

@dataclass(frozen=True)
class AdvisorContext:
    """Flat, typed snapshot of DevCard data for rule evaluation."""
    # Profile
    bio_empty: bool
    followers: int
    public_repos: int
    has_blog: bool
    has_twitter: bool
    hireable: bool
    # Activity
    activity_status: str  # "active", "moderate", "sporadic", "dormant"
    consistency_score: int
    commits_last_year: int
    # Quality
    quality_score: float
    ci_adoption: float
    test_adoption: float
    docs_adoption: float
    linter_adoption: float
    # Commit quality
    avg_message_length: float
    conventional_commits_pct: float
    multiline_pct: float
    # README depth
    readme_avg_word_count: float
    has_code_blocks_pct: float
    has_install_section_pct: float
    has_images_pct: float
    # Collaboration
    reviews_given: int
    notable_count: int
    orgs_count: int
    external_contributions: int
    # Lines
    total_lines_added: int
    total_lines_deleted: int
    # Coding habits
    indentation: str  # "spaces", "tabs", "mixed", "unknown"
    avg_line_length: float
    # Scores
    human_score: int
    agent_score: int

def build_context(devcard: DevCard, human_score: int, agent_score: int) -> AdvisorContext:
    """Extract flat context from DevCard. Safe defaults for missing data."""
    ...
```

`engine.py`:
```python
from devcard.advisor.models import AdvisorRule, Condition, ConditionOp
from devcard.advisor.context import AdvisorContext
from devcard.models import Verdict

def load_rules() -> list[AdvisorRule]:
    """Load and parse advisor_rules.yaml into typed models."""
    ...

def evaluate_condition(condition: Condition, context: AdvisorContext) -> bool:
    """Evaluate a single condition against context. Pure function."""
    value = getattr(context, condition.field, None)
    match condition.operator:
        case ConditionOp.eq: return value == condition.value
        case ConditionOp.gt: return value > condition.value
        ...

def evaluate_rule(rule: AdvisorRule, context: AdvisorContext) -> Verdict | None:
    """Evaluate all conditions in a rule. Returns Verdict if all match, None otherwise."""
    ...

def evaluate_all_rules(rules: list[AdvisorRule], context: AdvisorContext) -> list[Verdict]:
    """Evaluate all rules, return matching verdicts."""
    ...

def format_message(template: str, context: AdvisorContext) -> str:
    """Replace {field} placeholders with context values."""
    ...
```

**Tests** (`tests/test_advisor_engine.py`):
- `test_build_context_from_full_devcard` — all fields populated
- `test_build_context_handles_missing_data` — None extractors → safe defaults
- `test_condition_eq` / `test_condition_gt` / `test_condition_is_true` — each operator
- `test_rule_all_conditions_must_match` — AND logic
- `test_rule_returns_none_on_mismatch`
- `test_evaluate_all_rules_filters_matching`
- `test_format_message_replaces_placeholders`
- `test_load_rules_parses_yaml`

**Commit:** `feat: add typed rule engine with context builder`

---

## Task 5: LLM Advisor (Optional Gap-Filler)

**Files:**
- Create: `src/devcard/advisor/llm_advisor.py`
- Create: `src/devcard/enrichment/prompts/advisor.md`
- Test: `tests/test_advisor_llm.py`

**What to build:**

`llm_advisor.py`:
```python
from devcard.enrichment.base import LLMProvider
from devcard.enrichment.provider import FireworksProvider, ModelConfig
from devcard.models import DevCard, Verdict

class AdvisorLLM:
    """LLM-powered advice summary generator."""

    def __init__(self, provider: LLMProvider, model_config: ModelConfig):
        self._provider = provider
        self._model_config = model_config

    async def generate_summary(
        self, devcard: DevCard, verdicts: list[Verdict],
    ) -> str | None:
        """Generate cohesive 2-3 sentence summary from DevCard + verdicts."""
        ...

    @classmethod
    def from_config(cls, config: DevCardConfig) -> AdvisorLLM | None:
        """Factory: returns None if no API key configured."""
        if not config.fireworks_api_key:
            return None
        provider = FireworksProvider(config.fireworks_api_key, config.fireworks_base_url)
        model_config = ModelConfig(model=config.llm_model, temperature=0.4, max_tokens=512)
        return cls(provider, model_config)
```

`prompts/advisor.md`:
System prompt that receives DevCard data + existing rule verdicts. Instructs LLM to write a cohesive 2-3 sentence profile summary and identify 1-2 gaps the rules missed.

**Tests:** Mock the provider, verify summary generation works, verify None when no API key.

**Commit:** `feat: add LLM advisor with prompt template and provider injection`

---

## Task 6: Advise Pipeline

**Files:**
- Modify: `src/devcard/advisor/__init__.py` — main pipeline
- Test: `tests/test_advisor_pipeline.py`

**What to build:**

```python
async def advise_pipeline(
    username: str, config: DevCardConfig, *, enrich: bool = False,
) -> ProfileAdvice:
    """Generate profile advice: rules-based verdicts + optional LLM summary."""
    # 1. Generate DevCard
    devcard = await generate_devcard(username, config)
    # 2. Compute scores
    profile = await _fetch_profile_repo_data(client, username)
    human_score = compute_human_visibility_score(devcard, profile)
    agent_score = compute_agent_readiness_score(devcard, profile)
    # 3. Build context + evaluate rules
    context = build_context(devcard, human_score, agent_score)
    rules = load_rules()
    verdicts = evaluate_all_rules(rules, context)
    # 4. Optional LLM summary
    summary = None
    if enrich:
        llm = AdvisorLLM.from_config(config)
        if llm:
            summary = await llm.generate_summary(devcard, verdicts)
    # 5. Return typed result
    return ProfileAdvice(
        username=username, human_score=human_score,
        agent_score=agent_score, verdicts=verdicts, summary=summary,
    )
```

**Commit:** `feat: add advise pipeline orchestration`

---

## Task 7: CLI Command + Renderers

**Files:**
- Modify: `src/devcard/cli.py` — add `advise` command
- Create: `src/devcard/renderers/advice.py` — terminal + markdown renderers
- Test: `tests/test_cli.py` (add advise test), `tests/test_advice_renderer.py`

**Terminal renderer:** Scores panel at top → verdicts grouped by category → color-coded (green=praise, red=critique, yellow=suggestion) → optional LLM summary at bottom.

**Markdown renderer:** Header with scores → sections per category → table of verdicts → summary block.

**CLI command:**
```python
@app.command()
def advise(username, token, format="terminal", enrich=False, model=None, no_cache=False, verbose=False):
```

**Commit:** `feat: add devcard advise CLI command with terminal and markdown renderers`

---

## Task 8: JSON Schema + Final Polish

**Files:**
- Modify: `schema/devcard.v1.schema.json`

Add `Verdict` and `ProfileAdvice` definitions.

**Commit:** `feat: add Verdict and ProfileAdvice to JSON schema`

---

## Verification

1. `uv run pytest tests/` — all pass
2. `uv run ruff check src/ tests/` — clean
3. `uv run devcard advise <username>` — rules-only: scores + categorized verdicts
4. `uv run devcard advise <username> --enrich` — adds LLM summary
5. `uv run devcard advise <username> --format json` — machine-readable output
6. `uv run devcard advise <username> --format markdown` — GFM output
