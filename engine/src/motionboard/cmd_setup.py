"""mb setup: machine, tools and models report, with exact fix steps. Never downloads."""

import typer

from motionboard.cli import JsonOpt, app, run
from motionboard.guard import presets
from motionboard.setup import doctor


@app.command()
def setup(
    fix_plan: bool = typer.Option(False, "--fix-plan", help="Print exact install and download steps"),
    quick: bool = typer.Option(False, "--quick", help="Skip the HyperFrames probe (needs network on first run)"),
    as_json: bool = JsonOpt,
) -> None:
    """Check this machine for Motionboard. Nothing is installed or downloaded."""

    def go(conn, r):
        rep = doctor.check(probe_hyperframes=not quick)
        rep["guard"] = presets.active(conn).describe()
        if fix_plan:
            rep["fix_plan"] = doctor.fix_plan(rep)
        r.data = rep
        r.verified.append(f"read machine: {rep['machine']['chip']}, {rep['machine']['free_disk_gb']} GB disk free")
        r.verified.append("checked tools and model folders on disk")
        r.not_verified.append("model files are checked by name, not by checksum")
        r.next = "mb setup --fix-plan" if rep["gaps"] else "mb-storyboard: start a project"

    run("mb setup", as_json, go)
