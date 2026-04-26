# How We Work

## Development Workflow

```mermaid
flowchart LR
    Plan --> Implement --> Review[Code Review] --> Retro
```

| Step | Powered By | Modulated By |
|------|-----------|-------------|
| **Plan** | `superpowers` plugin (writing-plans, brainstorming) | `workflow-conventions` rule |
| **Implement** | `superpowers` plugin (executing-plans, test-driven-development) | `workflow-conventions` rule |
| **Code Review** | `superpowers` plugin (requesting-code-review) + `code-review` plugin | `workflow-conventions` rule |
| **Retro** | Custom `/retro` skill | `feedback-loop` rule |

## When Adding Features

1. Plan first (use plan mode for non-trivial changes)
2. Plan gets written to `context/product/plans/`
3. Implement with tests alongside code
4. Code review before handoff
5. Verify: `uv run pytest` + `uv run ruff check src/ tests/`
6. Open PR, merge
7. Log decisions in `context/product/decisions.md`

## Session Continuity

- Reference `context/product/decisions.md` before proposing alternatives to past decisions
- Reference `CLAUDE.md` for project conventions
- Read `context/process/learnings.md` for technical gotchas
