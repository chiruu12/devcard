"""DevCard MCP server — let AI agents query developer profiles."""
from __future__ import annotations

from fastmcp import FastMCP

mcp = FastMCP(
    name="DevCard",
    instructions=(
        "DevCard generates structured developer identity cards from "
        "GitHub profiles. Use these tools to look up developers, "
        "compare profiles, and check technology stacks."
    ),
)


def main():
    mcp.run()
