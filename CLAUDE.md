# Project: DevCard

## Overview

DevCard auto-generates structured, agent-readable developer identity cards from any public GitHub username. No sign-up. No LLM required. Paste a username — get a visual card (SVG), structured JSON (`devcard.json`), terminal output, and markdown summary. The JSON schema is the long-term protocol; the visual card drives adoption. This is a Python CLI tool, not a web service.

## Architecture

Three-layer architecture — schema/engine, visual, ecosystem:

```
CLI (typer) → Pipeline/Orchestrator
                ├── GitHub Client (async httpx, rate-limited, cached via diskcache)
                ├── Extractors (async, each returns Pydantic model)
                │     identity, languages, stack, activity, projects,
                │     collaboration, quality, expertise
                ├── Analyzers (classify dev type, contribution style, scoring)
                │     developer_type, project_classifier, contribution_style, scoring
                ├── Renderers (SVG, HTML, terminal, markdown, PNG)
                │     svg_card, html_profile, terminal, markdown, png + themes/
                └── Enrichment (optional LLM via litellm)

Mappings (YAML lookup tables: dependencies, topics, file patterns, dev type rules)
Schema (JSON Schema Draft 2020-12 for devcard.json)
```

Key flow: CLI invokes pipeline → pipeline creates GitHub client → fetches user + repos → fans out extractors concurrently (`asyncio.gather`) → runs analyzers on extractor output → renders output in requested format(s).

## Key Files

| Path | Purpose |
|------|---------|
| `src/devcard/cli.py` | Typer CLI entry point, all commands |
| `src/devcard/pipeline.py` | Orchestrator: assembles extractors, analyzers, renderers |
| `src/devcard/models.py` | Core Pydantic models (DevCard, Identity, Language, Stack, etc.) |
| `src/devcard/config.py` | DevCardConfig: token, cache dir, limits |
| `src/devcard/github/client.py` | Async httpx client with rate limiting + caching |
| `src/devcard/github/models.py` | GitHub API response models |
| `src/devcard/github/cache.py` | diskcache wrapper |
| `src/devcard/extractors/` | One file per signal: identity, languages, stack, activity, projects, collaboration, quality, expertise |
| `src/devcard/analyzers/` | developer_type, project_classifier, contribution_style, scoring |
| `src/devcard/renderers/` | svg_card, html_profile, terminal, markdown, png + themes/ |
| `src/devcard/enrichment/` | Optional LLM enrichment via litellm |
| `src/devcard/output/` | json_output, yaml_output serializers |
| `src/devcard/validators/` | JSON Schema validation |
| `mappings/` | YAML lookup tables (dependencies, topics, file patterns, dev type rules) |
| `schema/devcard.v1.schema.json` | JSON Schema for devcard.json |
| `schema/examples/` | Example devcard.json files |
| `tests/` | pytest tests |
| `tests/fixtures/` | Mock GitHub API response JSON files |
| `pyproject.toml` | Project config, deps, entry point |
| `context/` | Architecture docs, decisions, learnings |

## Development

No Makefile, Docker, or database. This is a pure CLI tool. All commands use `uv run`.

```bash
uv sync                                          # Install dependencies
uv sync --extra enrich --extra png                # Install with optional deps
uv run devcard --help                             # Show CLI help
uv run devcard generate <username>                # Generate a devcard
uv run devcard generate <username> --token $GITHUB_TOKEN  # With auth (5000 req/hr vs 60)
uv run devcard generate <username> --format svg --theme dark  # SVG with theme
uv run devcard me                                 # Generate for current git user
uv run devcard validate <file>                    # Validate devcard.json against schema
uv run pytest                                     # Run all tests
uv run pytest tests/test_extractors/              # Run extractor tests
uv run pytest -k "test_stack"                     # Run specific tests
uv run ruff check src/ tests/                     # Lint check
uv run ruff check --fix src/ tests/               # Auto-fix lint
uv run ruff format src/ tests/                    # Format code
```

## Testing

- All tests in `tests/` using pytest + pytest-asyncio
- Mock GitHub API responses via `httpx.MockTransport` — never hit real APIs in tests
- Fixtures in `tests/fixtures/` are JSON files mirroring real GitHub API responses
- Mark slow tests (integration, full pipeline) with `@pytest.mark.slow`
- SVG tests: parse with `xml.etree.ElementTree`, assert no foreignObject, check size <50KB
- CLI tests with `typer.testing.CliRunner`

## Conventions

### Before Making Changes
- Read the relevant file(s) first — before creating any new file, read an existing file of the same type to match patterns
- Check `context/product/decisions.md` for prior decisions on the topic
- Check `context/process/learnings.md` for known gotchas

### After Making Changes
- If the change involved a non-obvious decision, log it in `context/product/decisions.md`
- If we learned something useful, add it to `context/process/learnings.md`
- Run `uv run pytest` to verify nothing breaks. Fix any broken tests before reporting the change as done.
- Run `uv run ruff check src/ tests/` to ensure code quality. Fix any lint issues before reporting the change as done.

@context/process/learnings.md
