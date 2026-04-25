import typer

app = typer.Typer(
    name="devcard",
    help="Auto-generate structured developer identity cards from GitHub profiles.",
    no_args_is_help=True,
)


@app.command()
def generate(username: str = typer.Argument(help="GitHub username to generate a DevCard for")):
    """Generate a DevCard for a GitHub user."""
    typer.echo(f"Not implemented yet: {username}")
