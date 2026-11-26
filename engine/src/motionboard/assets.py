"""Asset versions (plates, clips, prompts) and per shot review (data model: asset_version, review_note)."""

import json
import shutil
import sqlite3
import subprocess
from pathlib import Path

from motionboard.db import repo
from motionboard.db.events import Actor
from motionboard.report import MbError

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}


def active(conn: sqlite3.Connection, shot_id: str, kind: str) -> dict | None:
    row = conn.execute("SELECT * FROM asset_version WHERE shot_id = ? AND kind = ? AND active = 1",
                       (shot_id, kind)).fetchone()
    return dict(row) if row else None


def _retarget_queued(conn: sqlite3.Connection, shot_id: str, plate_path: str, actor: Actor) -> bool:
    """Point queued or paused render jobs for a shot at its new active plate.

    A job copies the plate path into its settings when it is queued, so without this a plate swapped
    after queueing would still render from the old image. Returns True when a job was updated.
    """
    hit = False
    for j in conn.execute("SELECT id, settings FROM render_job WHERE shot_id = ? AND state IN ('queued','paused')",
                          (shot_id,)).fetchall():
        st = json.loads(j["settings"]) if isinstance(j["settings"], str) else dict(j["settings"])
        if st.get("plate") != plate_path:
            st["plate"] = plate_path
            repo.update(conn, "render_job", j["id"], {"settings": st}, actor)
        hit = True
    return hit


def versions(conn: sqlite3.Connection, shot_id: str, kind: str | None = None) -> list[dict]:
    if kind:
        return repo.find(conn, "asset_version", order="created_at", shot_id=shot_id, kind=kind)
    return repo.find(conn, "asset_version", order="created_at", shot_id=shot_id)


def add(conn: sqlite3.Connection, shot_id: str, kind: str, path: Path | None, source: str, actor: Actor,
        cost_usd: float = 0.0, text: str | None = None, make_active: bool = True) -> dict:
    with repo.tx(conn):
        if make_active:
            for v in repo.find(conn, "asset_version", shot_id=shot_id, kind=kind, active=1):
                repo.update(conn, "asset_version", v["id"], {"active": False}, actor)
        aid = repo.insert(conn, "asset_version", {
            "shot_id": shot_id, "kind": kind, "path": str(path) if path else None, "text": text,
            "source": source, "cost_usd": cost_usd, "active": make_active, "created_at": repo.now()}, actor)
    return repo.get(conn, "asset_version", aid)


def set_active(conn: sqlite3.Connection, asset_id: str, actor: Actor) -> dict:
    a = repo.get(conn, "asset_version", asset_id)
    if not a:
        raise MbError("NOT_FOUND", f"no asset version '{asset_id}'")
    with repo.tx(conn):
        for v in repo.find(conn, "asset_version", shot_id=a["shot_id"], kind=a["kind"], active=1):
            repo.update(conn, "asset_version", v["id"], {"active": False}, actor)
        repo.update(conn, "asset_version", asset_id, {"active": True}, actor)
        state = "plate_ready" if a["kind"] == "plate" else "clip_ready"
        if a["kind"] == "plate" and a["path"] and _retarget_queued(conn, a["shot_id"], a["path"], actor):
            state = "clip_queued"
        repo.update(conn, "shot", a["shot_id"], {"state": state, "updated_at": repo.now()}, actor)
    return repo.get(conn, "asset_version", asset_id)


def store_plate(conn: sqlite3.Connection, project: dict, shot: dict, src: Path, source: str, actor: Actor,
                cost_usd: float = 0.0) -> dict:
    """Copy an image into the project's plates folder, make it the active plate, mark the shot plate_ready."""
    src = Path(src).expanduser()
    if not src.is_file() or src.suffix.lower() not in IMAGE_EXT:
        raise MbError("INVALID_INPUT", f"not an image file: {src}")
    n = len(versions(conn, shot["id"], "plate")) + 1
    dst = Path(project["folder"]) / "plates" / f"shot-{shot['ord']:02d}-v{n}{src.suffix.lower()}"
    if src.resolve() != dst.resolve():
        shutil.copy2(src, dst)
    a = add(conn, shot["id"], "plate", dst, source, actor, cost_usd)
    state = "clip_queued" if _retarget_queued(conn, shot["id"], str(dst), actor) else "plate_ready"
    repo.update(conn, "shot", shot["id"], {"state": state, "dirty": False, "updated_at": repo.now()}, actor)
    return a


def review(conn: sqlite3.Connection, shot: dict, kind: str, decision: str, note: str, actor: Actor) -> dict:
    if kind not in ("plate", "clip"):
        raise MbError("INVALID_INPUT", "kind must be plate or clip")
    if decision not in ("approve", "reject", "comment"):
        raise MbError("INVALID_INPUT", "decision must be approve, reject or comment")
    a = active(conn, shot["id"], kind)
    if not a:
        raise MbError("INVALID_INPUT", f"shot {shot['ord']} has no {kind} to review")
    if decision == "reject" and not note.strip():
        raise MbError("INVALID_INPUT", "say why when rejecting, so the redo can fix it")
    with repo.tx(conn):
        repo.insert(conn, "review_note", {"asset_version_id": a["id"], "decision": decision, "text": note,
                                          "at": repo.now()}, actor)
        if decision == "approve":
            state = "plate_approved" if kind == "plate" else "clip_approved"
            repo.update(conn, "shot", shot["id"], {"state": state, "dirty": False, "updated_at": repo.now()}, actor)
        elif decision == "reject":
            repo.update(conn, "shot", shot["id"], {"state": "needs_redo", "updated_at": repo.now()}, actor)
    return repo.get(conn, "shot", shot["id"])


def probe(path: Path) -> dict:
    """Frames, size and duration of a video via ffprobe."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
         "stream=nb_read_frames,width,height,r_frame_rate:format=duration", "-of", "json", str(path)],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise MbError("INVALID_INPUT", f"cannot read video {path}: {r.stderr.strip()}")
    d = json.loads(r.stdout)
    st = d["streams"][0]
    num, den = (int(x) for x in st["r_frame_rate"].split("/"))
    return {"frames": int(st.get("nb_read_frames", 0)), "width": st["width"], "height": st["height"],
            "fps": round(num / den, 3), "duration": float(d["format"]["duration"])}
