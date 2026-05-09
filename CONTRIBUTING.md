# Contributing to DevCard

Thanks for your interest in contributing! Here are some ways to get involved.

## Getting Started

```bash
git clone https://github.com/chiruu12/devcard.git
cd devcard
uv sync --dev
uv run pytest tests/ -x -q
```

## Low-Barrier Contributions

### Add dependency mappings

`mappings/dependencies.yaml` maps package names to technologies. If your favorite framework is missing, add it:

```yaml
python:
  fastapi:
    name: FastAPI
    category: Web Framework
```

### Add advisor rules

`mappings/advisor_rules.yaml` defines profile improvement rules. Add a rule with a condition, severity, and message.

### Add SVG themes

Themes live in `src/devcard/renderers/themes/`. Copy an existing theme and modify colors. Register it in `cli.py:THEMES`.

## Development

```bash
uv run pytest tests/ -x -q     # Run tests
uv run ruff check src/ tests/   # Lint
uv run devcard generate <user>  # Test CLI
```

## Pull Requests

- One logical change per PR
- Include tests for new functionality
- Run `uv run pytest` and `uv run ruff check src/ tests/` before submitting
- Keep commit messages short and descriptive
