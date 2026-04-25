# Workflow Conventions

Project-specific conventions that guide how superpowers plugin skills behave in this project.

## Planning

- Plans MUST be written to `context/product/plans/<prefix>-plan.md`
  - `<prefix>` is a descriptive slug (e.g., `stack-extractor`, `svg-renderer`, `github-action`)
  - Ask the user which prefix to use if unclear
- If a plan exists in `.claude/plans/` but not in `context/product/plans/`, persist it using `/persist-plan`
- Plans should include:
  - Measurable outcomes (concrete yes/no statements)
  - Alternatives evaluation when multiple approaches exist
  - Execution strategy: chunking and sequencing
  - Testing strategy

## Pre-commit Hooks

pre-commit runs ruff check + ruff format on staged Python files. Do NOT run ruff manually before committing — the hook handles it. If the hook fails, read the errors and fix them before retrying.

## Implementation

- Read relevant existing files before writing anything
- Write tests alongside code, not after
- Coverage target: ~80% of new code
- Test all extractors, analyzers, and renderers. Do NOT test: Pydantic model construction, YAML loading, trivial CLI wiring.
- Run ALL tests before requesting user help
- Stay focused on the plan — do not refactor unrelated code
- If stuck, say so — don't brute-force

## Code Review

- After tests pass, run a code review before presenting results to the user
- Fix issues found by the reviewer before handoff

## Commit Discipline

Commit early and often. Key checkpoints:
- **After planning**: commit the plan file
- **After implementation**: organize into logical commits (one per extractor, one per renderer, etc.)
- **After code review**: commit fixes separately
- **After retro/learnings**: commit context/ changes

Use descriptive commit messages that explain *why*, not just *what*.

## Diagrams

- Use mermaid for all diagrams (architecture, workflows, dependencies)
