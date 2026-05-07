# DevCard MCP Server Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a standalone MCP server that lets AI agents query DevCard profiles live via `get_devcard()`, `get_developer_summary()`, `compare_developers()`, and `check_developer_stack()`.

**Architecture:** Standalone `devcard-mcp` directory in the repo root with its own `pyproject.toml`. Uses FastMCP framework. Imports devcard as a library. In-memory 30-min cache. Follows booster-mcp patterns exactly.

**Tech Stack:** FastMCP >=3.0, devcard (local path dep), Python 3.11+

---

### Task 1: Scaffold the MCP package

**Files:**
- Create: `devcard-mcp/pyproject.toml`
- Create: `devcard-mcp/src/devcard_mcp/__init__.py`
- Create: `devcard-mcp/src/devcard_mcp/server.py` (stub)
- Create: `devcard-mcp/README.md`

**Step 1: Create directory structure**

```bash
mkdir -p devcard-mcp/src/devcard_mcp
```

**Step 2: Write pyproject.toml**

```toml
[project]
name = "devcard-mcp"
version = "0.1.0"
description = "MCP server for DevCard — let AI agents query developer profiles"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "fastmcp>=3.0",
    "devcard",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project.scripts]
devcard-mcp = "devcard_mcp.server:main"
```

**Step 3: Write empty `__init__.py`**

```python
```

**Step 4: Write stub server.py**

```python
"""DevCard MCP server — let AI agents query developer profiles."""
from fastmcp import FastMCP

mcp = FastMCP(
    name="DevCard",
    instructions="DevCard generates structured developer identity cards from GitHub profiles.",
)


def main():
    mcp.run()
```

**Step 5: Write README.md**

Minimal README with install + config instructions.

**Step 6: Commit**

```bash
git add devcard-mcp/
git commit -m "feat: scaffold devcard-mcp package"
```

---

### Task 2: Implement the in-memory cache

**Files:**
- Create: `devcard-mcp/src/devcard_mcp/cache.py`
- Create: `devcard-mcp/tests/test_cache.py`

**Step 1: Write the failing test**

```python
# devcard-mcp/tests/test_cache.py
import time
from devcard_mcp.cache import DevCardCache

def test_get_returns_none_on_miss():
    cache = DevCardCache(ttl_seconds=60)
    assert cache.get("unknown") is None

def test_get_returns_cached_value():
    cache = DevCardCache(ttl_seconds=60)
    cache.set("user1", {"identity": {"username": "user1"}})
    assert cache.get("user1") is not None

def test_expired_entry_returns_none():
    cache = DevCardCache(ttl_seconds=0)
    cache.set("user1", {"data": True})
    assert cache.get("user1") is None

def test_clear_removes_all():
    cache = DevCardCache(ttl_seconds=60)
    cache.set("a", {})
    cache.set("b", {})
    cache.clear()
    assert cache.get("a") is None
```

**Step 2: Run test — verify FAIL**

```bash
cd devcard-mcp && uv run pytest tests/test_cache.py -v
```

**Step 3: Implement cache**

```python
# devcard-mcp/src/devcard_mcp/cache.py
from __future__ import annotations
import time
from typing import Any

class DevCardCache:
    def __init__(self, ttl_seconds: int = 1800):
        self._store: dict[str, tuple[Any, float]] = {}
        self._ttl = ttl_seconds

    def get(self, username: str) -> Any | None:
        entry = self._store.get(username)
        if entry is None:
            return None
        value, timestamp = entry
        if time.time() - timestamp > self._ttl:
            del self._store[username]
            return None
        return value

    def set(self, username: str, value: Any) -> None:
        self._store[username] = (value, time.time())

    def clear(self) -> None:
        self._store.clear()
```

**Step 4: Run test — verify PASS**

**Step 5: Commit**

```bash
git add devcard-mcp/
git commit -m "feat: in-memory DevCard cache with 30-min TTL"
```

---

### Task 3: Implement `get_devcard` tool

**Files:**
- Modify: `devcard-mcp/src/devcard_mcp/server.py`

**Step 1: Implement the tool**

```python
import asyncio
import logging
import os
from fastmcp import FastMCP
from devcard.config import DevCardConfig
from devcard.pipeline import generate_devcard
from devcard_mcp.cache import DevCardCache

logger = logging.getLogger(__name__)

mcp = FastMCP(
    name="DevCard",
    instructions=(
        "DevCard generates structured developer identity cards from "
        "GitHub profiles. Use these tools to look up developers, "
        "compare profiles, and check technology stacks."
    ),
)

_cache = DevCardCache(ttl_seconds=1800)

def _get_config() -> DevCardConfig:
    return DevCardConfig.create(token=os.environ.get("GITHUB_TOKEN"))

async def _get_or_generate(username: str, force_refresh: bool = False):
    if not force_refresh:
        cached = _cache.get(username)
        if cached is not None:
            return cached
    config = _get_config()
    devcard = await generate_devcard(username, config)
    _cache.set(username, devcard)
    return devcard

@mcp.tool()
async def get_devcard(username: str, force_refresh: bool = False) -> str:
    """Get a full DevCard for a GitHub user.

    Returns a structured JSON developer profile including identity,
    languages, tech stack, activity patterns, top projects, expertise
    domains, collaboration style, and quality scores.

    Results are cached for 30 minutes. Use force_refresh=True to bypass.
    """
    devcard = await _get_or_generate(username, force_refresh)
    return devcard.model_dump_json(indent=2, exclude_none=True)
```

**Step 2: Verify it runs**

```bash
cd devcard-mcp && uv run devcard-mcp
```
(Should start stdio server without errors)

**Step 3: Commit**

```bash
git commit -am "feat: get_devcard MCP tool with caching"
```

---

### Task 4: Implement `get_developer_summary` tool

**Files:**
- Modify: `devcard-mcp/src/devcard_mcp/server.py`

**Step 1: Add the tool**

```python
from devcard.output.curated import curate_for_agent

@mcp.tool()
async def get_developer_summary(username: str) -> str:
    """Get a concise, agent-friendly summary of a GitHub developer.

    Returns curated highlights: identity, top languages with coding ratio,
    stack (frameworks/libraries/tools), expertise domains with confidence,
    activity status with consistency score, and quality metrics.

    Lighter than get_devcard — use this when you need quick context.
    """
    devcard = await _get_or_generate(username)
    curated = curate_for_agent(devcard)
    import json
    return json.dumps(curated, indent=2, default=str)
```

**Step 2: Commit**

```bash
git commit -am "feat: get_developer_summary MCP tool"
```

---

### Task 5: Implement `compare_developers` tool

**Files:**
- Modify: `devcard-mcp/src/devcard_mcp/server.py`

**Step 1: Add the tool**

```python
@mcp.tool()
async def compare_developers(user1: str, user2: str) -> str:
    """Compare two GitHub developers side by side.

    Returns structured comparison of languages (shared/unique),
    stack overlap, expertise domains, quality scores, activity,
    and top projects for both developers.
    """
    card1, card2 = await asyncio.gather(
        _get_or_generate(user1),
        _get_or_generate(user2),
    )
    c1 = curate_for_agent(card1)
    c2 = curate_for_agent(card2)

    # Compute stack overlap
    s1 = _all_stack_names(card1)
    s2 = _all_stack_names(card2)

    return json.dumps({
        user1: c1,
        user2: c2,
        "comparison": {
            "shared_languages": _shared_langs(card1, card2),
            "shared_stack": sorted(s1 & s2),
            f"{user1}_only_stack": sorted(s1 - s2),
            f"{user2}_only_stack": sorted(s2 - s1),
        },
    }, indent=2, default=str)
```

With helpers `_all_stack_names(devcard)` and `_shared_langs(c1, c2)`.

**Step 2: Commit**

```bash
git commit -am "feat: compare_developers MCP tool"
```

---

### Task 6: Implement `check_developer_stack` tool

**Files:**
- Modify: `devcard-mcp/src/devcard_mcp/server.py`

**Step 1: Add the tool**

```python
@mcp.tool()
async def check_developer_stack(
    username: str, technologies: list[str]
) -> str:
    """Check if a developer uses specific technologies.

    Pass a list of technology names (e.g. ["PyTorch", "React", "Docker"]).
    Returns which were found in the developer's stack, which were not,
    and details (category + source repo) for each match.

    Case-insensitive matching.
    """
    devcard = await _get_or_generate(username)
    stack_lookup = _build_stack_lookup(devcard)

    found = {}
    not_found = []
    for tech in technologies:
        match = stack_lookup.get(tech.lower())
        if match:
            found[match["name"]] = {
                "category": match["category"],
                "source": match.get("source"),
            }
        else:
            not_found.append(tech)

    return json.dumps({
        "username": username,
        "found": list(found.keys()),
        "not_found": not_found,
        "details": found,
    }, indent=2)
```

With helper `_build_stack_lookup(devcard)` that creates a lowercase name -> item dict.

**Step 2: Commit**

```bash
git commit -am "feat: check_developer_stack MCP tool"
```

---

### Task 7: Write MCP server tests

**Files:**
- Create: `devcard-mcp/tests/test_server.py`

Test that all 4 tools exist, have correct parameter schemas, and return valid JSON when given mocked DevCard data. Mock `generate_devcard` to avoid real API calls.

**Step 1: Write tests**

```python
# Test tool registration
# Test get_devcard returns valid JSON
# Test get_developer_summary returns curated format
# Test check_developer_stack finds/misses correctly
# Test compare_developers returns both cards + comparison
# Test cache hit avoids re-generation
```

**Step 2: Run — verify PASS**

**Step 3: Commit**

---

### Task 8: Write README and finalize

**Files:**
- Modify: `devcard-mcp/README.md`
- Modify: root `README.md` (add MCP section)

Add complete setup instructions, MCP client config examples (Claude Desktop, Cursor), usage examples, and env var docs.

**Step 1: Write MCP README**

**Step 2: Update root README roadmap** (check off MCP server)

**Step 3: Final commit**

```bash
git commit -am "docs: MCP server README and root README update"
```

---

## Verification

1. `cd devcard-mcp && uv run pytest` — all tests pass
2. `cd devcard-mcp && uv run ruff check src/ tests/` — lint clean
3. `uv run devcard-mcp` — starts without errors
4. Test with Claude Desktop or `fastmcp dev` inspector
