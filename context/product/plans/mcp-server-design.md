# DevCard MCP Server Design

## Context

DevCard generates structured developer profiles from GitHub data. The MCP server exposes this as a live service that AI agents (Claude, GPT, Cursor, etc.) can query programmatically. Standalone package, same repo.

## How people use it

**MCP client config (Claude Desktop, Cursor, etc.):**
```json
{
  "mcpServers": {
    "devcard": {
      "command": "uvx",
      "args": ["devcard-mcp"],
      "env": { "GITHUB_TOKEN": "ghp_..." }
    }
  }
}
```

Then: "Look up karpathy's DevCard" triggers `get_devcard("karpathy")`.

**Direct:**
```bash
pip install devcard-mcp
devcard-mcp serve                    # stdio (MCP clients)
devcard-mcp serve --transport sse    # SSE (web apps)
```

## Tools

| Tool | Params | Returns |
|------|--------|---------|
| `get_devcard` | `username, force_refresh=False` | Full JSON DevCard |
| `get_developer_summary` | `username` | Curated agent-friendly text |
| `compare_developers` | `user1, user2` | Comparison JSON |
| `check_developer_stack` | `username, technologies: list[str]` | `{found, not_found, details}` |

### check_developer_stack response example:
```json
{
  "username": "chiruu12",
  "found": ["PyTorch"],
  "not_found": ["React", "Docker"],
  "details": {
    "PyTorch": {"category": "framework", "source": "NexNet"}
  }
}
```

## Architecture

```
src/devcard_mcp/
├── __init__.py
└── server.py          # FastMCP server with 4 tools + cache
```

- FastMCP framework (matches booster-mcp pattern)
- Imports devcard as library: `generate_devcard()`, `curate_for_agent()`
- GITHUB_TOKEN from environment
- stderr for all logging (critical for stdio transport)

## Cache

- In-memory dict: `{username: (DevCard, timestamp)}`
- 30-minute TTL
- Shared across all tools (generate once, serve many queries)
- `force_refresh` param on `get_devcard` bypasses cache

## Dependencies

```toml
[project]
dependencies = ["devcard", "fastmcp>=3.0"]
```

Separate pyproject.toml, entry point: `devcard-mcp = "devcard_mcp.server:main"`
