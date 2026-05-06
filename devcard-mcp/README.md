# DevCard MCP Server

Let AI agents query developer profiles from GitHub via the [Model Context Protocol](https://modelcontextprotocol.io/).

## Setup

```bash
# From the devcard repo root
cd devcard-mcp
uv sync
```

Set environment variables (or add to `.env`):
```bash
export GITHUB_TOKEN=ghp_your_token    # Required (60 req/hr without, 5000 with)
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
}
```

Then ask Claude: "Look up karpathy's developer profile" or "Compare torvalds and karpathy".

## Tools

### get_devcard

Get a full DevCard JSON for any GitHub user.

```
get_devcard(username="karpathy")
get_devcard(username="karpathy", force_refresh=True)  # bypass cache
```

### get_developer_summary

Get a concise, agent-friendly summary. Lighter than full DevCard.

```
get_developer_summary(username="chiruu12")
```

### compare_developers

Side-by-side comparison with language/stack overlap.

```
compare_developers(user1="karpathy", user2="torvalds")
```

### check_developer_stack

Check if a developer uses specific technologies.

```
check_developer_stack(username="chiruu12", technologies=["PyTorch", "React", "Docker"])
# Returns: { found: ["PyTorch"], not_found: ["React", "Docker"], details: {...} }
```

## Caching

All results are cached in-memory for 30 minutes. Use `force_refresh=True` on `get_devcard` to bypass.
