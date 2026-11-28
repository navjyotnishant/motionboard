"""Editing shots, concepts and review gates (T031, T034)."""

import json
import sqlite3
from pathlib import Path

from motionboard import checks
from motionboard.backends.base import VideoBackend
from motionboard.db import repo
from motionboard.db.events import Actor
from motionboard.report import MbError
from motionboard.storyboard import compose, timing
from motionboard.storyboard.draft import clean_creative, parse_motifs, parse_names
from motionboard.storyboard.templates import Look

TEXT_FIELDS = {"lyric", "visual", "action", "camera", "plate_prompt", "motion_prompt"}
BOOL_FIELDS = {"has_figure", "lip_sync"}
CREATIVE_FIELDS = {"intent", "audience", "metaphor", "motifs", "continuity", "materials", "objects"}  # shot.creative
PROMPT_CREATIVE = {"motifs", "continuity", "materials", "objects"}  # these change what the plate and clip should show
PROMPT_FIELDS = {"plate_prompt": "plate", "motion_prompt": "motion"}
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


def cast_lines(conn: sqlite3.Connection, shot_id: str) -> list[str]:
    """Style lines of the characters linked to a shot, in name order."""
    rows = conn.execute(
        "SELECT c.style_line FROM shot_character sc JOIN character c ON c.id = sc.character_id "
        "WHERE sc.shot_id = ? ORDER BY c.name", (shot_id,)).fetchall()
    return [r["style_line"] for r in rows]


def _coerce(field: str, value):
    if field in BOOL_FIELDS:
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("1", "true", "yes", "y")
    return str(value)


def set_field(conn: sqlite3.Connection, shot_id: str, field: str, value, actor: Actor,
              look: Look | None = None, expected_updated_at: str | None = None) -> dict:
    """Edit one shot field and apply the state rules (data-model shot state machine)."""
    editable = TEXT_FIELDS | BOOL_FIELDS | CREATIVE_FIELDS
    if field not in editable:
        raise MbError("INVALID_INPUT", f"field '{field}' cannot be edited here",
                      hint=f"editable: {', '.join(sorted(editable))}; use mb shot move for timing")
    s = get_shot(conn, shot_id)
    if expected_updated_at and s["updated_at"] != expected_updated_at:
        raise MbError("INVALID_INPUT", "shot changed elsewhere; reload and try again", data={"conflict": True})
    project = repo.get(conn, "project", s["project_id"])
    if look is not None and (s["plate_base"] is None or s["motion_base"] is None):
        compose.settle(conn, project, look, actor, [shot_id])  # a shot from before baselines existed
        s = get_shot(conn, shot_id)
    if field in PROMPT_FIELDS:
        # Writing a prompt by hand makes it the creator's override: the engine keeps regenerating the baseline
        # beside it and never rewrites the override (FR-031). Empty text, or the baseline itself, clears it.
        part, text, base = PROMPT_FIELDS[field], str(value).strip(), s[f"{PROMPT_FIELDS[field]}_base"]
        if not text and base is None:
            raise MbError("INVALID_INPUT", "a prompt cannot be empty")
        clearing = base is not None and (not text or text == base)
        v = base if clearing else text
        fields = {field: v, f"{part}_authored": not clearing, "override_kept": _kept_without(s, [part])}
    elif field in CREATIVE_FIELDS:
        creative = compose.creative_of(s)
        if field == "motifs":
            creative["motifs"] = parse_motifs(value)
        elif field in ("materials", "objects"):
            creative[field] = parse_names(value)
        else:
            creative[field] = str(value).strip()
        creative = clean_creative({k: v for k, v in creative.items() if v})
        fields = {"creative": creative}
        v = creative.get(field, "")
    else:
        v = _coerce(field, value)
        fields = {field: v}
    has_figure = v if field == "has_figure" else bool(s["has_figure"])
    if field == "lip_sync" and v and not has_figure:
        raise MbError("INVALID_INPUT", "lip-sync needs a figure in the shot (set has_figure first)")
    if field == "has_figure" and not v:
        fields["lip_sync"] = False
    if look is not None and field not in {"plate_prompt", "motion_prompt", "lyric"} and \
            (field not in CREATIVE_FIELDS or field in PROMPT_CREATIVE):  # keep prompts in step with the edit
        pr = compose.for_shot(conn, project, s, look, overrides=fields)
        if field in {"visual", "has_figure"} | PROMPT_CREATIVE:
            fields["plate_base"] = pr.plate
            if not s["plate_authored"]:
                fields["plate_prompt"] = pr.plate
        if field in {"action", "camera", "has_figure", "lip_sync", "visual"} | PROMPT_CREATIVE:
            fields["motion_base"] = pr.motion
            if not s["motion_authored"]:
                fields["motion_prompt"] = pr.motion
    touched = {k for k in fields if k not in PROMPT_FIELDS or fields[k] != s[k]}
    if field in PROMPT_CREATIVE:
        touched |= {"visual"}  # a motif's state or a continuity rule changes the picture, like a visual edit
    redo_plate = touched & PLATE_FIELDS and s["state"] in PLATE_DONE
    redo_clip = touched & CLIP_FIELDS and s["state"] in CLIP_DONE | {"clip_failed"}
    if redo_plate or redo_clip:
        fields.update(state="needs_redo", dirty=True)
    fields["updated_at"] = repo.now()
    repo.update(conn, "shot", shot_id, fields, actor)
    return get_shot(conn, shot_id)


# --- authored prompt overrides (FR-031 to FR-033) ----------------------------

def _kept(s: dict) -> dict:
    try:
        k = json.loads(s.get("override_kept") or "{}")
    except json.JSONDecodeError:
        k = {}
    return k if isinstance(k, dict) else {}


def _kept_without(s: dict, parts: list[str]) -> dict:
    return {k: v for k, v in _kept(s).items() if k not in parts}


def _parts(part: str) -> list[str]:
    if part not in ("plate", "motion", "both"):
        raise MbError("INVALID_INPUT", "part must be plate, motion or both")
    return ["plate", "motion"] if part == "both" else [part]


def keep_override(conn: sqlite3.Connection, shot_id: str, part: str, version: int, actor: Actor) -> list[str]:
    """The creator reviewed an authored override against art direction `version` and keeps it as written."""
    s = get_shot(conn, shot_id)
    parts = [p for p in _parts(part) if s[f"{p}_authored"]]
    if not parts:
        raise MbError("INVALID_INPUT", f"shot {s['ord']} has no authored {part} prompt to keep",
                      hint="mb shot override list")
    repo.update(conn, "shot", shot_id, {"override_kept": {**_kept(s), **dict.fromkeys(parts, version)}}, actor)
    return parts


def clear_override(conn: sqlite3.Connection, shot_id: str, part: str, actor: Actor,
                   look: Look | None = None) -> list[str]:
    """Drop an authored override: the shot goes back to the generated prompt. Finished work made from the override
    is marked for redo, as after any prompt edit."""
    s = get_shot(conn, shot_id)
    if look is not None and (s["plate_base"] is None or s["motion_base"] is None):
        compose.settle(conn, repo.get(conn, "project", s["project_id"]), look, actor, [shot_id])
        s = get_shot(conn, shot_id)
    parts = [p for p in _parts(part) if s[f"{p}_authored"]]
    if not parts:
        return []
    fields: dict = {"override_kept": _kept_without(s, parts)}
    for p in parts:
        if s[f"{p}_base"] is None:
            raise MbError("INVALID_INPUT", f"shot {s['ord']} has no generated {p} prompt to go back to",
                          hint="the project needs a look first (mb draft)")
        fields.update({f"{p}_prompt": s[f"{p}_base"], f"{p}_authored": False})
    if ("plate" in parts and s["state"] in PLATE_DONE) or \
            ("motion" in parts and s["state"] in CLIP_DONE | {"clip_failed"}):
        fields.update(state="needs_redo", dirty=True)
    fields["updated_at"] = repo.now()
    repo.update(conn, "shot", shot_id, fields, actor)
    return parts


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
        from motionboard.direction import store

        art = store.gate_problem(conn, pid)
        if art:
            problems.append(art)
        problems += [f"shot {s['ord']} plate is {s['state']}" for s in shots
                     if s["state"] not in PLATE_DONE - {"plate_ready"}]
    elif stage == "clips":
        problems += [f"shot {s['ord']} clip is {s['state']}" for s in shots if s["state"] != "clip_approved"]
    elif stage == "final":
        d = repo.get(conn, "delivery", pid, key="project_id")
        if not d or not d.get("video_path"):
            problems.append("no finished video yet; run mb finish")
    return problems


def sung_line_warnings(conn: sqlite3.Connection, project: dict) -> list[str]:
    """Sung lines that the board gives to the singer only in part (see checks.split_lines)."""
    a = repo.get(conn, "song_analysis", project["id"], key="project_id")
    if not a:
        return []
    shots = [dict(r) for r in conn.execute("SELECT * FROM shot WHERE project_id = ? ORDER BY ord", (project["id"],))]
    return checks.split_lines(shots, json.loads(a["lines"] or "[]"))


def literal_warnings(conn: sqlite3.Connection, project: dict) -> list[str]:
    """Shots that repeat their lyric as a picture (see checks.literal_shots), as one line for the report."""
    shots = [dict(r) for r in conn.execute("SELECT * FROM shot WHERE project_id = ? ORDER BY ord", (project["id"],))]
    found = checks.literal_shots(shots)
    if not found:
        return []
    return [f"{len(found)} of {len(shots)} shots illustrate the lyric literally; rework them from the treatment: "
            + "; ".join(found[:6]) + ("; ..." if len(found) > 6 else "")]


def grammar_warnings(conn: sqlite3.Connection, project: dict, look: Look | None) -> list[str]:
    """Shots that contradict the direction: forbidden movement in an action or a motion prompt (generated or
    authored), authored plate prompts against the Bible, undesigned characters (FR-018, FR-028)."""
    from motionboard.direction import conflicts

    return [c["message"] + (" (kept by the creator)" if c["kept"] else "")
            for c in conflicts.for_project(conn, project, look)]


def clip_warnings(conn: sqlite3.Connection, project: dict) -> list[str]:
    """The clips in use that jump scene part way through (see checks.scene_cuts)."""
    out = []
    for r in conn.execute(
            "SELECT s.ord, v.path FROM shot s JOIN asset_version v ON v.shot_id = s.id AND v.kind = 'clip' "
            "AND v.active = 1 WHERE s.project_id = ? ORDER BY s.ord", (project["id"],)):
        path = Path(r["path"])
        problem = checks.clip_problem(path) if path.is_file() else "file is missing"
        if problem:
            out.append(f"shot {r['ord']} clip in use: {problem}")
    return out


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
