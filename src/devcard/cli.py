from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from devcard.config import DevCardConfig
from devcard.output.json_output import to_json
from devcard.pipeline import generate_devcard

app = typer.Typer(
    name="devcard",
    help="Auto-generate structured developer identity cards from GitHub profiles.",
    no_args_is_help=True,
)

err_console = Console(stderr=True)


@app.command("generate")
def generate_cmd(
    username: str = typer.Argument(help="GitHub username to generate a DevCard for"),
    token: Optional[str] = typer.Option(None, "--token", "-t", help="GitHub personal access token"),
    format: str = typer.Option(
        "json", "--format", "-f", help="Output format: json, terminal, svg, all"
    ),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Disable response caching"),
) -> None:
    """Generate a DevCard for a GitHub user."""
    config = DevCardConfig.create(token=token, no_cache=no_cache)

    with err_console.status(f"[bold green]Generating DevCard for {username}..."):
        try:
            devcard = asyncio.run(generate_devcard(username, config))
        except Exception as e:
            err_console.print(f"[bold red]Error:[/] {e}")
            raise typer.Exit(code=1)

    result = to_json(devcard)

    if output:
        output.write_text(result)
        err_console.print(f"[green]Written to {output}[/]")
    else:
        sys.stdout.write(result + "\n")


@app.command("validate")
def validate_cmd(
    file: Path = typer.Argument(help="Path to a devcard.json file to validate"),
) -> None:
    """Validate a devcard.json file against the schema."""
    err_console.print("[dim]Not implemented yet[/]")
    raise typer.Exit(code=1)
