"""Editing shots, concepts and review gates (T031, T034)."""

import json
import sqlite3
from pathlib import Path

from motionboard.backends.base import VideoBackend
from motionboard.db import repo
from motionboard.db.events import Actor
from motionboard.report import MbError
from motionboard.storyboard import timing
from motionboard.storyboard.draft import motion_prompt, plate_prompt
from motionboard.storyboard.templates import Look

TEXT_FIELDS = {"lyric", "visual", "action", "camera", "plate_prompt", "motion_prompt"}
BOOL_FIELDS = {"has_figure", "lip_sync"}
PLATE_FIELDS = {"visual", "plate_prompt", "has_figure"}
CLIP_FIELDS = {"action", "camera", "motion_prompt", "lip_sync"}
PLATE_DONE = {"plate_ready", "plate_approved", "clip_queued", "clip_rendering", "clip_ready", "clip_approved",
              "clip_failed"}
CLIP_DONE = {"clip_ready", "clip_approved"}
STAGES = ("storyboard", "plates", "clips", "final")


def get_shot(conn: sqlite3.Connection, shot_id: str) -> dict:
    s = repo.get(conn, "shot", shot_id)
    if not s:
        raise MbError("NOT_FOUND", f"no shot '{shot_id}'")
    return s


def shot_by_ord(conn: sqlite3.Connection, project_id: str, ord_: int) -> dict:
    row = conn.execute("SELECT * FROM shot WHERE project_id = ? AND ord = ?", (project_id, ord_)).fetchone()
    if not row:
        raise MbError("NOT_FOUND", f"no shot {ord_} in project")
    return dict(row)


def _coerce(field: str, value):
    if field in BOOL_FIELDS:
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("1", "true", "yes", "y")
    return str(value)


def set_field(conn: sqlite3.Connection, shot_id: str, field: str, value, actor: Actor,
              look: Look | None = None, expected_updated_at: str | None = None) -> dict:
    """Edit one shot field and apply the state rules (data-model shot state machine)."""
    if field not in TEXT_FIELDS | BOOL_FIELDS:
        raise MbError("INVALID_INPUT", f"field '{field}' cannot be edited here",
                      hint=f"editable: {', '.join(sorted(TEXT_FIELDS | BOOL_FIELDS))}; use mb shot move for timing")
    s = get_shot(conn, shot_id)
    if expected_updated_at and s["updated_at"] != expected_updated_at:
        raise MbError("INVALID_INPUT", "shot changed elsewhere; reload and try again", data={"conflict": True})
    v = _coerce(field, value)
    fields = {field: v}
    has_figure = v if field == "has_figure" else bool(s["has_figure"])
    if field == "lip_sync" and v and not has_figure:
        raise MbError("INVALID_INPUT", "lip-sync needs a figure in the shot (set has_figure first)")
    if field == "has_figure" and not v:
        fields["lip_sync"] = False
    if look is not None:  # keep prompts in step unless the prompt itself is being edited
        visual = v if field == "visual" else s["visual"]
        if field in {"visual", "has_figure"}:
            chars = [c["style_line"] for c in repo.find(conn, "character", project_id=s["project_id"])]
            fields["plate_prompt"] = plate_prompt(visual, has_figure, look, chars)
        if field in {"action", "camera", "has_figure"}:
            fields["motion_prompt"] = motion_prompt(
                v if field == "action" else s["action"], v if field == "camera" else s["camera"], has_figure, look)
    touched = set(fields)
    redo_plate = touched & PLATE_FIELDS and s["state"] in PLATE_DONE
    redo_clip = touched & CLIP_FIELDS and s["state"] in CLIP_DONE | {"clip_failed"}
    if redo_plate or redo_clip:
        fields.update(state="needs_redo", dirty=True)
    fields["updated_at"] = repo.now()
    repo.update(conn, "shot", shot_id, fields, actor)
    return get_shot(conn, shot_id)


def move_boundary(conn: sqlite3.Connection, shot_id: str, new_end: float, backend: VideoBackend,
                  actor: Actor, beats: list[float] | None = None, snap: float = 0.12) -> list[dict]:
    """Move the cut between a shot and the next one. Snaps to a beat within `snap` seconds."""
    s = get_shot(conn, shot_id)
    nxt = conn.execute("SELECT * FROM shot WHERE project_id = ? AND ord = ?",
                       (s["project_id"], s["ord"] + 1)).fetchone()
    if not nxt:
        raise MbError("INVALID_INPUT", "the last shot ends at the end of the segment; move the previous cut instead")
    nxt = dict(nxt)
    if beats:
        b = min(beats, key=lambda x: abs(x - new_end))
        if abs(b - new_end) <= snap:
            new_end = b
    new_end = round(new_end, 3)
    if not (s["start"] + 0.5 <= new_end <= nxt["end"] - 0.5):
        raise MbError("INVALID_INPUT", "each shot must stay at least 0.5 s long")
    ts = repo.now()
    with repo.tx(conn):
        for row, start, end in ((s, s["start"], new_end), (nxt, new_end, nxt["end"])):
            f = {"start": start, "end": end, "frames": timing.frames_for(end - start, backend.frame_rule),
                 "updated_at": ts}
            if row["state"] in CLIP_DONE | {"clip_failed"}:
                f.update(state="needs_redo", dirty=True)
            repo.update(conn, "shot", row["id"], f, actor)
    return [get_shot(conn, s["id"]), get_shot(conn, nxt["id"])]


# --- concepts ----------------------------------------------------------------

def add_concepts(conn: sqlite3.Connection, project_id: str, path: Path, actor: Actor) -> list[dict]:
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError) as e:
        raise MbError("INVALID_INPUT", f"cannot read concepts file: {e}") from e
    items = data.get("concepts", data) if isinstance(data, dict) else data
    if not isinstance(items, list) or not items:
        raise MbError("INVALID_INPUT", "concepts file must be a non-empty list or {\"concepts\": [...]}")
    ids = []
    for c in items:
        if not c.get("title"):
            raise MbError("INVALID_INPUT", "every concept needs a title")
        ids.append(repo.insert(conn, "concept", {
            "project_id": project_id, "title": c["title"], "premise": c.get("premise", ""),
            "hero_image_idea": c.get("hero_image_idea", ""), "sample_shots": c.get("sample_shots", []),
            "chosen": False}, actor))
    return [repo.get(conn, "concept", i) for i in ids]


def choose_concept(conn: sqlite3.Connection, project_id: str, concept_id: str, actor: Actor) -> dict:
    c = repo.get(conn, "concept", concept_id)
    if not c or c["project_id"] != project_id:
        raise MbError("NOT_FOUND", f"no concept '{concept_id}' in this project")
    with repo.tx(conn):
        for row in repo.find(conn, "concept", project_id=project_id, chosen=1):
            repo.update(conn, "concept", row["id"], {"chosen": False}, actor)
        repo.update(conn, "concept", concept_id, {"chosen": True}, actor)
        repo.update(conn, "project", project_id, {"concept_id": concept_id, "updated_at": repo.now()}, actor)
    return repo.get(conn, "concept", concept_id)


# --- gates -------------------------------------------------------------------

def approvals(conn: sqlite3.Connection, project_id: str) -> dict[str, str | None]:
    rows = {r["stage"]: r["approved_at"] for r in repo.find(conn, "stage_approval", project_id=project_id)}
    return {st: rows.get(st) for st in STAGES}


def gate_problems(conn: sqlite3.Connection, project: dict, stage: str) -> list[str]:
    pid = project["id"]
    shots = [dict(r) for r in conn.execute("SELECT * FROM shot WHERE project_id = ? ORDER BY ord", (pid,))]
    problems: list[str] = []
    done = approvals(conn, pid)
    before = STAGES[: STAGES.index(stage)]
    problems += [f"approve the {b} stage first" for b in before if not done[b]]
    if not shots:
        return problems + ["no shots yet; run mb draft"]
    if stage == "storyboard":
        try:
            timing.validate(shots, round(project["segment_end"] - project["segment_start"], 3))
        except ValueError as e:
            problems.append(str(e))
        problems += [f"shot {s['ord']} has no action" for s in shots if not s["action"].strip()]
        problems += [f"shot {s['ord']} has no plate prompt" for s in shots if not s["plate_prompt"].strip()]
    elif stage == "plates":
        problems += [f"shot {s['ord']} plate is {s['state']}" for s in shots
                     if s["state"] not in PLATE_DONE - {"plate_ready"}]
    elif stage == "clips":
        problems += [f"shot {s['ord']} clip is {s['state']}" for s in shots if s["state"] != "clip_approved"]
    elif stage == "final":
        d = repo.get(conn, "delivery", pid, key="project_id")
        if not d or not d.get("video_path"):
            problems.append("no finished video yet; run mb finish")
    return problems


def approve(conn: sqlite3.Connection, project: dict, stage: str, via: str, revoke: bool = False) -> dict:
    if stage not in STAGES:
        raise MbError("INVALID_INPUT", f"stage must be one of {', '.join(STAGES)}")
    pid = project["id"]
    actor: Actor = "studio" if via == "studio" else "chat"
    with repo.tx(conn):
        if revoke:
            for later in STAGES[STAGES.index(stage):]:
                conn.execute("UPDATE stage_approval SET approved_at = NULL WHERE project_id = ? AND stage = ?",
                             (pid, later))
            repo.update(conn, "project", pid, {"updated_at": repo.now()}, actor)
            return approvals(conn, pid)
        problems = gate_problems(conn, project, stage)
        if problems:
            raise MbError("GATE_NOT_APPROVED", f"{stage} cannot be approved yet",
                          hint="; ".join(problems[:8]), data={"problems": problems})
        conn.execute(
            "INSERT INTO stage_approval(project_id, stage, approved_at, via) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(project_id, stage) DO UPDATE SET approved_at = excluded.approved_at, via = excluded.via",
            (pid, stage, repo.now(), via),
        )
        repo.update(conn, "project", pid, {"updated_at": repo.now()}, actor)
    return approvals(conn, pid)


def require_gates(conn: sqlite3.Connection, project_id: str, *stages: str) -> None:
    done = approvals(conn, project_id)
    missing = [s for s in stages if not done[s]]
    if missing:
        raise MbError("GATE_NOT_APPROVED", f"approve {', '.join(missing)} first",
                      hint=f"mb approve --project {project_id} --stage {missing[0]}")
