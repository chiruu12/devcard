# DevCard MCP Server — Full Experience Design

> Date: 2026-04-27
> Status: Approved
> Scope: Evolve DevCard from CLI-first to MCP-first with 8 tools, full GitHub write capability, and multi-agent distribution

## Problem

DevCard has a solid core engine (extractors, analyzers, renderers) and a basic MCP server with 4 read-only tools. But it can't audit profiles, detect issues, fix problems, or write anything back to GitHub. Developers have to manually interpret DevCard output and make changes themselves. The goal is a zero-friction experience: "audit my github" → see scores → "fix it" → done.

## Design Decisions

1. **Expand in-place** — keep two-package structure (`devcard` core + `devcard-mcp` wrapper), add fixers + new analyzers to core
2. **All 8 tools from day one** — audit, generate, analyze_repo, fix_profile, fix_repo, agent_ready, compare, render
3. **Broadest reach** — target all AI coding agents (Claude Code, Cursor, Copilot, Windsurf) via MCP
4. **Full dry-run + apply** — all fix tools preview changes before applying, dry_run=true by default
5. **Pure heuristics** — no LLM for fixers, deterministic and free
6. **GitHub REST API for writes** — no gh CLI dependency, works in Docker
7. **Dual packaging** — Python (uvx) + npm (@devcard/mcp-server) from day one

## Architecture

```
devcard (core)                               devcard-mcp (wrapper)
├── github/client.py  + write methods        ├── server.py → 8 tools
├── extractors/ (unchanged)                  ├── cache.py
├── analyzers/                               └── pyproject.toml
│   ├── scoring.py (dual: human + agent)
│   ├── issue_detector.py (NEW)
│   └── (others unchanged)
├── fixers/ (NEW)
│   ├── description_generator.py
│   ├── topic_suggester.py
│   ├── agents_md_generator.py
│   ├── llms_txt_generator.py
│   ├── profile_readme_generator.py
│   └── devcard_deployer.py
├── renderers/ (unchanged)
└── pipeline.py + audit/fix/analyze pipelines
```

## Tool API

| Tool | Purpose | Writes to GitHub? |
|------|---------|-------------------|
| `audit_profile` | Score profile + find issues | No |
| `generate_devcard` | Create devcard.json + SVG | No |
| `analyze_repo` | Deep-dive single repo | No |
| `fix_profile` | Fix profile-level issues | Yes (with confirmation) |
| `fix_repo` | Fix single repo issues | Yes (with confirmation) |
| `agent_ready` | One-command full agent-readiness | Yes (with confirmation) |
| `compare_devs` | Side-by-side comparison | No |
| `render_card` | Visual card generation | No |

## Scoring

**Human Visibility (0-100):** Bio (10) + Profile README (15) + Repo descriptions (15) + Topics (10) + README quality (15) + License (5) + Pinned repos (5) + Activity (10) + Social links (5) + Contribution graph (10)

**Agent Readiness (0-100):** devcard.json (20) + AGENTS.md (20) + llms.txt (10) + Structured READMEs (15) + Dependency files (10) + Topics/metadata (10) + Classification (10) + Clean commits (5)

## Fixers (Pure Heuristics)

All fixers follow: `generate_<thing>(data) -> FixResult` — no I/O, no LLM.

1. **description_generator** — first README paragraph or `{lang} {type} built with {stack}`
2. **topic_suggester** — from language + deps (mappings) + README keywords
3. **agents_md_generator** — from README, deps, dirs, configs
4. **llms_txt_generator** — from description, docs/ listing, README sections
5. **profile_readme_generator** — template with DevCard SVG embed
6. **devcard_deployer** — generates devcard.json + devcard.svg

## GitHub Write Methods

Added to `github/client.py`:
- `create_or_update_file()` — Contents API PUT
- `update_repo_description()` — Repos API PATCH
- `update_repo_topics()` — Topics API PUT

## Distribution

```bash
# Claude Code
claude mcp add devcard -- uvx devcard-mcp

# Or via npm
claude mcp add devcard -- npx @devcard/mcp-server
```

Plus: Docker image, GitHub Action, agent skill files for all major agents.

## Phases

P0: GitHub writes → P1: Scoring + issues → P2: Fixers → P3: Audit/analyze tools → P4: Fix tools → P5: Render/compare tools → P6: Skills + packaging
