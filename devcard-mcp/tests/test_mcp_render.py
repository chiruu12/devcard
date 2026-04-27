"""Tests for render_card MCP tool and compare_developers score enhancement."""
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
_mock_devcard_renderers = ModuleType("devcard.renderers")
_mock_devcard_renderers_svg = ModuleType("devcard.renderers.svg_card")
_mock_devcard_renderers_themes = ModuleType("devcard.renderers.themes")
_mock_devcard_renderers_themes_default = ModuleType("devcard.renderers.themes.default")
_mock_devcard_analyzers = ModuleType("devcard.analyzers")
_mock_devcard_analyzers_scoring = ModuleType("devcard.analyzers.scoring")
_mock_devcard_github = ModuleType("devcard.github")
_mock_devcard_github_client = ModuleType("devcard.github.client")

_mock_devcard_config.DevCardConfig = MagicMock()  # type: ignore[attr-defined]
_mock_devcard_pipeline.generate_devcard = AsyncMock()  # type: ignore[attr-defined]
_mock_devcard_pipeline._fetch_profile_repo_data = AsyncMock()  # type: ignore[attr-defined]
_mock_devcard_output_curated.curate_for_agent = MagicMock()  # type: ignore[attr-defined]

# SVG renderer mock
_mock_devcard_renderers_svg.render_svg = MagicMock()  # type: ignore[attr-defined]

# Theme mock — THEME attribute on the default module
_mock_theme = MagicMock()
_mock_theme.name = "default"
_mock_devcard_renderers_themes_default.THEME = _mock_theme  # type: ignore[attr-defined]

# Scoring mocks
_mock_devcard_analyzers_scoring.compute_human_visibility_score = MagicMock(return_value=42)  # type: ignore[attr-defined]
_mock_devcard_analyzers_scoring.compute_agent_readiness_score = MagicMock(return_value=55)  # type: ignore[attr-defined]

# GitHub client mock
_mock_client_instance = MagicMock()
_mock_client_instance.close = AsyncMock()
_mock_devcard_github_client.GitHubClient = MagicMock(return_value=_mock_client_instance)  # type: ignore[attr-defined]

sys.modules.setdefault("devcard", _mock_devcard)
sys.modules.setdefault("devcard.config", _mock_devcard_config)
sys.modules.setdefault("devcard.pipeline", _mock_devcard_pipeline)
sys.modules.setdefault("devcard.output", _mock_devcard_output)
sys.modules.setdefault("devcard.output.curated", _mock_devcard_output_curated)
sys.modules.setdefault("devcard.renderers", _mock_devcard_renderers)
sys.modules.setdefault("devcard.renderers.svg_card", _mock_devcard_renderers_svg)
sys.modules.setdefault("devcard.renderers.themes", _mock_devcard_renderers_themes)
sys.modules.setdefault("devcard.renderers.themes.default", _mock_devcard_renderers_themes_default)
sys.modules.setdefault("devcard.analyzers", _mock_devcard_analyzers)
sys.modules.setdefault("devcard.analyzers.scoring", _mock_devcard_analyzers_scoring)
sys.modules.setdefault("devcard.github", _mock_devcard_github)
sys.modules.setdefault("devcard.github.client", _mock_devcard_github_client)

from devcard_mcp.server import (  # noqa: E402, I001
    compare_developers,
    render_card,
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
    """Build a MagicMock that quacks like a DevCard."""
    devcard = MagicMock()
    devcard.identity.username = username

    class _Lang:
        def __init__(self, n):
            self.name = n

    devcard.languages = [_Lang("Python"), _Lang("JavaScript")]

    devcard.stack.frameworks = [_make_stack_item("FastAPI", "framework")]
    devcard.stack.libraries = []
    devcard.stack.databases = []
    devcard.stack.tools = []
    devcard.stack.platforms = []
    devcard.stack.ci_cd = []
    devcard.stack.testing = []
    devcard.stack.other = []

    devcard.model_dump_json.return_value = json.dumps({
        "identity": {"username": username},
    })
    return devcard


# ---------------------------------------------------------------------------
# Tests: render_card
# ---------------------------------------------------------------------------

class TestRenderCard:
    @pytest.mark.asyncio
    async def test_render_card_returns_svg(self):
        """render_card returns JSON with svg, embed_markdown, size_bytes keys."""
        card = _make_devcard("alice")
        svg_content = '<svg xmlns="http://www.w3.org/2000/svg" width="495" height="200"></svg>'

        with patch("devcard_mcp.server._get_or_generate", new_callable=AsyncMock,
                    return_value=card), \
             patch("devcard_mcp.server._load_theme", return_value=_mock_theme), \
             patch("devcard.renderers.svg_card.render_svg", return_value=svg_content):
            result = await render_card("alice")
            parsed = json.loads(result)

            assert "svg" in parsed
            assert "embed_markdown" in parsed
            assert "size_bytes" in parsed
            assert parsed["svg"].startswith("<svg")
            assert parsed["username"] == "alice"
            assert parsed["size_bytes"] == len(svg_content.encode())

    @pytest.mark.asyncio
    async def test_render_card_default_theme(self):
        """render_card with theme='default' works without error."""
        card = _make_devcard("bob")
        svg_content = '<svg xmlns="http://www.w3.org/2000/svg"></svg>'

        with patch("devcard_mcp.server._get_or_generate", new_callable=AsyncMock,
                    return_value=card), \
             patch("devcard_mcp.server._load_theme", return_value=_mock_theme) as mock_load, \
             patch("devcard.renderers.svg_card.render_svg", return_value=svg_content):
            result = await render_card("bob", theme="default")
            parsed = json.loads(result)

            mock_load.assert_called_once_with("default")
            assert parsed["theme"] == "default"
            assert parsed["svg"].startswith("<svg")


# ---------------------------------------------------------------------------
# Tests: compare_developers with scores
# ---------------------------------------------------------------------------

class TestCompareDevelopersWithScores:
    @pytest.mark.asyncio
    async def test_compare_developers_includes_scores(self):
        """compare_developers includes a 'scores' key with scores for both users."""
        card1 = _make_devcard("user1")
        card2 = _make_devcard("user2")

        curated1 = {"identity": {"username": "user1"}}
        curated2 = {"identity": {"username": "user2"}}

        mock_profile = MagicMock()

        with patch("devcard_mcp.server._get_or_generate", new_callable=AsyncMock,
                    side_effect=[card1, card2]), \
             patch("devcard_mcp.server.curate_for_agent",
                   side_effect=[curated1, curated2]), \
             patch("devcard_mcp.server._get_config"), \
             patch("devcard.github.client.GitHubClient") as mock_client_cls, \
             patch("devcard.pipeline._fetch_profile_repo_data",
                   new_callable=AsyncMock,
                   return_value=mock_profile), \
             patch("devcard.analyzers.scoring.compute_human_visibility_score",
                   return_value=75), \
             patch("devcard.analyzers.scoring.compute_agent_readiness_score",
                   return_value=60):

            mock_client_instance = MagicMock()
            mock_client_instance.close = AsyncMock()
            mock_client_cls.return_value = mock_client_instance

            result = await compare_developers("user1", "user2")
            parsed = json.loads(result)

            assert "scores" in parsed
            assert "user1" in parsed["scores"]
            assert "user2" in parsed["scores"]
            assert "human_visibility" in parsed["scores"]["user1"]
            assert "agent_readiness" in parsed["scores"]["user1"]
            assert "human_visibility" in parsed["scores"]["user2"]
            assert "agent_readiness" in parsed["scores"]["user2"]
