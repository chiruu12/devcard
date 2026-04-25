---
paths:
  - "src/devcard/cli.py"
---

# CLI Conventions

## Rules
- Keep the CLI layer thin — validation, argument parsing, then call the pipeline. No business logic.
- Use typer for all commands and options. Use `typer.Option` with `help=` for all flags.
- All output to stderr for progress/status (via Rich console). Only the final result goes to stdout.
- This enables piping: `devcard generate torvalds --format json | jq .identity`
- File output uses `-o`/`--output` flag. When omitted, write to stdout.
- Token resolution: `--token` flag > `GITHUB_TOKEN` env var > `gh auth token`. Show a Rich warning panel if no token found.
- Use `asyncio.run()` to bridge sync typer commands to async pipeline.
- Error handling: catch pipeline errors, display Rich error panels, exit with code 1. Never show raw tracebacks to users.
- Global options (token, cache-dir, no-cache, verbose) go on the top-level app, not per-command.
