"""Creative direction commands: mb art (Art Direction Bible) and mb critique (structured reviews). Feature 003."""

from pathlib import Path

import typer

from motionboard import projects
from motionboard.cli import JsonOpt, app, run
from motionboard.config import ACTOR
from motionboard.direction import bible, critique, service
from motionboard.storyboard import templates

art_app = typer.Typer(no_args_is_help=True, help="Art Direction Bible: the film's world, characters, light, "
                      "camera, motifs and motion rules, versioned and approved by the creator")
critique_app = typer.Typer(no_args_is_help=True, help="Structured creative reviews with findings")
app.add_typer(art_app, name="art")
app.add_typer(critique_app, name="critique")

ProjectOpt = typer.Option(..., "--project", "-p", help="Project id (or its last characters)")


def _look(conn, p):
    return templates.get_look(p["visual_look"], conn) if p.get("visual_look") else None


def _impact_lines(imp: dict) -> list[str]:
    out = []
    for s in imp.get("shots", []):
        kinds = sorted({a["kind"] for a in s["assets"]})
        out.append(f"shot {s['shot']}: {' and '.join(kinds)} made under earlier direction ({'; '.join(s['reasons'])})")
    return out


@art_app.command("draft")
def art_draft(project: str = ProjectOpt, file: Path = typer.Option(..., "--file", help="Bible as JSON or YAML"),
              profile: str = typer.Option(None, "--profile", help="compact (simple films) or full (narrative films)"),
              note: str = typer.Option("", "--note", help="What changed and why"), as_json: bool = JsonOpt) -> None:
    """Save a Bible draft. Opens a revision of the approved version, or replaces the open draft."""

    def go(conn, r):
        p = projects.get(conn, project)
        r.project = p["id"]
        res = service.save_draft(conn, p, bible.load_file(file), profile, note, ACTOR())
        r.data = res
        r.verified.append(f"version {res['version']} saved as {res['status']} ({res['profile']} profile)")
        r.verified.append(f"{service.MD_NAME} regenerated in the project folder")
        r.not_verified += [f"error: {e}" for e in res["errors"]] + [f"warning: {w}" for w in res["warnings"]]
        if res["impact"].get("shots"):
            r.not_verified.append(f"if approved, {len(res['impact']['shots'])} shots have plates or clips made under "
                                  "the current direction; see mb art impact")
        r.next = ("fix the errors, then mb art draft again" if res["errors"] else
                  f"mb art submit -p {p['id']}; the creator reviews it; mb art approve only after they say yes")

    run("mb art draft", as_json, go)


@art_app.command("check")
def art_check(project: str = ProjectOpt, as_json: bool = JsonOpt) -> None:
    """Validate the open version (or the approved one when nothing is open)."""

    def go(conn, r):
        p = projects.get(conn, project)
        r.project = p["id"]
        res = service.check(conn, p)
        r.data = res
        r.verified.append(f"version {res['version']} checked against the {res['profile']} profile")
        r.not_verified += [f"error: {e}" for e in res["errors"]] + [f"warning: {w}" for w in res["warnings"]]
        r.not_verified.append("whether the direction is original and serves the song: that is a creative review")

    run("mb art check", as_json, go)


@art_app.command("submit")
def art_submit(project: str = ProjectOpt, as_json: bool = JsonOpt) -> None:
    """Send the open draft for the creator's review."""

    def go(conn, r):
        p = projects.get(conn, project)
        r.project = p["id"]
        r.data = service.submit(conn, p, ACTOR())
        r.verified.append(f"version {r.data['version']} is awaiting review")
        r.not_verified += [f"warning: {w}" for w in r.data["warnings"]]

    run("mb art submit", as_json, go)


@art_app.command("reject")
def art_reject(project: str = ProjectOpt, note: str = typer.Option(..., "--note", help="What to change"),
               as_json: bool = JsonOpt) -> None:
    """Send the version under review back to draft with the reason."""

    def go(conn, r):
        p = projects.get(conn, project)
        r.project = p["id"]
        r.data = service.reject(conn, p, note, ACTOR())
        r.verified.append(f"version {r.data['version']} sent back to draft")

    run("mb art reject", as_json, go)


def approve_art(conn, r, project: str, via: str | None) -> None:
    p = projects.get(conn, project)
    r.project = p["id"]
    res = service.approve(conn, p, via or ACTOR(), _look(conn, p), ACTOR())
    r.data = res
    r.verified.append(f"art direction version {res['version']} approved"
                      + (f"; version {res['superseded']} superseded" if res["superseded"] else ""))
    if res["recomposed"]:
        r.verified.append(f"prompts of {len(res['recomposed'])} shots now follow this direction")
    r.not_verified += _impact_lines(res["impact"])
    r.not_verified += [f"warning: {w}" for w in res["warnings"]]
    for o in res["overrides"]:
        r.not_verified.append(
            f"shot {o['shot']} {o['part']} prompt is authored by the creator and was not rewritten"
            + ("; the generated prompt under it changed with this version" if o["baseline_changed"] else "")
            + ("; it now conflicts: " + "; ".join(o["conflicts"]) if o["conflicts"] else ""))
    if res["overrides"]:
        r.not_verified.append(f"for each authored prompt the creator keeps it (mb shot override keep), revises it "
                              f"(mb shot set) or clears it (mb shot override clear); see mb shot override list "
                              f"-p {p['id']}")
    r.not_verified += critique.open_for_gate(conn, p["id"], "art_direction")
    r.not_verified.append("no plate or clip was regenerated; redo the shots above with mb plates --shots or "
                          "mb clips --shots --redo when the creator chooses")


@art_app.command("approve")
def art_approve(project: str = ProjectOpt, via: str = typer.Option(None, "--via"), as_json: bool = JsonOpt) -> None:
    """The creator approves the open version. Run only after the creator says yes."""
    run("mb art approve", as_json, lambda conn, r: approve_art(conn, r, project, via))


@art_app.command("show")
def art_show(project: str = ProjectOpt, version: int = typer.Option(None, "--version"),
             pending: bool = typer.Option(False, "--pending", help="The open draft or revision"),
             markdown: bool = typer.Option(False, "--markdown", help="Readable text instead of the structure"),
             as_json: bool = JsonOpt) -> None:
    """The approved Bible (or a version, or the pending one)."""

    def go(conn, r):
        p = projects.get(conn, project)
        r.project = p["id"]
        r.data = service.show(conn, p, version, pending, markdown)
        if r.data["status"] != "approved":
            r.not_verified.append(f"version {r.data['version']} is {r.data['status']}; prompts follow only an "
                                  "approved version")

    run("mb art show", as_json, go)


@art_app.command("history")
def art_history(project: str = ProjectOpt, as_json: bool = JsonOpt) -> None:
    """Every version with its status and approval."""

    def go(conn, r):
        p = projects.get(conn, project)
        r.project = p["id"]
        r.data = {"versions": service.history(conn, p["id"])}

    run("mb art history", as_json, go)


@art_app.command("impact")
def art_impact(project: str = ProjectOpt, as_json: bool = JsonOpt) -> None:
    """Shots and assets a pending revision would affect, or that the last approval affected."""

    def go(conn, r):
        p = projects.get(conn, project)
        r.project = p["id"]
        r.data = {"impact": service.impact_now(conn, p["id"])}
        r.verified.append("compared the Bible versions section by section and looked up active plates and clips")
        r.not_verified.append("whether each image actually breaks the new direction: look at the plates")

    run("mb art impact", as_json, go)


@art_app.command("motifs")
def art_motifs(project: str = ProjectOpt, as_json: bool = JsonOpt) -> None:
    """Each motif's state shot by shot."""

    def go(conn, r):
        p = projects.get(conn, project)
        r.project = p["id"]
        r.data = {"motifs": service.motifs(conn, p["id"])}

    run("mb art motifs", as_json, go)


@art_app.command("export")
def art_export(project: str = ProjectOpt, out: Path = typer.Option(None, "--out", help="Default: project folder"),
               as_json: bool = JsonOpt) -> None:
    """Write the readable Markdown view."""

    def go(conn, r):
        p = projects.get(conn, project)
        r.project = p["id"]
        path = service.write_markdown(conn, p)
        if path and out:
            dest = Path(out).expanduser()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(path.read_text())
            path = dest
        r.data = {"path": str(path) if path else None}
        r.verified.append("written from the database" if path else "nothing to write: no art direction yet")

    run("mb art export", as_json, go)


@critique_app.command("add")
def critique_add(project: str = ProjectOpt,
                 stage: str = typer.Option(..., "--stage", help="concept, art_direction, plate or rough_cut"),
                 role: str = typer.Option(..., "--role", help="director, production_designer, cinematographer, "
                                          "editor, emotion_editor or creator"),
                 verdict: str = typer.Option(..., "--verdict", help="ready, revise or blocked"),
                 file: Path = typer.Option(..., "--file", help="summary, findings, checked, not_checked"),
                 as_json: bool = JsonOpt) -> None:
    """Record a review. Each finding: observation, audience_impact, implication, recommendation (shots optional)."""

    def go(conn, r):
        p = projects.get(conn, project)
        r.project = p["id"]
        r.data = {"critique": critique.add(conn, p, stage, role, verdict, file, ACTOR())}
        r.verified.append(f"{verdict} review stored with {len(r.data['critique']['findings'])} findings")
        r.not_verified += [f"not checked: {x}" for x in r.data["critique"]["not_checked"]]

    run("mb critique add", as_json, go)


@critique_app.command("list")
def critique_list(project: str = ProjectOpt, stage: str = typer.Option(None, "--stage"),
                  shot: int = typer.Option(None, "--shot", help="Only findings about this shot"),
                  open_only: bool = typer.Option(False, "--open", help="Only unresolved"), as_json: bool = JsonOpt):
    """Reviews, newest first."""

    def go(conn, r):
        p = projects.get(conn, project)
        r.project = p["id"]
        r.data = {"critiques": critique.listing(conn, p["id"], stage, shot, open_only)}

    run("mb critique list", as_json, go)


@critique_app.command("resolve")
def critique_resolve(project: str = ProjectOpt, critique_id: str = typer.Option(..., "--id"),
                     as_json: bool = JsonOpt) -> None:
    """Mark a review as dealt with."""

    def go(conn, r):
        p = projects.get(conn, project)
        r.project = p["id"]
        r.data = {"critique": critique.resolve(conn, p["id"], critique_id, ACTOR())}

    run("mb critique resolve", as_json, go)
