# DevCard Tech Stack

## Core
- **Language**: Python 3.11+
- **Package Manager**: uv
- **CLI Framework**: typer (with Rich integration)
- **HTTP Client**: httpx (async)
- **Data Validation**: pydantic v2
- **Caching**: diskcache (local filesystem)
- **Terminal UI**: Rich
- **YAML Parsing**: PyYAML
- **Schema Validation**: jsonschema

## Optional
- **LLM Enrichment**: litellm (optional `[enrich]` extra)
- **PNG Export**: CairoSVG (optional `[png]` extra)

## Development
- **Testing**: pytest, pytest-asyncio
- **Linting/Formatting**: ruff
- **Build Backend**: hatchling (src layout)

## Infrastructure
- None. DevCard is a pure CLI tool with no server, database, or container dependencies.
- Caching uses local filesystem via diskcache (default: `~/.cache/devcard/`)
