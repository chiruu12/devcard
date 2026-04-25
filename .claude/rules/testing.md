---
paths:
  - "tests/**/*.py"
---

# Testing Conventions

## Rules
- Never hit the real GitHub API in tests — always use `httpx.MockTransport` or fixture JSON files
- Fixture files in `tests/fixtures/` are JSON files that mirror real GitHub API responses. Capture real responses once, commit them, use them forever.
- Name fixture files after the API endpoint: `user_torvalds.json`, `repos_torvalds.json`, `repo_languages_linux.json`
- Test each extractor independently with minimal fixture data — only include the fields that extractor actually reads
- Test analyzers with constructed Pydantic models, not raw JSON — they consume extractor output, not API responses
- Test renderers by asserting structural properties (SVG: valid XML, no foreignObject, size <50KB; terminal: contains expected sections; markdown: valid GFM)
- Mark slow tests (full pipeline integration) with `@pytest.mark.slow`
- Use `pytest-asyncio` for all async tests. Use `@pytest.mark.asyncio` decorator.
- CLI tests use `typer.testing.CliRunner` — test commands produce expected output and exit codes
- Parametrize extractor tests across multiple fixture profiles when testing edge cases (e.g., user with no repos, user with only forks, user with 100+ repos)
