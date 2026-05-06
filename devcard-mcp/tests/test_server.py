"""Tests for DevCard MCP server tools.

devcard is NOT installed in the MCP venv, so we mock the devcard package
in sys.modules before importing devcard_mcp.server.
"""
from __future__ import annotations

import json
import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Patch devcard imports into sys.modules so devcard_mcp.server can be loaded
# ---------------------------------------------------------------------------

_mock_devcard = ModuleType("devcard")
_mock_devcard_config = ModuleType("devcard.config")
_mock_devcard_pipeline = ModuleType("devcard.pipeline")
_mock_devcard_output = ModuleType("devcard.output")
_mock_devcard_output_curated = ModuleType("devcard.output.curated")

_mock_devcard_config.DevCardConfig = MagicMock()  # type: ignore[attr-defined]
_mock_devcard_pipeline.generate_devcard = AsyncMock()  # type: ignore[attr-defined]
_mock_devcard_output_curated.curate_for_agent = MagicMock()  # type: ignore[attr-defined]

sys.modules.setdefault("devcard", _mock_devcard)
sys.modules.setdefault("devcard.config", _mock_devcard_config)
sys.modules.setdefault("devcard.pipeline", _mock_devcard_pipeline)
sys.modules.setdefault("devcard.output", _mock_devcard_output)
sys.modules.setdefault("devcard.output.curated", _mock_devcard_output_curated)

from devcard_mcp.server import (  # noqa: E402
    _all_stack_names,
    _build_stack_lookup,
    _get_or_generate,
    check_developer_stack,
    compare_developers,
    get_devcard,
    get_developer_summary,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_stack_item(name: str, category: str, source: str = "repo"):
    item = MagicMock()
    item.name = name
    item.category = category
    item.source = source
    return item


def _make_devcard(username: str = "testuser"):
    """Build a MagicMock that quacks like a DevCard Pydantic model."""
    devcard = MagicMock()
    devcard.identity.username = username
    devcard.identity.name = "Test User"
    devcard.identity.followers = 100
    devcard.identity.public_repos = 10

    # languages — MagicMock(name=...) overrides the internal Mock name,
    # so we need a simple namespace instead.
    class _Lang:
        def __init__(self, n, pct, cat):
            self.name = n
            self.percentage = pct
            self.category = cat

    devcard.languages = [
        _Lang("Python", 70.0, "logic"),
        _Lang("JavaScript", 30.0, "logic"),
    ]

    # stack
    devcard.stack.frameworks = [_make_stack_item("FastAPI", "framework", "backend-repo")]
    devcard.stack.libraries = [_make_stack_item("NumPy", "library", "ml-repo")]
    devcard.stack.databases = [_make_stack_item("PostgreSQL", "database", "backend-repo")]
    devcard.stack.tools = [_make_stack_item("Docker", "tool", "infra-repo")]
    devcard.stack.platforms = []
    devcard.stack.ci_cd = []
    devcard.stack.testing = [_make_stack_item("pytest", "testing", "backend-repo")]
    devcard.stack.other = []

    devcard.model_dump_json.return_value = json.dumps({
        "identity": {"username": username},
        "languages": [
            {"name": "Python", "percentage": 70.0},
            {"name": "JavaScript", "percentage": 30.0},
        ],
    })
    return devcard


# ---------------------------------------------------------------------------
# Pure-function tests: _all_stack_names
# ---------------------------------------------------------------------------

class TestAllStackNames:
    def test_returns_all_names(self):
        devcard = _make_devcard()
        names = _all_stack_names(devcard)
        assert names == {"FastAPI", "NumPy", "PostgreSQL", "Docker", "pytest"}

    def test_no_stack_returns_empty(self):
        devcard = MagicMock()
        devcard.stack = None
        assert _all_stack_names(devcard) == set()

    def test_empty_stack_returns_empty(self):
        devcard = MagicMock()
        for field in ("frameworks", "libraries", "databases", "tools",
                      "platforms", "ci_cd", "testing", "other"):
            setattr(devcard.stack, field, [])
        assert _all_stack_names(devcard) == set()


# ---------------------------------------------------------------------------
# Pure-function tests: _build_stack_lookup
# ---------------------------------------------------------------------------

class TestBuildStackLookup:
    def test_lookup_keys_are_lowercase(self):
        devcard = _make_devcard()
        lookup = _build_stack_lookup(devcard)
        for key in lookup:
            assert key == key.lower(), f"Key '{key}' is not lowercase"

    def test_lookup_contains_all_items(self):
        devcard = _make_devcard()
        lookup = _build_stack_lookup(devcard)
        assert set(lookup.keys()) == {"fastapi", "numpy", "postgresql", "docker", "pytest"}

    def test_lookup_preserves_original_name(self):
        devcard = _make_devcard()
        lookup = _build_stack_lookup(devcard)
        assert lookup["fastapi"]["name"] == "FastAPI"
        assert lookup["numpy"]["name"] == "NumPy"

    def test_lookup_includes_category_and_source(self):
        devcard = _make_devcard()
        lookup = _build_stack_lookup(devcard)
        assert lookup["fastapi"]["category"] == "framework"
        assert lookup["fastapi"]["source"] == "backend-repo"

    def test_no_stack_returns_empty(self):
        devcard = MagicMock()
        devcard.stack = None
        assert _build_stack_lookup(devcard) == {}


# ---------------------------------------------------------------------------
# Async tool tests: _get_or_generate
# ---------------------------------------------------------------------------

class TestGetOrGenerate:
    @pytest.fixture(autouse=True)
    def _clear_cache(self):
        """Reset the module-level cache before each test."""
        from devcard_mcp import server
        server._cache.clear()
        yield
        server._cache.clear()

    @pytest.mark.asyncio
    async def test_calls_generate_on_cache_miss(self):
        expected = _make_devcard("alice")
        with patch("devcard_mcp.server.generate_devcard", new_callable=AsyncMock,
                    return_value=expected) as mock_gen, \
             patch("devcard_mcp.server._get_config"):
            result = await _get_or_generate("alice")
            mock_gen.assert_awaited_once()
            assert result is expected

    @pytest.mark.asyncio
    async def test_returns_cached_on_hit(self):
        cached_card = _make_devcard("bob")
        from devcard_mcp import server
        server._cache.set("bob", cached_card)

        with patch("devcard_mcp.server.generate_devcard", new_callable=AsyncMock) as mock_gen:
            result = await _get_or_generate("bob")
            mock_gen.assert_not_awaited()
            assert result is cached_card

    @pytest.mark.asyncio
    async def test_force_refresh_bypasses_cache(self):
        cached_card = _make_devcard("carol")
        fresh_card = _make_devcard("carol")
        from devcard_mcp import server
        server._cache.set("carol", cached_card)

        with patch("devcard_mcp.server.generate_devcard", new_callable=AsyncMock,
                    return_value=fresh_card) as mock_gen, \
             patch("devcard_mcp.server._get_config"):
            result = await _get_or_generate("carol", force_refresh=True)
            mock_gen.assert_awaited_once()
            assert result is fresh_card


# ---------------------------------------------------------------------------
# Async tool tests: get_devcard
# ---------------------------------------------------------------------------

class TestGetDevcard:
    @pytest.mark.asyncio
    async def test_returns_json_string(self):
        card = _make_devcard("dave")
        with patch("devcard_mcp.server._get_or_generate", new_callable=AsyncMock,
                    return_value=card):
            result = await get_devcard("dave")
            # get_devcard calls devcard.model_dump_json
            card.model_dump_json.assert_called_once()
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_passes_force_refresh(self):
        card = _make_devcard("eve")
        with patch("devcard_mcp.server._get_or_generate", new_callable=AsyncMock,
                    return_value=card) as mock_get:
            await get_devcard("eve", force_refresh=True)
            mock_get.assert_awaited_once_with("eve", True)


# ---------------------------------------------------------------------------
# Async tool tests: get_developer_summary
# ---------------------------------------------------------------------------

class TestGetDeveloperSummary:
    @pytest.mark.asyncio
    async def test_returns_curated_json(self):
        card = _make_devcard("frank")
        curated = {"identity": {"username": "frank"}, "top_languages": ["Python"]}
        with patch("devcard_mcp.server._get_or_generate", new_callable=AsyncMock,
                    return_value=card), \
             patch("devcard_mcp.server.curate_for_agent", return_value=curated):
            result = await get_developer_summary("frank")
            parsed = json.loads(result)
            assert parsed["identity"]["username"] == "frank"
            assert "top_languages" in parsed


# ---------------------------------------------------------------------------
# Async tool tests: compare_developers
# ---------------------------------------------------------------------------

class TestCompareDevelopers:
    @pytest.mark.asyncio
    async def test_returns_comparison_with_shared_languages(self):
        card1 = _make_devcard("user1")
        card2 = _make_devcard("user2")

        class _Lang:
            def __init__(self, n):
                self.name = n

        card1.languages = [_Lang("Python"), _Lang("Go")]
        card2.languages = [_Lang("Python"), _Lang("Rust")]

        curated1 = {"identity": {"username": "user1"}}
        curated2 = {"identity": {"username": "user2"}}

        with patch("devcard_mcp.server._get_or_generate", new_callable=AsyncMock,
                    side_effect=[card1, card2]), \
             patch("devcard_mcp.server.curate_for_agent",
                   side_effect=[curated1, curated2]):
            result = await compare_developers("user1", "user2")
            parsed = json.loads(result)
            assert "comparison" in parsed
            assert "Python" in parsed["comparison"]["shared_languages"]
            assert "Go" not in parsed["comparison"]["shared_languages"]

    @pytest.mark.asyncio
    async def test_comparison_includes_unique_stack(self):
        card1 = _make_devcard("user1")
        card2 = _make_devcard("user2")

        # Give them different stacks
        card2.stack.frameworks = [_make_stack_item("Django", "framework", "web-repo")]
        card2.stack.libraries = []
        card2.stack.databases = []
        card2.stack.tools = []
        card2.stack.testing = []

        with patch("devcard_mcp.server._get_or_generate", new_callable=AsyncMock,
                    side_effect=[card1, card2]), \
             patch("devcard_mcp.server.curate_for_agent",
                   side_effect=[{}, {}]):
            result = await compare_developers("user1", "user2")
            parsed = json.loads(result)
            comp = parsed["comparison"]
            assert "Django" in comp["user2_only_stack"]
            assert "FastAPI" in comp["user1_only_stack"]


# ---------------------------------------------------------------------------
# Async tool tests: check_developer_stack
# ---------------------------------------------------------------------------

class TestCheckDeveloperStack:
    @pytest.mark.asyncio
    async def test_found_and_not_found(self):
        card = _make_devcard("grace")
        with patch("devcard_mcp.server._get_or_generate", new_callable=AsyncMock,
                    return_value=card):
            result = await check_developer_stack("grace", ["FastAPI", "React", "Docker"])
            parsed = json.loads(result)
            assert "FastAPI" in parsed["found"]
            assert "Docker" in parsed["found"]
            assert "React" in parsed["not_found"]

    @pytest.mark.asyncio
    async def test_case_insensitive_matching(self):
        card = _make_devcard("heidi")
        with patch("devcard_mcp.server._get_or_generate", new_callable=AsyncMock,
                    return_value=card):
            result = await check_developer_stack("heidi", ["fastapi", "NUMPY", "docker"])
            parsed = json.loads(result)
            assert len(parsed["found"]) == 3
            assert len(parsed["not_found"]) == 0

    @pytest.mark.asyncio
    async def test_details_include_category_and_source(self):
        card = _make_devcard("ivan")
        with patch("devcard_mcp.server._get_or_generate", new_callable=AsyncMock,
                    return_value=card):
            result = await check_developer_stack("ivan", ["FastAPI"])
            parsed = json.loads(result)
            assert "FastAPI" in parsed["details"]
            assert parsed["details"]["FastAPI"]["category"] == "framework"
            assert parsed["details"]["FastAPI"]["source"] == "backend-repo"

    @pytest.mark.asyncio
    async def test_empty_technologies_list(self):
        card = _make_devcard("judy")
        with patch("devcard_mcp.server._get_or_generate", new_callable=AsyncMock,
                    return_value=card):
            result = await check_developer_stack("judy", [])
            parsed = json.loads(result)
            assert parsed["found"] == []
            assert parsed["not_found"] == []
