"""Draft shots from a mode plus look, optionally with Claude-written shot ideas (T030).

The engine owns timing and prompt assembly; Claude owns creative ideas. When a
shots file is given (written by Claude from a chosen concept), its visual,
action, camera and figure choices replace the mode's pattern shot by shot.
Every shot ends up with exactly one clear action.
"""

import json
import re
import sqlite3
from pathlib import Path

from motionboard.backends.base import VideoBackend
from motionboard.db import repo
from motionboard.db.events import Actor
from motionboard.direction import store
from motionboard.report import MbError
from motionboard.storyboard import compose, timing
from motionboard.storyboard.templates import Look, Mode


def _fmt(text: str, look: Look, lyric: str) -> str:
    return text.replace("{world}", look.world).replace("{lyric}", lyric or "the music")


def plate_prompt(visual: str, has_figure: bool, look: Look, character_lines: list[str]) -> str:
    """The first frame without art direction (kept for callers and tests; see storyboard.compose)."""
    return compose.plate_text(visual, has_figure, look, character_lines)


SINGING = compose.SINGING
MAX_WORDS = compose.MAX_WORDS


def motion_prompt(action: str, camera: str, has_figure: bool, look: Look, lip_sync: bool = False,
                  visual: str = "", cast: list[str] | None = None) -> str:
    """What moves, with the look's motion grammar and no art direction (see storyboard.compose)."""
    return compose.motion_text(action, camera, has_figure, look, lip_sync, visual, cast)


def load_shot_ideas(path: Path | None) -> list[dict]:
    if not path:
        return []
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError) as e:
        raise MbError("INVALID_INPUT", f"cannot read shots file: {e}") from e
    ideas = data.get("shots", data) if isinstance(data, dict) else data
    if not isinstance(ideas, list):
        raise MbError("INVALID_INPUT", "shots file must be a list or {\"shots\": [...]}")
    for i, s in enumerate(ideas):
        if not isinstance(s, dict) or not s.get("action"):
            raise MbError("INVALID_INPUT", f"shot idea {i + 1} needs an 'action'")
    return ideas


def draft(
    conn: sqlite3.Connection,
    project: dict,
    mode: Mode,
    look: Look,
    backend: VideoBackend,
    analysis: dict,
    ideas: list[dict] | None = None,
    actor: Actor = "chat",
    replace: bool = False,
) -> list[dict]:
    pid = project["id"]
    existing = conn.execute("SELECT count(*) FROM shot WHERE project_id = ?", (pid,)).fetchone()[0]
    if existing and not replace:
        raise MbError("INVALID_INPUT", f"project already has {existing} shots", hint="add --replace to redraft")
    duration = round(project["segment_end"] - project["segment_start"], 3)
    slots = timing.build(duration, analysis["beats"], analysis["lines"], mode.rhythm)
    for name in mode.characters:  # the mode's cast exists as characters the creator can describe
        if not repo.find(conn, "character", project_id=pid, name=name):
            repo.insert(conn, "character", {"project_id": pid, "name": name, "style_line": ""}, actor)
    chars = {c["name"]: c for c in repo.find(conn, "character", project_id=pid)}
    ideas = ideas or []
    chorus = chorus_lines(project.get("lyrics") or "", [sl.lyric for sl in slots])
    body = store.approved_body(conn, pid)
    ts = repo.now()
    with repo.tx(conn):
        if existing:
            for row in conn.execute("SELECT id FROM shot WHERE project_id = ?", (pid,)).fetchall():
                repo.delete(conn, "shot", row["id"], actor)
        for i, sl in enumerate(slots):
            idea = ideas[i] if i < len(ideas) else None
            pat = mode.pattern[i % len(mode.pattern)]
            if idea:
                visual = idea.get("visual") or _fmt(pat.visual, look, sl.lyric)
                action = idea["action"]
                camera = idea.get("camera", pat.camera)
                has_figure = bool(idea.get("has_figure", pat.has_figure))
                lip = bool(idea.get("lip_sync", False)) and has_figure
                idea_mp = (idea.get("motion_prompt") or "").strip()
                idea_pp = (idea.get("plate_prompt") or "").strip()
                creative = clean_creative(idea.get("creative") or {})
            else:
                idea_mp, idea_pp, creative = "", "", {}
                visual = _fmt(pat.visual, look, sl.lyric)
                action, camera, has_figure = pat.action, pat.camera, pat.has_figure
                lip = pat.lip_sync and has_figure and bool(sl.lyric) and (
                    mode.lip_sync == "lines" or (mode.lip_sync == "chorus" and _norm(sl.lyric) in chorus))
            cast = cast_in(visual, chars) if has_figure else []
            pr = compose.compose(look, body, visual=visual, action=action, camera=camera, has_figure=has_figure,
                                 lip_sync=lip, cast=[{"name": c["name"], "style_line": c["style_line"]} for c in cast],
                                 creative=creative)
            sid = repo.insert(
                conn,
                "shot",
                {
                    "project_id": pid, "ord": i + 1, "start": sl.start, "end": sl.end,
                    "frames": timing.frames_for(sl.dur, backend.frame_rule),
                    "lyric": sl.lyric, "visual": visual, "action": action, "camera": camera,
                    "has_figure": has_figure, "lip_sync": lip,
                    # A prompt written in the shots file is the creator's override: kept beside the generated
                    # baseline, never rewritten by the engine, and checked against the motion grammar (FR-028).
                    "plate_prompt": idea_pp or pr.plate, "motion_prompt": idea_mp or pr.motion,
                    "plate_base": pr.plate, "motion_base": pr.motion,
                    "plate_authored": bool(idea_pp) and idea_pp != pr.plate,
                    "motion_authored": bool(idea_mp) and idea_mp != pr.motion, "creative": creative,
                    "state": "draft", "dirty": False, "updated_at": ts,
                },
                actor,
            )
            for c in cast:
                conn.execute("INSERT INTO shot_character(shot_id, character_id) VALUES (?, ?)", (sid, c["id"]))
        realistic = look.realistic or project["look"] == "realistic"
        has_people = any(s["has_figure"] for s in shots(conn, pid))
        repo.update(
            conn, "project", pid,
            {"mode": mode.slug, "visual_look": look.slug, "synthetic_people": realistic and has_people,
             "updated_at": ts},
            actor,
        )
    return shots(conn, pid)


def _norm(line: str) -> str:
    return re.sub(r"[^\w\s]", "", line.lower()).strip()


def chorus_lines(lyrics: str, segment_lines: list[str]) -> set[str]:
    """Lines sung more than once in the song are the chorus. With no repeats, the whole segment counts,
    because the segment itself is picked as the first chorus."""
    counts: dict[str, int] = {}
    for line in lyrics.splitlines():
        n = _norm(line)
        if n:
            counts[n] = counts.get(n, 0) + 1
    repeated = {n for n, c in counts.items() if c > 1}
    return repeated or {_norm(x) for x in segment_lines if x}


def cast_in(visual: str, chars: dict[str, dict]) -> list[dict]:
    """Characters named in capitals in the visual (HER, HIM, SINGER) appear in that shot."""
    words = set(re.findall(r"[A-Z][A-Z0-9_-]+", visual))
    return [c for name, c in chars.items() if name.upper() in words]


def shots(conn: sqlite3.Connection, project_id: str) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM shot WHERE project_id = ? ORDER BY ord", (project_id,))]


def clean_creative(value) -> dict:
    """Validate a shot's creative context (intent, audience, metaphor, motifs, continuity); all keys optional."""
    if value in (None, "", {}):
        return {}
    if not isinstance(value, dict):
        raise MbError("INVALID_INPUT", "creative must be an object with intent, audience, metaphor, motifs, "
                      "continuity, materials, objects")
    unknown = set(value) - set(compose.CREATIVE_KEYS)
    if unknown:
        raise MbError("INVALID_INPUT", f"unknown creative field(s): {', '.join(sorted(unknown))}",
                      hint=f"fields: {', '.join(compose.CREATIVE_KEYS)}")
    out: dict = {}
    for k in ("intent", "audience", "metaphor", "continuity"):
        if value.get(k):
            out[k] = str(value[k]).strip()
    motifs = parse_motifs(value.get("motifs"))
    if motifs:
        out["motifs"] = motifs
    for k in ("materials", "objects"):
        names = parse_names(value.get(k))
        if names:
            out[k] = names
    return out


def parse_names(value) -> list[str]:
    """Names of Bible materials or objects this shot shows: a list, or text split on commas and lines."""
    if value in (None, "", []):
        return []
    if isinstance(value, str):
        v = value.strip()
        if v.startswith("["):
            try:
                value = json.loads(v)
            except json.JSONDecodeError as e:
                raise MbError("INVALID_INPUT", f"not valid JSON: {e}") from e
        else:
            value = re.split(r"[,\n]", v)
    if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
        raise MbError("INVALID_INPUT", "materials and objects are lists of names from the art direction")
    return list(dict.fromkeys(x.strip() for x in value if x.strip()))


def parse_motifs(value) -> list[dict]:
    """A JSON list of {name, state}, or lines of 'name: state'."""
    if value in (None, "", []):
        return []
    if isinstance(value, str):
        v = value.strip()
        if v.startswith("["):
            try:
                value = json.loads(v)
            except json.JSONDecodeError as e:
                raise MbError("INVALID_INPUT", f"motifs is not valid JSON: {e}") from e
        else:
            value = [{"name": a.strip(), "state": b.strip()} for a, _, b in
                     (line.partition(":") for line in v.splitlines() if line.strip())]
    if not isinstance(value, list):
        raise MbError("INVALID_INPUT", "motifs must be a list of {name, state}")
    out = []
    for m in value:
        if not isinstance(m, dict) or not str(m.get("name", "")).strip():
            raise MbError("INVALID_INPUT", "each motif needs a name (and usually a state)")
        out.append({"name": str(m["name"]).strip(), "state": str(m.get("state", "")).strip()})
    return out
