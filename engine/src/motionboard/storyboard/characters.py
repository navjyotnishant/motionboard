"""Characters: a name, a reference image and a style line, linked to the shots they appear in (T068)."""

import shutil
import sqlite3
from pathlib import Path

from motionboard.db import repo
from motionboard.db.events import Actor
from motionboard.report import MbError
from motionboard.storyboard import board
from motionboard.storyboard.draft import plate_prompt
from motionboard.storyboard.templates import Look

FIELDS = {"style_line", "reference_image", "name"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}


def get(conn: sqlite3.Connection, project_id: str, name: str) -> dict:
    rows = repo.find(conn, "character", project_id=project_id, name=name.upper())
    if not rows:
        raise MbError("NOT_FOUND", f"no character '{name}' in project", hint="mb character add --name ...")
    return rows[0]


def listing(conn: sqlite3.Connection, project_id: str) -> list[dict]:
    out = []
    for c in sorted(repo.find(conn, "character", project_id=project_id), key=lambda c: c["name"]):
        shots = [r["ord"] for r in conn.execute(
            "SELECT s.ord FROM shot_character sc JOIN shot s ON s.id = sc.shot_id WHERE sc.character_id = ? "
            "ORDER BY s.ord", (c["id"],)).fetchall()]
        out.append({"name": c["name"], "style_line": c["style_line"], "reference_image": c["reference_image"],
                    "shots": shots})
    return out


def _store_reference(project: dict, name: str, src: Path) -> str:
    src = Path(src).expanduser()
    if not src.is_file():
        raise MbError("NOT_FOUND", f"reference image not found: {src}")
    if src.suffix.lower() not in IMAGE_EXT:
        raise MbError("INVALID_INPUT", f"reference must be an image ({', '.join(sorted(IMAGE_EXT))})")
    dest_dir = Path(project["folder"]) / "plates" / "characters"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{name.lower()}{src.suffix.lower()}"
    shutil.copy2(src, dest)
    return str(dest)


def _shot_ids(conn: sqlite3.Connection, character_id: str) -> list[str]:
    return [r["shot_id"] for r in conn.execute(
        "SELECT shot_id FROM shot_character WHERE character_id = ?", (character_id,)).fetchall()]


def refresh_prompts(conn: sqlite3.Connection, shot_ids: list[str], look: Look | None, actor: Actor) -> list[int]:
    """Rebuild plate prompts for shots whose cast changed. Finished plates are marked for redo."""
    if look is None:
        return []
    changed = []
    for sid in shot_ids:
        s = board.get_shot(conn, sid)
        new = plate_prompt(s["visual"], bool(s["has_figure"]), look, board.cast_lines(conn, sid))
        if new == s["plate_prompt"]:
            continue
        fields = {"plate_prompt": new, "updated_at": repo.now()}
        if s["state"] in board.PLATE_DONE:
            fields.update(state="needs_redo", dirty=True)
        repo.update(conn, "shot", sid, fields, actor)
        changed.append(s["ord"])
    return changed


def add(conn: sqlite3.Connection, project: dict, name: str, style_line: str, reference: Path | None,
        actor: Actor) -> dict:
    name = name.strip().upper()
    if not name or not name.replace("-", "").replace("_", "").isalnum():
        raise MbError("INVALID_INPUT", "character names are one word, letters and digits (HER, HIM, SINGER)")
    if repo.find(conn, "character", project_id=project["id"], name=name):
        raise MbError("INVALID_INPUT", f"character '{name}' already exists", hint="use mb character set")
    ref = _store_reference(project, name, reference) if reference else None
    with repo.tx(conn):
        repo.insert(conn, "character", {"project_id": project["id"], "name": name, "style_line": style_line.strip(),
                                        "reference_image": ref}, actor)
    return get(conn, project["id"], name)


def set_field(conn: sqlite3.Connection, project: dict, name: str, field: str, value: str, look: Look | None,
              actor: Actor) -> tuple[dict, list[int]]:
    if field not in FIELDS:
        raise MbError("INVALID_INPUT", f"field '{field}' cannot be set", hint=f"fields: {', '.join(sorted(FIELDS))}")
    c = get(conn, project["id"], name)
    with repo.tx(conn):
        if field == "reference_image":
            v = _store_reference(project, c["name"], Path(value)) if value else None
        elif field == "name":
            v = value.strip().upper()
            if repo.find(conn, "character", project_id=project["id"], name=v):
                raise MbError("INVALID_INPUT", f"character '{v}' already exists")
        else:
            v = value.strip()
        repo.update(conn, "character", c["id"], {field: v}, actor)
        changed = refresh_prompts(conn, _shot_ids(conn, c["id"]), look, actor) if field == "style_line" else []
        if field == "reference_image":  # a new face means plates made from the old one are out of date
            for sid in _shot_ids(conn, c["id"]):
                s = board.get_shot(conn, sid)
                if s["state"] in board.PLATE_DONE:
                    repo.update(conn, "shot", sid, {"state": "needs_redo", "dirty": True,
                                                    "updated_at": repo.now()}, actor)
                    changed.append(s["ord"])
    return repo.get(conn, "character", c["id"]), sorted(set(changed))


def link(conn: sqlite3.Connection, project: dict, name: str, ords: list[int], on: bool, look: Look | None,
         actor: Actor) -> list[int]:
    c = get(conn, project["id"], name)
    sids = []
    with repo.tx(conn):
        for o in ords:
            s = board.shot_by_ord(conn, project["id"], o)
            if on and not s["has_figure"]:
                raise MbError("INVALID_INPUT", f"shot {o} has no figure", hint="set has_figure on that shot first")
            if on:
                conn.execute("INSERT OR IGNORE INTO shot_character(shot_id, character_id) VALUES (?, ?)",
                             (s["id"], c["id"]))
            else:
                conn.execute("DELETE FROM shot_character WHERE shot_id = ? AND character_id = ?", (s["id"], c["id"]))
            sids.append(s["id"])
        return refresh_prompts(conn, sids, look, actor)
