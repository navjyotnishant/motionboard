"""Projects: folder on disk plus a row in the DB."""

import re
import shutil
import sqlite3
from pathlib import Path

from motionboard import config
from motionboard.db import repo
from motionboard.db.events import Actor
from motionboard.report import MbError

ASPECTS = ("9:16", "16:9")
LOOKS = ("stylized", "realistic")


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:48] or "project"


def create(
    conn: sqlite3.Connection,
    title: str,
    song: Path | None,
    lyrics: str = "",
    idea: str = "",
    aspect: str = "9:16",
    look: str = "stylized",
    actor: Actor = "chat",
    root: Path | None = None,
) -> dict:
    if aspect not in ASPECTS:
        raise MbError("INVALID_INPUT", f"aspect must be one of {', '.join(ASPECTS)}")
    if look not in LOOKS:
        raise MbError("INVALID_INPUT", f"look must be one of {', '.join(LOOKS)}")
    if song is not None and not Path(song).expanduser().is_file():
        raise MbError("NOT_FOUND", f"song file not found: {song}")
    pid = repo.new_id()
    folder = (root or config.projects_root()) / f"{slugify(title)}-{pid[-6:].lower()}"
    for sub in config.PROJECT_SUBDIRS:
        (folder / sub).mkdir(parents=True, exist_ok=True)
    song_path = None
    if song is not None:
        src = Path(song).expanduser().resolve()
        dst = folder / "audio" / f"song{src.suffix.lower()}"
        shutil.copy2(src, dst)
        song_path = str(dst)
    ts = repo.now()
    repo.insert(
        conn,
        "project",
        {
            "id": pid, "title": title, "folder": str(folder), "song_path": song_path, "lyrics": lyrics,
            "idea": idea, "aspect": aspect, "look": look, "created_at": ts, "updated_at": ts,
        },
        actor,
    )
    return repo.get(conn, "project", pid)


def get(conn: sqlite3.Connection, project_id: str) -> dict:
    p = repo.get(conn, "project", project_id)
    if not p:
        rows = conn.execute("SELECT * FROM project WHERE id LIKE ?", (f"%{project_id}",)).fetchall()
        if len(rows) == 1:
            return dict(rows[0])
        raise MbError("NOT_FOUND", f"no project '{project_id}'", hint="mb project list")
    return p


def touch(conn: sqlite3.Connection, project_id: str, actor: Actor, **fields) -> None:
    repo.update(conn, "project", project_id, {**fields, "updated_at": repo.now()}, actor)


def segment_length(project: dict) -> float:
    if project.get("segment_start") is None or project.get("segment_end") is None:
        raise MbError("INVALID_INPUT", "song not analysed yet", hint=f"mb analyze --project {project['id']}")
    return round(project["segment_end"] - project["segment_start"], 3)


def segment_audio(project: dict) -> Path:
    return Path(project["folder"]) / "audio" / "segment.wav"
