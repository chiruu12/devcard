# Design: Profile Advisor (`devcard advise`)

## Context

DevCard generates developer identity cards with 14+ extractors covering identity, languages, stack, activity, projects, collaboration, quality, expertise, coding habits, code reviews, lines changed, commit quality, README depth, and responsiveness. It also has an audit pipeline (dual scoring) and issue detector.

The Profile Advisor adds a new layer: actionable, personalized advice that praises what's good and critiques what needs work, with specific fix instructions. It uses a YAML rules engine for deterministic verdicts and an optional LLM (Fireworks AI) for personalized summaries.

## Architecture

```
CLI: devcard advise <username> [--enrich] [--format] [--token]
MCP: advise_profile(username)
        ↓
    advise_pipeline(username, config, enrich=False)
        ↓
    1. generate_devcard() → full DevCard
    2. audit scores (human_visibility + agent_readiness)
    3. Rule engine: YAML rules → pre-written Verdicts
    4. LLM (if --enrich): gap-fill + cohesive summary
        ↓
    ProfileAdvice (structured output)
        ↓
    Renderers: terminal (rich), markdown, JSON
```

## YAML Rules Engine

File: `mappings/advisor_rules.yaml`

Rules organized by category, each with:
- `condition`: expression evaluated against DevCard data
- `type`: praise | critique | suggestion
- `severity`: high | medium | low | info (for critiques/suggestions)
- `message`: pre-written text with `{variable}` placeholders
- `action`: specific fix instruction (for critiques)

Categories: profile, repos, activity, documentation, quality, collaboration

Condition syntax: simple Python-evaluable expressions against a flat context dict built from DevCard fields (e.g., `bio_length == 0`, `followers >= 100`, `conventional_commits_pct >= 80`).

## LLM Layer (Optional)

Prompt: `src/devcard/enrichment/prompts/advisor.md`

Input to LLM:
- Serialized DevCard JSON
- Rule-engine verdicts already generated
- Instructions to write a cohesive 2-3 sentence summary and fill any gaps

Uses existing `FireworksProvider` with structured output.

## Data Model

```python
class Verdict(BaseModel):
    category: str
    type: Literal["praise", "critique", "suggestion"]
    message: str
    action: str | None = None
    severity: Literal["high", "medium", "low", "info"] | None = None

class ProfileAdvice(BaseModel):
    username: str
    human_score: int
    agent_score: int
    verdicts: list[Verdict]
    summary: str | None = None
```

## Implementation Steps

1. Add Verdict + ProfileAdvice models to models.py
2. Create mappings/advisor_rules.yaml with ~20-30 rules across 6 categories
3. Create src/devcard/advisor/ package:
   - rule_engine.py: load YAML, evaluate conditions, produce Verdicts
   - __init__.py: advise_pipeline() orchestration
4. Create src/devcard/enrichment/prompts/advisor.md
5. Add `devcard advise` CLI command
6. Add terminal + markdown renderers for ProfileAdvice
7. Tests for rule engine, pipeline, and renderers
8. Wire MCP tool (devcard-mcp)

## Verification

1. `devcard advise <username>` — rules-only output with scores + verdicts
2. `devcard advise <username> --enrich` — rules + LLM summary
3. `devcard advise <username> --format json` — machine-readable
4. All tests pass, lint clean
