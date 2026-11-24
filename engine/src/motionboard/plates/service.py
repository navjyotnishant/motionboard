"""Requesting plates for shots: gate check, cost confirmation, adapter call, storage."""

import sqlite3
from pathlib import Path

from motionboard import assets
from motionboard.db import repo
from motionboard.db.events import Actor
from motionboard.plates import adapter as adapters
from motionboard.plates.adapter import Pending, PlateRequest
from motionboard.report import MbError
from motionboard.storyboard import board, templates

PLATE_SIZES = {"9:16": (1080, 1920), "16:9": (1920, 1080)}
NEEDS_PLATE = {"draft", "needs_redo", "plate_requested"}


def shots_needing_plates(conn: sqlite3.Connection, project_id: str, ords: list[int] | None) -> list[dict]:
    rows = [dict(r) for r in conn.execute("SELECT * FROM shot WHERE project_id = ? ORDER BY ord", (project_id,))]
    if ords:
        wanted = set(ords)
        missing = wanted - {r["ord"] for r in rows}
        if missing:
            raise MbError("NOT_FOUND", f"no shots {sorted(missing)}")
        return [r for r in rows if r["ord"] in wanted]
    return [r for r in rows if r["state"] in NEEDS_PLATE or not assets.active(conn, r["id"], "plate")]


def _reference(conn: sqlite3.Connection, shot_id: str) -> Path | None:
    row = conn.execute(
        "SELECT c.reference_image FROM shot_character sc JOIN character c ON c.id = sc.character_id "
        "WHERE sc.shot_id = ? AND c.reference_image IS NOT NULL LIMIT 1", (shot_id,)).fetchone()
    return Path(row[0]) if row and row[0] and Path(row[0]).exists() else None


def request_plates(conn: sqlite3.Connection, project: dict, adapter_name: str, ords: list[int] | None,
                   confirm_cost: bool, actor: Actor) -> dict:
    board.require_gates(conn, project["id"], "storyboard")
    adapters.ensure_default_manual(conn)
    row = adapters.get_row(conn, adapter_name)
    ad = adapters.build(row, project)
    shots = shots_needing_plates(conn, project["id"], ords)
    est = round(len(shots) * float(row["cost_per_image_usd"]), 4)
    if est > 0 and not confirm_cost:
        raise MbError("COST_NOT_CONFIRMED", f"{len(shots)} plates with '{row['name']}' cost about ${est:.2f}",
                      hint="re-run with --confirm-cost after the creator says yes",
                      data={"est_cost_usd": est, "shots": [s["ord"] for s in shots], "adapter": row["name"]})
    look = templates.get_look(project["visual_look"], conn) if project.get("visual_look") else None
    w, h = PLATE_SIZES[project["aspect"]]
    tmp = Path(project["folder"]) / "plates" / "incoming"
    tmp.mkdir(parents=True, exist_ok=True)
    done, pending, failed, spent = [], [], [], 0.0
    for s in shots:
        rid = repo.insert(conn, "plate_request", {
            "shot_id": s["id"], "adapter_id": row["id"], "prompt": s["plate_prompt"],
            "reference_image": str(_reference(conn, s["id"]) or "") or None,
            "state": "approved_cost" if est > 0 else "pending",
            "est_cost_usd": float(row["cost_per_image_usd"]), "created_at": repo.now()}, actor)
        req = PlateRequest(rid, s["id"], s["ord"], s["plate_prompt"], look.negative if look else "", w, h,
                           tmp / f"shot-{s['ord']:02d}-{rid[-6:].lower()}.png", _reference(conn, s["id"]))
        try:
            res = ad.request(req)
        except MbError as e:
            repo.update(conn, "plate_request", rid, {"state": "failed"}, actor)
            failed.append({"shot": s["ord"], "error": e.message})
            continue
        if isinstance(res, Pending):
            repo.update(conn, "shot", s["id"], {"state": "plate_requested", "updated_at": repo.now()}, actor)
            pending.append({"shot": s["ord"], "request": rid, "prompt": s["plate_prompt"],
                            "reference_image": str(req.reference_image) if req.reference_image else None})
            continue
        a = assets.store_plate(conn, project, s, res.path, row["name"], actor, res.cost_usd)
        repo.update(conn, "plate_request", rid, {"state": "done", "result_asset_id": a["id"]}, actor)
        spent += res.cost_usd
        done.append({"shot": s["ord"], "path": a["path"]})
    return {"adapter": row["name"], "kind": row["kind"], "done": done, "pending": pending, "failed": failed,
            "spent_usd": round(spent, 4), "est_cost_usd": est, "size": f"{w}x{h}"}


def pending_requests(conn: sqlite3.Connection, project_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT pr.id, pr.prompt, pr.reference_image, s.ord FROM plate_request pr JOIN shot s ON s.id = pr.shot_id "
        "WHERE s.project_id = ? AND pr.state IN ('pending', 'approved_cost') ORDER BY s.ord, pr.created_at",
        (project_id,)).fetchall()
    return [{"request": r["id"], "shot": r["ord"], "prompt": r["prompt"], "reference_image": r["reference_image"]}
            for r in rows]


def fulfil(conn: sqlite3.Connection, project: dict, request_id: str, file: Path, actor: Actor) -> dict:
    pr = repo.get(conn, "plate_request", request_id)
    if not pr:
        raise MbError("NOT_FOUND", f"no plate request '{request_id}'")
    shot = repo.get(conn, "shot", pr["shot_id"])
    if shot["project_id"] != project["id"]:
        raise MbError("NOT_FOUND", "request belongs to another project")
    a = assets.store_plate(conn, project, shot, file, "handoff", actor, pr["est_cost_usd"])
    repo.update(conn, "plate_request", request_id, {"state": "done", "result_asset_id": a["id"]}, actor)
    return a


def upload(conn: sqlite3.Connection, project: dict, ord_: int, file: Path, actor: Actor) -> dict:
    shot = board.shot_by_ord(conn, project["id"], ord_)
    return assets.store_plate(conn, project, shot, file, "upload", actor)
