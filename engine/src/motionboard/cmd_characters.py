"""Character commands: add, set, list, link and unlink (T068)."""

from pathlib import Path

import typer

from motionboard import projects
from motionboard.cli import JsonOpt, app, run
from motionboard.storyboard import characters, templates

character_app = typer.Typer(no_args_is_help=True, help="Characters: name, reference image, style line")
app.add_typer(character_app, name="character")

ProjectOpt = typer.Option(..., "--project", "-p", help="Project id (or its last characters)")
NameOpt = typer.Option(..., "--name", help="Character name as used in shot visuals, e.g. HER")


def _look(conn, p):
    return templates.get_look(p["visual_look"], conn) if p.get("visual_look") else None


def _ords(shots: str) -> list[int]:
    try:
        return [int(x) for x in shots.replace(" ", "").split(",") if x]
    except ValueError as e:
        raise typer.BadParameter("--shots takes numbers like 1,3,4") from e


@character_app.command("list")
def character_list(project: str = ProjectOpt, as_json: bool = JsonOpt) -> None:
    """List characters with the shots they appear in."""

    def go(conn, r):
        p = projects.get(conn, project)
        r.project = p["id"]
        r.data = {"characters": characters.listing(conn, p["id"])}

    run("mb character list", as_json, go)


@character_app.command("add")
def character_add(
    project: str = ProjectOpt,
    name: str = NameOpt,
    style: str = typer.Option("", "--style", help="One line describing how they look, added to plate prompts"),
    ref: Path | None = typer.Option(None, "--ref", help="Reference image kept consistent across plates"),
    as_json: bool = JsonOpt,
) -> None:
    """Add a character."""

    def go(conn, r):
        p = projects.get(conn, project)
        r.project = p["id"]
        c = characters.add(conn, p, name, style, ref, "chat")
        r.data = {"character": c}
        if c["reference_image"]:
            r.verified.append(f"reference copied to {c['reference_image']}")
        r.next = [f"mb character link -p {project} --name {c['name']} --shots 1,2"]

    run("mb character add", as_json, go)


@character_app.command("set")
def character_set(
    project: str = ProjectOpt,
    name: str = NameOpt,
    field: str = typer.Option(..., "--field", help="style_line, reference_image or name"),
    value: str = typer.Option(..., "--value"),
    as_json: bool = JsonOpt,
) -> None:
    """Change a character. Shots they appear in get new plate prompts; finished plates are marked for redo."""

    def go(conn, r):
        p = projects.get(conn, project)
        r.project = p["id"]
        c, changed = characters.set_field(conn, p, name, field, value, _look(conn, p), "chat")
        r.data = {"character": c, "shots_changed": changed}

    run("mb character set", as_json, go)


@character_app.command("link")
def character_link(project: str = ProjectOpt, name: str = NameOpt,
                   shots: str = typer.Option(..., "--shots", help="Shot numbers, e.g. 1,3,4"),
                   as_json: bool = JsonOpt) -> None:
    """Put a character in shots."""

    def go(conn, r):
        p = projects.get(conn, project)
        r.project = p["id"]
        r.data = {"shots_changed": characters.link(conn, p, name, _ords(shots), True, _look(conn, p), "chat")}

    run("mb character link", as_json, go)


@character_app.command("unlink")
def character_unlink(project: str = ProjectOpt, name: str = NameOpt,
                     shots: str = typer.Option(..., "--shots"), as_json: bool = JsonOpt) -> None:
    """Take a character out of shots."""

    def go(conn, r):
        p = projects.get(conn, project)
        r.project = p["id"]
        r.data = {"shots_changed": characters.link(conn, p, name, _ords(shots), False, _look(conn, p), "chat")}

    run("mb character unlink", as_json, go)
