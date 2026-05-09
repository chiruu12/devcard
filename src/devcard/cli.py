from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.logging import RichHandler

from devcard.config import DevCardConfig
from devcard.output.json_output import to_json
from devcard.pipeline import generate_devcard
from devcard.renderers.terminal import render_terminal
from devcard.validators.schema_validator import validate_devcard

app = typer.Typer(
    name="devcard",
    help="Auto-generate structured developer identity cards from GitHub profiles.",
    no_args_is_help=True,
)


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=Console(stderr=True), rich_tracebacks=True)],
    )

err_console = Console(stderr=True)

THEMES = {
    "default": "devcard.renderers.themes.default",
    "dark": "devcard.renderers.themes.dark",
    "minimal": "devcard.renderers.themes.minimal",
    "neon": "devcard.renderers.themes.neon",
    "terminal-green": "devcard.renderers.themes.terminal_green",
}


def _load_theme(name: str):
    import importlib

    mod = importlib.import_module(THEMES[name])
    return mod.THEME


@app.command("generate")
def generate_cmd(
    username: str = typer.Argument(help="GitHub username to generate a DevCard for"),
    token: str | None = typer.Option(None, "--token", "-t", help="GitHub personal access token"),
    format: str = typer.Option(
        "terminal",
        "--format",
        "-f",
        help="Output format: json, yaml, terminal, svg, markdown, toon, agent, llms-txt, all",
    ),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output file path"),
    theme: str = typer.Option(
        "default", "--theme", help="SVG theme: default, dark, minimal, neon, terminal-green"
    ),
    no_cache: bool = typer.Option(False, "--no-cache", help="Disable response caching"),
    enrich: bool = typer.Option(False, "--enrich", help="Enable AI-powered enrichment (Fireworks)"),
    model: str | None = typer.Option(
        None, "--model", help="Override LLM model for enrichment"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show debug logs"),
) -> None:
    """Generate a DevCard for a GitHub user."""
    _setup_logging(verbose)
    config = DevCardConfig.create(token=token, no_cache=no_cache)
    if model:
        config.llm_model = model

    if not config.github_token:
        err_console.print(
            "[bold yellow]⚠ No GitHub token detected.[/] Rate limit: 60 requests/hour.\n"
            "  Set GITHUB_TOKEN or use --token for 5000 requests/hour.\n"
            "  [dim]export GITHUB_TOKEN=$(gh auth token)[/]\n"
        )

    if not enrich and config.fireworks_api_key:
        err_console.print("[dim]Tip: use --enrich for AI-powered insights[/]")

    with err_console.status(f"[bold green]Generating DevCard for {username}..."):
        try:
            devcard = asyncio.run(generate_devcard(username, config, enrich=enrich))
        except Exception as e:
            err_console.print(f"[bold red]Error:[/] {e}")
            raise typer.Exit(code=1)

    if format == "json":
        result = to_json(devcard)
        if output:
            output.write_text(result)
            err_console.print(f"[green]Written to {output}[/]")
        else:
            sys.stdout.write(result + "\n")

    elif format == "yaml":
        from devcard.output.yaml_output import to_yaml

        result = to_yaml(devcard)
        if output:
            output.write_text(result)
            err_console.print(f"[green]Written to {output}[/]")
        else:
            sys.stdout.write(result)

    elif format == "terminal":
        result = render_terminal(devcard)
        sys.stdout.write(result)

    elif format == "svg":
        from devcard.renderers.svg_card import render_svg

        svg_theme = _load_theme(theme) if theme in THEMES else None
        result = render_svg(devcard, theme=svg_theme)
        out_path = output or Path(f"{username}.svg")
        out_path.write_text(result)
        err_console.print(f"[green]SVG written to {out_path}[/]")

    elif format == "markdown":
        from devcard.renderers.markdown import render_markdown

        result = render_markdown(devcard)
        if output:
            output.write_text(result)
            err_console.print(f"[green]Written to {output}[/]")
        else:
            sys.stdout.write(result + "\n")

    elif format == "toon":
        from devcard.output.toon_output import to_toon

        result = to_toon(devcard)
        if output:
            output.write_text(result)
            err_console.print(f"[green]Written to {output}[/]")
        else:
            sys.stdout.write(result + "\n")

    elif format == "agent":
        from devcard.output.agent_card import to_agent_card

        result = to_agent_card(devcard)
        if output:
            output.write_text(result)
            err_console.print(f"[green]Written to {output}[/]")
        else:
            sys.stdout.write(result + "\n")

    elif format == "llms-txt":
        from devcard.output.llms_txt import to_llms_txt

        result = to_llms_txt(devcard)
        out_path = output or Path(f"{username}.llms.txt")
        out_path.write_text(result)
        err_console.print(f"[green]llms.txt written to {out_path}[/]")

    elif format == "all":
        from devcard.output.yaml_output import to_yaml
        from devcard.renderers.markdown import render_markdown
        from devcard.renderers.svg_card import render_svg

        json_path = output or Path(f"{username}.devcard.json")
        json_path.write_text(to_json(devcard))
        err_console.print(f"[green]JSON: {json_path}[/]")

        svg_theme = _load_theme(theme) if theme in THEMES else None
        svg_path = json_path.with_suffix(".svg")
        svg_path.write_text(render_svg(devcard, theme=svg_theme))
        err_console.print(f"[green]SVG:  {svg_path}[/]")

        md_path = json_path.with_suffix(".md")
        md_path.write_text(render_markdown(devcard))
        err_console.print(f"[green]MD:   {md_path}[/]")

        from devcard.output.llms_txt import to_llms_txt

        llms_path = json_path.with_name(f"{username}.llms.txt")
        llms_path.write_text(to_llms_txt(devcard))
        err_console.print(f"[green]llms: {llms_path}[/]")

        sys.stdout.write(render_terminal(devcard))

    else:
        err_console.print(f"[red]Unknown format: {format}[/]")
        raise typer.Exit(code=1)


@app.command("validate")
def validate_cmd(
    file: Path = typer.Argument(help="Path to a devcard.json file to validate"),
) -> None:
    """Validate a devcard.json file against the schema."""
    if not file.exists():
        err_console.print(f"[red]File not found: {file}[/]")
        raise typer.Exit(code=1)

    try:
        data = json.loads(file.read_text())
    except json.JSONDecodeError as e:
        err_console.print(f"[red]Invalid JSON: {e}[/]")
        raise typer.Exit(code=1)

    errors = validate_devcard(data)
    if errors:
        err_console.print(f"[red]Validation failed ({len(errors)} errors):[/]")
        for error in errors:
            err_console.print(f"  - {error}")
        raise typer.Exit(code=1)
    else:
        err_console.print("[green]Valid DevCard![/]")


@app.command("me")
def me_cmd(
    token: str | None = typer.Option(None, "--token", "-t", help="GitHub personal access token"),
    format: str = typer.Option("terminal", "--format", "-f", help="Output format"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output file path"),
    theme: str = typer.Option("default", "--theme", help="SVG theme"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Disable response caching"),
    enrich: bool = typer.Option(False, "--enrich", help="Enable AI-powered enrichment (Fireworks)"),
    model: str | None = typer.Option(None, "--model", help="Override LLM model for enrichment"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show debug logs"),
) -> None:
    """Generate a DevCard for the current git user."""
    import subprocess

    username = None
    try:
        result = subprocess.run(
            ["gh", "api", "user", "-q", ".login"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            username = result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    if not username:
        err_console.print(
            "[red]Could not detect GitHub username."
            " Use 'devcard generate <username>' instead.[/]"
        )
        raise typer.Exit(code=1)

    err_console.print(f"[dim]Detected username: {username}[/]")
    generate_cmd(
        username=username, token=token, format=format,
        output=output, theme=theme, no_cache=no_cache,
        enrich=enrich, model=model, verbose=verbose,
    )


@app.command("compare")
def compare_cmd(
    user1: str = typer.Argument(help="First GitHub username"),
    user2: str = typer.Argument(help="Second GitHub username"),
    token: str | None = typer.Option(None, "--token", "-t", help="GitHub personal access token"),
    format: str = typer.Option(
        "terminal", "--format", "-f", help="Output format: terminal, json",
    ),
    no_cache: bool = typer.Option(False, "--no-cache", help="Disable response caching"),
) -> None:
    """Compare two developers side by side."""
    from devcard.renderers.compare import render_compare

    config = DevCardConfig.create(token=token, no_cache=no_cache)

    with err_console.status(f"[bold green]Generating DevCards for {user1} & {user2}..."):
        try:
            card1, card2 = asyncio.run(_generate_pair(user1, user2, config))
        except Exception as e:
            err_console.print(f"[bold red]Error:[/] {e}")
            raise typer.Exit(code=1)

    if format == "json":
        result = json.dumps({
            "user1": json.loads(to_json(card1)),
            "user2": json.loads(to_json(card2)),
        }, indent=2)
        sys.stdout.write(result + "\n")
    else:
        result = render_compare(card1, card2)
        sys.stdout.write(result)


async def _generate_pair(user1: str, user2: str, config: DevCardConfig):
    task1 = generate_devcard(user1, config)
    task2 = generate_devcard(user2, config)
    return await asyncio.gather(task1, task2)


@app.command("advise")
def advise_cmd(
    username: str = typer.Argument(help="GitHub username to advise"),
    token: str | None = typer.Option(None, "--token", "-t", help="GitHub personal access token"),
    format: str = typer.Option(
        "terminal", "--format", "-f", help="Output format: terminal, markdown, json",
    ),
    enrich: bool = typer.Option(False, "--enrich", help="Enable LLM-powered summary"),
    model: str | None = typer.Option(None, "--model", help="Override LLM model"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Disable response caching"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show debug logs"),
) -> None:
    """Get actionable profile advice with scores, praise, and critiques."""
    _setup_logging(verbose)
    config = DevCardConfig.create(token=token, no_cache=no_cache)
    if model:
        config.llm_model = model

    with err_console.status(f"[bold green]Analyzing profile for {username}..."):
        try:
            from devcard.advisor import advise_pipeline

            advice = asyncio.run(advise_pipeline(username, config, enrich=enrich))
        except Exception as e:
            err_console.print(f"[bold red]Error:[/] {e}")
            raise typer.Exit(code=1)

    if format == "json":
        result = advice.model_dump_json(indent=2, exclude_none=True)
        sys.stdout.write(result + "\n")

    elif format == "markdown":
        from devcard.renderers.advice import render_advice_markdown

        result = render_advice_markdown(advice)
        sys.stdout.write(result + "\n")

    elif format == "terminal":
        from devcard.renderers.advice import render_advice_terminal

        result = render_advice_terminal(advice)
        sys.stdout.write(result)

    else:
        err_console.print(f"[red]Unknown format: {format}[/]")
        raise typer.Exit(code=1)
