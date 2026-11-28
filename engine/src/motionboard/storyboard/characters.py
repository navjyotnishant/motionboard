"""Characters: a name, a reference image and a style line, linked to the shots they appear in (T068)."""

import json
import shutil
import sqlite3
from pathlib import Path

from motionboard.db import repo
from motionboard.db.events import Actor
from motionboard.report import MbError
from motionboard.storyboard import board, compose
from motionboard.storyboard.templates import Look

FIELDS = {"style_line", "reference_image", "name"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}
PURPOSES = ("face", "silhouette", "costume", "material", "detail", "turnaround", "other")


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
                    "references": references(conn, c["id"]), "shots": shots})
    return out


def _store_reference(project: dict, name: str, src: Path, purpose: str = "") -> str:
    """Copy a reference image into plates/characters/. The first one is NAME.ext (as before 003); later ones get a
    purpose and a number so nothing is overwritten."""
    src = Path(src).expanduser()
    if not src.is_file():
        raise MbError("NOT_FOUND", f"reference image not found: {src}")
    if src.suffix.lower() not in IMAGE_EXT:
        raise MbError("INVALID_INPUT", f"reference must be an image ({', '.join(sorted(IMAGE_EXT))})")
    dest_dir = Path(project["folder"]) / "plates" / "characters"
    dest_dir.mkdir(parents=True, exist_ok=True)
    ext = src.suffix.lower()
    dest = dest_dir / f"{name.lower()}{ext}"
    n = 2
    while dest.exists() and dest.resolve() != src.resolve():
        dest = dest_dir / f"{name.lower()}-{purpose or 'ref'}-{n}{ext}"
        n += 1
    if dest.resolve() != src.resolve():
        shutil.copy2(src, dest)
    return str(dest)


# --- references (feature 003): several per character, one primary -------------------------------------------

def references(conn: sqlite3.Connection, character_id: str) -> list[dict]:
    rows = conn.execute("SELECT * FROM character_reference WHERE character_id = ? ORDER BY is_primary DESC, ord, "
                        "created_at", (character_id,)).fetchall()
    return [{"id": r["id"], "path": r["path"], "purpose": r["purpose"], "description": r["description"],
             "primary": bool(r["is_primary"]), "ord": r["ord"], "exists": Path(r["path"]).exists(),
             "meta": json.loads(r["meta"] or "{}")} for r in rows]


def _sync_legacy(conn: sqlite3.Connection, character_id: str, actor: Actor) -> None:
    """character.reference_image mirrors the primary reference for older readers (research R7)."""
    row = conn.execute("SELECT path FROM character_reference WHERE character_id = ? AND is_primary = 1",
                       (character_id,)).fetchone()
    repo.update(conn, "character", character_id, {"reference_image": row["path"] if row else None}, actor)


def _redo_plates(conn: sqlite3.Connection, character_id: str, actor: Actor) -> list[int]:
    """A new look for a character means plates made from the old references are out of date."""
    changed = []
    for sid in _shot_ids(conn, character_id):
        s = board.get_shot(conn, sid)
        if s["state"] in board.PLATE_DONE:
            repo.update(conn, "shot", sid, {"state": "needs_redo", "dirty": True, "updated_at": repo.now()}, actor)
            changed.append(s["ord"])
    return changed


def add_reference(conn: sqlite3.Connection, project: dict, name: str, src: Path, purpose: str, description: str,
                  primary: bool, actor: Actor) -> tuple[dict, list[int]]:
    if purpose not in PURPOSES:
        raise MbError("INVALID_INPUT", f"purpose must be one of {', '.join(PURPOSES)}")
    c = get(conn, project["id"], name)
    existing = references(conn, c["id"])
    path = _store_reference(project, c["name"], src, purpose)
    make_primary = primary or not any(r["primary"] for r in existing)
    with repo.tx(conn):
        if make_primary:
            conn.execute("UPDATE character_reference SET is_primary = 0 WHERE character_id = ?", (c["id"],))
        rid = repo.insert(conn, "character_reference", {
            "character_id": c["id"], "path": path, "purpose": purpose, "description": description.strip(),
            "is_primary": make_primary, "ord": max([r["ord"] for r in existing], default=-1) + 1, "meta": {},
            "created_at": repo.now()}, actor)
        _sync_legacy(conn, c["id"], actor)
        changed = _redo_plates(conn, c["id"], actor)
    return next(r for r in references(conn, c["id"]) if r["id"] == rid), changed


def _ref_row(conn: sqlite3.Connection, project: dict, ref_id: str) -> dict:
    row = conn.execute("SELECT r.*, c.project_id, c.name FROM character_reference r JOIN character c "
                       "ON c.id = r.character_id WHERE r.id = ?", (ref_id,)).fetchone()
    if not row or row["project_id"] != project["id"]:
        raise MbError("NOT_FOUND", f"no reference '{ref_id}' in this project", hint="mb character ref list")
    return dict(row)


def remove_reference(conn: sqlite3.Connection, project: dict, ref_id: str, actor: Actor) -> tuple[dict, list[int]]:
    """Remove a reference row. The image file stays on disk. A new primary is picked if needed."""
    r = _ref_row(conn, project, ref_id)
    with repo.tx(conn):
        repo.delete(conn, "character_reference", ref_id, actor)
        if r["is_primary"]:
            nxt = conn.execute("SELECT id FROM character_reference WHERE character_id = ? ORDER BY ord, created_at "
                               "LIMIT 1", (r["character_id"],)).fetchone()
            if nxt:
                repo.update(conn, "character_reference", nxt["id"], {"is_primary": True}, actor)
        _sync_legacy(conn, r["character_id"], actor)
        changed = _redo_plates(conn, r["character_id"], actor)
    return {"id": ref_id, "character": r["name"], "path": r["path"], "file_kept": True}, changed


def set_primary(conn: sqlite3.Connection, project: dict, ref_id: str, actor: Actor) -> tuple[dict, list[int]]:
    r = _ref_row(conn, project, ref_id)
    with repo.tx(conn):
        conn.execute("UPDATE character_reference SET is_primary = 0 WHERE character_id = ?", (r["character_id"],))
        repo.update(conn, "character_reference", ref_id, {"is_primary": True}, actor)
        _sync_legacy(conn, r["character_id"], actor)
        changed = _redo_plates(conn, r["character_id"], actor)
    return next(x for x in references(conn, r["character_id"]) if x["id"] == ref_id), changed


def shot_references(conn: sqlite3.Connection, shot_id: str) -> list[dict]:
    """Every reference of every character in the shot: characters by name, each primary first, then by order."""
    out = []
    for c in conn.execute("SELECT c.id, c.name FROM shot_character sc JOIN character c ON c.id = sc.character_id "
                          "WHERE sc.shot_id = ? ORDER BY c.name", (shot_id,)):
        for r in references(conn, c["id"]):
            out.append({"character": c["name"], "path": r["path"], "purpose": r["purpose"], "primary": r["primary"],
                        "description": r["description"]})
    return out


def _shot_ids(conn: sqlite3.Connection, character_id: str) -> list[str]:
    return [r["shot_id"] for r in conn.execute(
        "SELECT shot_id FROM shot_character WHERE character_id = ?", (character_id,)).fetchall()]


def refresh_prompts(conn: sqlite3.Connection, shot_ids: list[str], look: Look | None, actor: Actor) -> list[int]:
    """Rebuild prompts for shots whose cast changed. Finished plates whose first frame changed are marked for redo."""
    if look is None or not shot_ids:
        return []
    sid = shot_ids[0]
    project = repo.get(conn, "project", board.get_shot(conn, sid)["project_id"])
    return compose.recompose(conn, project, shot_ids, look, actor, mark_redo=True)


def add(conn: sqlite3.Connection, project: dict, name: str, style_line: str, reference: Path | None,
        actor: Actor) -> dict:
    name = name.strip().upper()
    if not name or not name.replace("-", "").replace("_", "").isalnum():
        raise MbError("INVALID_INPUT", "character names are one word, letters and digits (HER, HIM, SINGER)")
    if repo.find(conn, "character", project_id=project["id"], name=name):
        raise MbError("INVALID_INPUT", f"character '{name}' already exists", hint="use mb character set")
    with repo.tx(conn):
        repo.insert(conn, "character", {"project_id": project["id"], "name": name, "style_line": style_line.strip(),
                                        "reference_image": None}, actor)
        if reference:
            add_reference(conn, project, name, reference, "other", "", True, actor)
    return get(conn, project["id"], name)


def set_field(conn: sqlite3.Connection, project: dict, name: str, field: str, value: str, look: Look | None,
              actor: Actor) -> tuple[dict, list[int]]:
    if field not in FIELDS:
        raise MbError("INVALID_INPUT", f"field '{field}' cannot be set", hint=f"fields: {', '.join(sorted(FIELDS))}")
    c = get(conn, project["id"], name)
    compose.settle(conn, project, look, actor)  # before the change, so hand-written prompts are recognised
    if field == "reference_image":  # replaces the primary reference (the single reference of older projects)
        with repo.tx(conn):
            old = conn.execute("SELECT id FROM character_reference WHERE character_id = ? AND is_primary = 1",
                               (c["id"],)).fetchone()
            if old:
                repo.delete(conn, "character_reference", old["id"], actor)
            changed: list[int] = []
            if value:
                _, changed = add_reference(conn, project, c["name"], Path(value), "other", "", True, actor)
            else:
                _sync_legacy(conn, c["id"], actor)
                changed = _redo_plates(conn, c["id"], actor)
        return repo.get(conn, "character", c["id"]), sorted(set(changed))
    with repo.tx(conn):
        if field == "name":
            v = value.strip().upper()
            if repo.find(conn, "character", project_id=project["id"], name=v):
                raise MbError("INVALID_INPUT", f"character '{v}' already exists")
        else:
            v = value.strip()
        repo.update(conn, "character", c["id"], {field: v}, actor)
        changed = refresh_prompts(conn, _shot_ids(conn, c["id"]), look, actor) if field == "style_line" else []
    return repo.get(conn, "character", c["id"]), sorted(set(changed))


def link(conn: sqlite3.Connection, project: dict, name: str, ords: list[int], on: bool, look: Look | None,
         actor: Actor) -> list[int]:
    c = get(conn, project["id"], name)
    compose.settle(conn, project, look, actor)
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
