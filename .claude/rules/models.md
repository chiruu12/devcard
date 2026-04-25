---
paths:
  - "src/devcard/models.py"
  - "src/devcard/github/models.py"
---

# Model Conventions

## Pattern-Matching
Before writing a new model, read `src/devcard/models.py` to match existing patterns.

## Core DevCard Models (src/devcard/models.py)
- All fields must have `Field(description="...")` — these descriptions appear in the JSON Schema and serve as documentation for agent consumers
- Use `Optional[...]` with `default=None` for all non-essential fields — extractors may fail, and partial results are expected
- Use `list[X]` with `default_factory=list` for collection fields, never `None` for lists
- Enums: use lowercase snake_case string values (e.g., `FULL_STACK = "full_stack"`)
- Use `Literal` types for small fixed sets (e.g., activity status: `Literal["active", "moderate", "sporadic", "dormant"]`) rather than creating an enum
- Every model must be serializable to JSON via `model_dump_json(exclude_none=True)`
- Do not add computed properties or methods to models — they are pure data containers. Computation belongs in extractors/analyzers.

## GitHub API Models (src/devcard/github/models.py)
- Always use `model_config = ConfigDict(extra="ignore")` — GitHub API responses include many fields we don't use
- Field names must match the GitHub API JSON keys exactly (use `alias` if the Python name differs)
- These models are internal — they don't appear in the public devcard.json schema
