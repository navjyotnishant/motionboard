"""Storyboard stage commands: project, analyze, concepts, modes, draft, shot, sheet, approve, export, import."""

import json
from pathlib import Path

import typer

from motionboard import projects
from motionboard.audio import align as align_mod
from motionboard.audio import analyze as analyze_mod
from motionboard.audio import segment as segment_mod
from motionboard.backends import registry
from motionboard.cli import JsonOpt, app, run
from motionboard.db import repo
from motionboard.report import MbError
from motionboard.storyboard import board, contact_sheet, io_json, templates
from motionboard.storyboard import draft as draft_mod

project_app = typer.Typer(no_args_is_help=True, help="Projects")
concepts_app = typer.Typer(no_args_is_help=True, help="Brainstorm concepts")
shot_app = typer.Typer(no_args_is_help=True, help="Edit shots")
app.add_typer(project_app, name="project")
app.add_typer(concepts_app, name="concepts")
app.add_typer(shot_app, name="shot")

ProjectOpt = typer.Option(..., "--project", "-p", help="Project id (or its last characters)")


def _shot_summary(s: dict) -> dict:
    return {k: s[k] for k in ("id", "ord", "start", "end", "frames", "lyric", "visual", "action", "camera",
                              "has_figure", "lip_sync", "state")}


@project_app.command("new")
def project_new(
    title: str = typer.Option(..., "--title"),
    song: Path = typer.Option(None, "--song", help="Audio file (wav, mp3, m4a)"),
    lyrics_file: Path = typer.Option(None, "--lyrics-file"),
    idea: str = typer.Option("", "--idea"),
    aspect: str = typer.Option("9:16", "--aspect", help="9:16 or 16:9"),
    look: str = typer.Option("stylized", "--look", help="stylized or realistic"),
    as_json: bool = JsonOpt,
) -> None:
    """Create a project folder and record."""

    def go(conn, r):
        lyrics = lyrics_file.read_text() if lyrics_file else ""
        p = projects.create(conn, title, song, lyrics, idea, aspect, look)
        r.project = p["id"]
        r.data = {"id": p["id"], "folder": p["folder"], "song": p["song_path"], "aspect": aspect, "look": look}
        r.verified.append("project folder created with audio, plates, clips, out, logs")
        if not lyrics:
            r.not_verified.append("no lyrics given; timing will use the beat grid only")
        r.next = f"mb analyze --project {p['id']}"

    run("mb project new", as_json, go)


@project_app.command("list")
def project_list(as_json: bool = JsonOpt) -> None:
    """List projects, newest first."""

    def go(conn, r):
        rows = conn.execute("SELECT id, title, aspect, mode, visual_look, folder, updated_at FROM project "
                            "ORDER BY updated_at DESC").fetchall()
        r.data = {"projects": [dict(x) for x in rows]}

    run("mb project list", as_json, go)


@app.command()
def analyze(
    project: str = ProjectOpt,
    start: float = typer.Option(None, "--start", help="Segment start in the song (seconds)"),
    end: float = typer.Option(None, "--end", help="Segment end in the song (seconds)"),
    target: float = typer.Option(segment_mod.DEFAULT_TARGET, "--target", help="Auto segment length (seconds)"),
    as_json: bool = JsonOpt,
) -> None:
    """Pick and cut the song segment, then measure tempo, beats, loudness and sung lines."""

    def go(conn, r):
        p = projects.get(conn, project)
        r.project = p["id"]
        if not p["song_path"]:
            raise MbError("INVALID_INPUT", "project has no song", hint="create it with --song")
        src = Path(p["song_path"])
        if start is not None and end is not None:
            s, e, how = start, end, "given"
        else:
            s, e = segment_mod.auto_pick(src, target)
            how = "whole song" if e - s < target - 0.5 else "auto (loudest sustained window, beat aligned)"
        seg = projects.segment_audio(p)
        segment_mod.cut(src, seg, s, e)
        a = analyze_mod.analyze(seg)
        lines, verified = align_mod.align(seg, p["lyrics"], a.duration, a.beats)
        with repo.tx(conn):
            conn.execute("DELETE FROM song_analysis WHERE project_id = ?", (p["id"],))
            repo.insert(conn, "song_analysis", {
                "project_id": p["id"], "tempo_bpm": a.tempo_bpm, "beats": a.beats,
                "lines": [vars(x) for x in lines], "loudness": a.loudness, "waveform_peaks": a.peaks,
                "verified_vocal_alignment": verified}, "chat", key="project_id")
            projects.touch(conn, p["id"], "chat", segment_start=s, segment_end=round(s + a.duration, 3))
        r.data = {"segment": {"start": s, "end": round(s + a.duration, 3), "how": how},
                  "duration": a.duration, "tempo_bpm": a.tempo_bpm, "beats": len(a.beats), "lines": len(lines),
                  "segment_audio": str(seg)}
        r.verified += [f"segment cut to {seg.name} ({a.duration:.2f} s)", f"{len(a.beats)} beats measured"]
        if lines:
            (r.verified if verified else r.not_verified).append(
                "sung lines aligned to the voice" if verified else
                "sung lines spread on the beat grid, not matched to the voice (install the align extra for "
                "voice alignment)")
        r.next = f"mb modes, then mb draft --project {p['id']} --mode <mode> --look <look>"

    run("mb analyze", as_json, go)


@concepts_app.command("add")
def concepts_add(project: str = ProjectOpt, file: Path = typer.Option(..., "--file"), as_json: bool = JsonOpt):
    """Store brainstorm concepts written by Claude (JSON list of title, premise, hero_image_idea, sample_shots)."""

    def go(conn, r):
        p = projects.get(conn, project)
        r.project = p["id"]
        cs = board.add_concepts(conn, p["id"], file, "chat")
        r.data = {"concepts": [{k: c[k] for k in ("id", "title", "premise")} for c in cs]}
        r.next = f"mb concepts choose --project {p['id']} --concept <id>"

    run("mb concepts add", as_json, go)


@concepts_app.command("choose")
def concepts_choose(project: str = ProjectOpt, concept: str = typer.Option(..., "--concept"),
                    as_json: bool = JsonOpt):
    """Mark one concept as chosen."""

    def go(conn, r):
        p = projects.get(conn, project)
        r.project = p["id"]
        c = board.choose_concept(conn, p["id"], concept, "chat")
        r.data = {"chosen": c["title"]}

    run("mb concepts choose", as_json, go)


@app.command()
def modes(as_json: bool = JsonOpt) -> None:
    """List story modes (with their animation packs) and looks."""

    def go(conn, r):
        r.data = {
            "modes": [{"slug": m.slug, "name": m.name, "summary": m.summary, "animation": m.animation,
                       "lip_sync": m.lip_sync, "source": m.source} for m in templates.list_modes(conn)],
            "looks": [{"slug": lk.slug, "name": lk.name, "summary": lk.summary, "source": lk.source}
                      for lk in templates.list_looks(conn)],
        }

    run("mb modes", as_json, go)


@app.command()
def draft(
    project: str = ProjectOpt,
    mode: str = typer.Option(..., "--mode"),
    look: str = typer.Option(..., "--look"),
    shots_file: Path = typer.Option(None, "--shots-file", help="Claude-written shot ideas (visual, action, camera)"),
    replace: bool = typer.Option(False, "--replace", help="Replace existing shots"),
    as_json: bool = JsonOpt,
) -> None:
    """Build the timed shot list from a mode plus look (and optional shot ideas)."""

    def go(conn, r):
        p = projects.get(conn, project)
        r.project = p["id"]
        a = repo.get(conn, "song_analysis", p["id"], key="project_id")
        if not a or p["segment_end"] is None:
            raise MbError("INVALID_INPUT", "song not analysed yet", hint=f"mb analyze --project {p['id']}")
        if board.approvals(conn, p["id"])["storyboard"]:
            raise MbError("INVALID_INPUT", "storyboard is approved; revoke it before redrafting",
                          hint=f"mb approve --project {p['id']} --stage storyboard --revoke")
        m, lk = templates.get_mode(mode, conn), templates.get_look(look, conn)
        ideas = draft_mod.load_shot_ideas(shots_file)
        b = registry.get(p["video_backend"])
        shots = draft_mod.draft(conn, p, m, lk, b, {"beats": json.loads(a["beats"]), "lines": json.loads(a["lines"])},
                                ideas, "chat", replace)
        r.data = {"mode": m.slug, "look": lk.slug, "animation": m.animation, "shots": len(shots),
                  "list": [_shot_summary(s) for s in shots]}
        r.verified.append("shots tile the segment with no gaps or overlaps")
        r.verified.append(f"frames rounded up to the {b.name} frame rule")
        if ideas and len(ideas) != len(shots):
            r.not_verified.append(f"{len(ideas)} shot ideas for {len(shots)} timed shots; extra shots use the "
                                  "mode pattern")
        r.next = f"mb sheet --project {p['id']} --kind storyboard"

    run("mb draft", as_json, go)


@shot_app.command("set")
def shot_set(
    project: str = ProjectOpt,
    shot: int = typer.Option(..., "--shot", help="Shot number"),
    field: str = typer.Option(..., "--field"),
    value: str = typer.Option(..., "--value"),
    as_json: bool = JsonOpt,
) -> None:
    """Edit one shot field; prompts follow the project look; finished work is marked for redo."""

    def go(conn, r):
        p = projects.get(conn, project)
        r.project = p["id"]
        s = board.shot_by_ord(conn, p["id"], shot)
        lk = templates.get_look(p["visual_look"], conn) if p.get("visual_look") else None
        s = board.set_field(conn, s["id"], field, value, "chat", lk)
        r.data = {"shot": _shot_summary(s), "plate_prompt": s["plate_prompt"], "motion_prompt": s["motion_prompt"]}

    run("mb shot set", as_json, go)


@shot_app.command("move")
def shot_move(
    project: str = ProjectOpt,
    shot: int = typer.Option(..., "--shot", help="Shot number whose end moves"),
    end: float = typer.Option(..., "--end", help="New end time in segment seconds"),
    as_json: bool = JsonOpt,
) -> None:
    """Move the cut between a shot and the next; snaps to a beat within 0.12 s."""

    def go(conn, r):
        p = projects.get(conn, project)
        r.project = p["id"]
        a = repo.get(conn, "song_analysis", p["id"], key="project_id") or {"beats": "[]"}
        s = board.shot_by_ord(conn, p["id"], shot)
        pair = board.move_boundary(conn, s["id"], end, registry.get(p["video_backend"]), "chat",
                                   json.loads(a["beats"]))
        r.data = {"shots": [_shot_summary(x) for x in pair]}

    run("mb shot move", as_json, go)


@app.command()
def sheet(project: str = ProjectOpt, kind: str = typer.Option("storyboard", "--kind",
          help="storyboard, plates or clips"), as_json: bool = JsonOpt) -> None:
    """Contact sheet image of the board."""

    def go(conn, r):
        p = projects.get(conn, project)
        r.project = p["id"]
        if kind not in ("storyboard", "plates", "clips"):
            raise MbError("INVALID_INPUT", "kind must be storyboard, plates or clips")
        out = contact_sheet.render(conn, p, kind, Path(p["folder"]) / "out" / f"sheet-{kind}.png")
        r.data = {"sheet": str(out)}
        r.verified.append("sheet rendered")
        r.not_verified.append("visual quality of the board: review the sheet")

    run("mb sheet", as_json, go)


@app.command()
def approve(project: str = ProjectOpt, stage: str = typer.Option(..., "--stage"),
            revoke: bool = typer.Option(False, "--revoke"), via: str = typer.Option("chat", "--via"),
            as_json: bool = JsonOpt) -> None:
    """Approve (or revoke) a review gate: storyboard, plates, clips, final."""

    def go(conn, r):
        p = projects.get(conn, project)
        r.project = p["id"]
        r.data = {"approvals": board.approve(conn, p, stage, via, revoke)}
        r.verified.append(f"{stage} {'revoked' if revoke else 'approved'}")

    run("mb approve", as_json, go)


@app.command("export")
def export_cmd(project: str = ProjectOpt, out: Path = typer.Option(..., "--out"),
               no_media: bool = typer.Option(False, "--no-media"), as_json: bool = JsonOpt) -> None:
    """Export the project as a folder with project.json and media."""

    def go(conn, r):
        p = projects.get(conn, project)
        r.project = p["id"]
        path = io_json.export(conn, p, out, with_media=not no_media)
        r.data = {"file": str(path)}

    run("mb export", as_json, go)


@app.command("import")
def import_cmd(file: Path = typer.Option(..., "--file", help="project.json or its folder"),
               as_json: bool = JsonOpt) -> None:
    """Import a project export as a new project."""

    def go(conn, r):
        p = io_json.import_(conn, file)
        r.project = p["id"]
        r.data = {"id": p["id"], "folder": p["folder"], "title": p["title"]}

    run("mb import", as_json, go)
