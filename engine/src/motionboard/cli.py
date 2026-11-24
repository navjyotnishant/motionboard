"""`mb` command line (contracts/cli.md). Every command takes --json and prints one report."""

import sqlite3
import sys
from collections.abc import Callable

import typer

from motionboard import __version__
from motionboard.backends import registry
from motionboard.db.connection import latest_version, open_db
from motionboard.guard import fitcheck, presets
from motionboard.report import MbError, Report

app = typer.Typer(no_args_is_help=True, add_completion=False, help="Motionboard engine")
db_app = typer.Typer(no_args_is_help=True, help="Database")
app.add_typer(db_app, name="db")

JsonOpt = typer.Option(False, "--json", help="Print exactly one JSON object")


def run(command: str, as_json: bool, fn: Callable[[sqlite3.Connection, Report], None]) -> None:
    """Open the DB, run fn, print the report, exit non-zero on failure."""
    report = Report(command=command)
    try:
        conn = open_db()
        try:
            fn(conn, report)
        finally:
            conn.close()
    except MbError as err:
        report = Report.failure(command, err, report.project)
    except Exception as err:  # unexpected: still one report, never a traceback on stdout
        report = Report.failure(command, MbError("INTERNAL", f"{type(err).__name__}: {err}"))
    typer.echo(report.to_json() if as_json else report.to_text())
    if not report.ok:
        sys.exit(1)


@app.callback()
def main() -> None:
    """Motionboard engine. Every command accepts --json."""


@app.command()
def version(as_json: bool = JsonOpt) -> None:
    """Print the engine version."""
    r = Report(command="mb version", data={"version": __version__})
    typer.echo(r.to_json() if as_json else __version__)


@db_app.command("migrate")
def db_migrate(as_json: bool = JsonOpt) -> None:
    """Create or upgrade the database schema."""

    def go(conn, r):
        from motionboard import config
        from motionboard.db.connection import current_version

        presets.seed(conn)
        r.data = {"db": str(config.db_path()), "schema_version": current_version(conn)}
        r.verified.append(f"schema at version {latest_version()}")
        r.verified.append("builtin guard presets present")

    run("mb db migrate", as_json, go)


@app.command()
def guard(
    set_name: str = typer.Option(None, "--set", help="Make this preset active"),
    create: str = typer.Option(None, "--create", help="Create a custom preset with this name"),
    start: int = typer.Option(None, "--start", help="Start floor: free memory percent needed to begin"),
    kill: int = typer.Option(None, "--kill", help="Kill floor: stop the job below this free percent"),
    swap: int = typer.Option(None, "--swap", help="Swap growth ceiling in MB during the job"),
    poll: float = typer.Option(2.0, "--poll", help="Seconds between samples"),
    as_json: bool = JsonOpt,
) -> None:
    """List guard presets, set the active one, or create a custom one."""

    def go(conn, r):
        if create:
            if None in (start, kill, swap):
                raise MbError("INVALID_INPUT", "--create needs --start, --kill and --swap")
            p = presets.create(conn, presets.GuardProfile(create, start, kill, swap, poll), actor="chat")
            r.verified.append(f"created preset '{p.name}'")
        if set_name:
            p = presets.set_active(conn, set_name, actor="chat")
            r.verified.append(f"active preset is now '{p.name}'")
        act = presets.active(conn)
        r.data = {
            "active": act.name,
            "active_description": act.describe(),
            "presets": [vars(p) for p in presets.list_profiles(conn)],
        }

    run("mb guard", as_json, go)


@app.command()
def fit(
    backend: str = typer.Option(None, "--backend", help="Video backend (default ltx23)"),
    width: int = typer.Option(..., "--width"),
    height: int = typer.Option(..., "--height"),
    frames: int = typer.Option(..., "--frames"),
    mode: str = typer.Option("i2v", "--mode", help="i2v or a2v"),
    preset: str = typer.Option(None, "--preset", help="Guard preset (default: active)"),
    as_json: bool = JsonOpt,
) -> None:
    """Dry run: will this render fit in memory right now? Nothing is started."""

    def go(conn, r):
        b = registry.get(backend)
        profile = presets.get(conn, preset) if preset else presets.active(conn)
        n = b.frame_rule(frames)
        res = fitcheck.fit(b, mode, width, height, n, profile, conn)
        r.data = {
            "backend": b.name, "mode": mode, "width": width, "height": height, "frames": n,
            "guard": profile.describe(), **vars(res), "summary": res.summary(),
        }
        r.verified.append(f"free memory read now: {res.free_pct_now}%")
        r.not_verified.append(f"peak is an estimate from {res.basis}, not a test run")
        if not res.fits:
            raise MbError(
                "FIT_REFUSED", res.summary(), hint="; ".join(res.suggestions), data=r.data
            )

    run("mb fit", as_json, go)


# Stage commands register themselves on `app`.
from motionboard import cmd_clips, cmd_setup, cmd_storyboard  # noqa: E402,F401

if __name__ == "__main__":
    app()
