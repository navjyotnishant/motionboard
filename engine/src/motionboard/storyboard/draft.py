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
from motionboard.report import MbError
from motionboard.storyboard import timing
from motionboard.storyboard.templates import Look, Mode


def _fmt(text: str, look: Look, lyric: str) -> str:
    return text.replace("{world}", look.world).replace("{lyric}", lyric or "the music")


def plate_prompt(visual: str, has_figure: bool, look: Look, character_lines: list[str]) -> str:
    parts = [visual.rstrip(". ")]
    if has_figure:
        parts += [c for c in character_lines if c]
    parts.append(look.style_line)
    if not has_figure:
        parts.append(look.no_figure_line)
    return ". ".join(p.strip() for p in parts if p) + "."


def motion_prompt(action: str, camera: str, has_figure: bool, look: Look) -> str:
    parts = [action.rstrip(". "), f"Camera: {camera}" if camera else "", look.style_line]
    if not has_figure:
        parts.append(look.no_figure_line)
    return ". ".join(p for p in parts if p) + "."


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
            else:
                visual = _fmt(pat.visual, look, sl.lyric)
                action, camera, has_figure = pat.action, pat.camera, pat.has_figure
                lip = pat.lip_sync and has_figure and bool(sl.lyric) and (
                    mode.lip_sync == "lines" or (mode.lip_sync == "chorus" and _norm(sl.lyric) in chorus))
            cast = cast_in(visual, chars) if has_figure else []
            sid = repo.insert(
                conn,
                "shot",
                {
                    "project_id": pid, "ord": i + 1, "start": sl.start, "end": sl.end,
                    "frames": timing.frames_for(sl.dur, backend.frame_rule),
                    "lyric": sl.lyric, "visual": visual, "action": action, "camera": camera,
                    "has_figure": has_figure, "lip_sync": lip,
                    "plate_prompt": plate_prompt(visual, has_figure, look, [c["style_line"] for c in cast]),
                    "motion_prompt": motion_prompt(action, camera, has_figure, look),
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
