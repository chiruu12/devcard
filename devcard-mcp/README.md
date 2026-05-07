# DevCard MCP Server

Let AI agents query, audit, and improve developer profiles from GitHub via the [Model Context Protocol](https://modelcontextprotocol.io/).

## Setup

```bash
# From the devcard repo root
cd devcard-mcp
uv sync
```

Set environment variables:
```bash
export GITHUB_TOKEN=$(gh auth token)   # or: export GITHUB_TOKEN=ghp_your_token
```

## Usage with Claude Desktop

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "devcard": {
      "command": "uv",
      "args": ["--directory", "/path/to/devcard/devcard-mcp", "run", "devcard-mcp"],
      "env": {
        "GITHUB_TOKEN": "ghp_your_token"
      }
    }
  }
```

Replace `/path/to/devcard` with your actual clone path.

Then ask Claude: "Look up karpathy's developer profile" or "Audit my GitHub presence".

## Usage with Claude Code

Add the MCP server to your Claude Code config:

```bash
claude mcp add devcard -- uv --directory /path/to/devcard/devcard-mcp run devcard-mcp
```

For the best experience, also install the DevCard skills from `skills/claude-code/`.

## Tools

### Read-Only Tools

#### get_devcard

Full DevCard JSON for any GitHub user. Returns 14+ signals (identity, languages, stack, activity, projects, collaboration, quality, expertise, coding habits, notable contributions, and more).

```
get_devcard(username="karpathy")
get_devcard(username="karpathy", force_refresh=True)  # bypass cache
```

#### get_developer_summary

Concise, agent-friendly text summary. Lighter than full DevCard.

```
get_developer_summary(username="chiruu12")
```

#### compare_developers

Side-by-side comparison with language/stack overlap and quality scores.

```
compare_developers(user1="karpathy", user2="torvalds")
```

#### check_developer_stack

Check if a developer uses specific technologies.

```
check_developer_stack(username="chiruu12", technologies=["PyTorch", "React", "Docker"])
```

#### render_card

Generate a visual SVG card. Themes: default, dark, minimal, neon, terminal-green.

```
render_card(username="chiruu12", theme="dark")
```

### Analysis Tools

#### audit_profile

Score a profile (human visibility 0-100, agent readiness 0-100) and detect issues.

```
audit_profile(username="chiruu12")
```

Returns: `human_visibility_score`, `agent_readiness_score`, `issues[]`, `recommendations[]`

#### analyze_repo

Deep-dive into a single repository. Returns classification, issues, suggested description and topics.

```
analyze_repo(owner="chiruu12", repo="Hive")
```

### Write Tools

All write tools default to `dry_run=True` (preview only). Set `dry_run=False` to apply changes. Requires a GitHub token with repo write access.

#### fix_profile

Fix profile-level issues: deploy devcard.json, generate profile README, add missing descriptions and topics.

```
fix_profile(username="chiruu12", fixes=["devcard_json", "profile_readme"], dry_run=True)
fix_profile(username="chiruu12", fixes=["all"], dry_run=False)  # apply all fixes
```

#### fix_repo

Fix repo-level issues: generate AGENTS.md, suggest topics, improve description.

```
fix_repo(owner="chiruu12", repo="Hive", fixes=["agents_md", "topics"], dry_run=True)
```

#### agent_ready

One-command full agent-readiness cycle: audit, preview all fixes, optionally apply.

```
agent_ready(username="chiruu12", dry_run=True)   # preview everything
agent_ready(username="chiruu12", dry_run=False)  # apply all fixes
```

## Caching

All results are cached in-memory for 30 minutes. Use `force_refresh=True` on `get_devcard` to bypass.

## Development

```bash
cd devcard-mcp
uv sync
uv run pytest                       # Run tests
uv run ruff check src/ tests/       # Lint
```
