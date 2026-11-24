"""Render queue in the render_job table (research R10)."""

import json
import sqlite3
from pathlib import Path

from motionboard import assets, projects
from motionboard.backends.base import VideoBackend
from motionboard.db import repo
from motionboard.db.events import Actor
from motionboard.report import MbError

PAUSE_KEY = "queue_paused"
ACTIVE = ("queued", "running", "paused")


def clip_path(project: dict, shot: dict, version: int) -> Path:
    return Path(project["folder"]) / "clips" / f"shot-{shot['ord']:02d}-v{version}.mp4"


def has_valid_clip(conn: sqlite3.Connection, shot: dict) -> bool:
    a = assets.active(conn, shot["id"], "clip")
    return bool(a and a["path"] and Path(a["path"]).exists() and shot["state"] in ("clip_ready", "clip_approved")
                and not shot["dirty"])


def enqueue_clips(conn: sqlite3.Connection, project: dict, backend: VideoBackend, ords: list[int] | None,
                  redo: bool, actor: Actor) -> dict:
    rows = [dict(r) for r in conn.execute("SELECT * FROM shot WHERE project_id = ? ORDER BY ord", (project["id"],))]
    if ords:
        rows = [r for r in rows if r["ord"] in set(ords)]
    w, h = backend.sizes[project["aspect"]]
    queued, skipped = [], []
    base_pri = conn.execute("SELECT coalesce(max(priority), 0) FROM render_job").fetchone()[0]
    for i, s in enumerate(rows):
        if not redo and has_valid_clip(conn, s):
            skipped.append({"shot": s["ord"], "reason": "has a finished clip"})
            continue
        if conn.execute("SELECT 1 FROM render_job WHERE shot_id = ? AND state IN ('queued','running','paused')",
                        (s["id"],)).fetchone():
            skipped.append({"shot": s["ord"], "reason": "already queued"})
            continue
        plate = assets.active(conn, s["id"], "plate")
        if not plate or not plate["path"] or not Path(plate["path"]).exists():
            skipped.append({"shot": s["ord"], "reason": "no plate"})
            continue
        version = len(assets.versions(conn, s["id"], "clip")) + 1
        settings = {"mode": "a2v" if s["lip_sync"] else "i2v", "width": w, "height": h,
                    "frames": backend.frame_rule(s["frames"]), "fps": 24, "seed": 42, "plate": plate["path"],
                    "prompt": s["motion_prompt"], "out": str(clip_path(project, s, version))}
        jid = repo.insert(conn, "render_job", {
            "project_id": project["id"], "shot_id": s["id"], "kind": "lipsync" if s["lip_sync"] else "clip",
            "backend": backend.name, "settings": settings, "priority": base_pri + i + 1, "state": "queued",
            "log_path": str(Path(project["folder"]) / "logs" / f"shot-{s['ord']:02d}-v{version}.log"),
            "created_at": repo.now()}, actor)
        repo.update(conn, "shot", s["id"], {"state": "clip_queued", "updated_at": repo.now()}, actor)
        queued.append({"shot": s["ord"], "job": jid, "frames": settings["frames"], "mode": settings["mode"]})
    return {"queued": queued, "skipped": skipped, "size": f"{w}x{h}"}


def jobs(conn: sqlite3.Connection, project_id: str | None = None, active_only: bool = True) -> list[dict]:
    sql = ("SELECT j.*, s.ord AS shot_ord FROM render_job j LEFT JOIN shot s ON s.id = j.shot_id WHERE 1=1")
    args: list = []
    if project_id:
        sql += " AND j.project_id = ?"
        args.append(project_id)
    if active_only:
        sql += " AND j.state IN ('queued','running','paused')"
    sql += " ORDER BY CASE j.state WHEN 'running' THEN 0 ELSE 1 END, j.priority, j.created_at"
    out = []
    for r in conn.execute(sql, args).fetchall():
        d = dict(r)
        d["settings"] = json.loads(d["settings"])
        out.append(d)
    return out


def next_job(conn: sqlite3.Connection) -> dict | None:
    r = conn.execute("SELECT * FROM render_job WHERE state = 'queued' ORDER BY priority, created_at LIMIT 1").fetchone()
    return dict(r) if r else None


def paused(conn: sqlite3.Connection) -> bool:
    return bool(repo.get_setting(conn, PAUSE_KEY, False))


def pause(conn: sqlite3.Connection, actor: Actor) -> None:
    """Pause after the current shot: the worker finishes the running job, then waits."""
    repo.set_setting(conn, PAUSE_KEY, True, actor)


def resume(conn: sqlite3.Connection, actor: Actor) -> None:
    repo.set_setting(conn, PAUSE_KEY, False, actor)


def stop(conn: sqlite3.Connection, project_id: str | None, actor: Actor) -> int:
    """Stop the running job now and remove queued ones; affected shots go back to plate_approved."""
    n = 0
    for j in jobs(conn, project_id):
        repo.update(conn, "render_job", j["id"], {"state": "stopped", "stop_reason": "stopped by request",
                                                  "ended_at": repo.now()}, actor)
        if j["shot_id"] and j["state"] == "queued":
            repo.update(conn, "shot", j["shot_id"], {"state": "plate_approved", "updated_at": repo.now()}, actor)
        n += 1
    return n


def move(conn: sqlite3.Connection, job_id: str, position: int, actor: Actor) -> list[dict]:
    queued = [j for j in jobs(conn) if j["state"] == "queued"]
    ids = [j["id"] for j in queued]
    if job_id not in ids:
        raise MbError("NOT_FOUND", f"job '{job_id}' is not queued")
    ids.remove(job_id)
    ids.insert(max(0, min(position - 1, len(ids))), job_id)
    with repo.tx(conn):
        for i, jid in enumerate(ids):
            repo.update(conn, "render_job", jid, {"priority": i + 1}, actor)
    return [j for j in jobs(conn) if j["state"] == "queued"]


def project_of(conn: sqlite3.Connection, job: dict) -> dict:
    return projects.get(conn, job["project_id"])
