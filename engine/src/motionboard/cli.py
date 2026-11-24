"""`mb` command line. Commands are added per task in specs/001-music-video-pipeline/tasks.md."""

import json

import typer

from motionboard import __version__

app = typer.Typer(no_args_is_help=True, add_completion=False, help="Motionboard engine")


@app.callback()
def main() -> None:
    """Motionboard engine. Every command accepts --json."""


@app.command()
def version(as_json: bool = typer.Option(False, "--json", help="Print one JSON object")) -> None:
    """Print the engine version."""
    if as_json:
        typer.echo(json.dumps({"ok": True, "command": "mb version", "data": {"version": __version__}}))
    else:
        typer.echo(__version__)


if __name__ == "__main__":
    app()
