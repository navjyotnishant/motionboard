"""Requesting plates for shots: gate check, cost confirmation, adapter call, storage."""

import json
import sqlite3
from pathlib import Path

from motionboard import assets
from motionboard.db import repo
from motionboard.db.events import Actor
from motionboard.direction import store
from motionboard.plates import adapter as adapters
from motionboard.plates.adapter import Pending, PlateRequest, Reference
from motionboard.report import MbError
from motionboard.storyboard import board, characters, compose, templates

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


def _references(conn: sqlite3.Connection, shot_id: str) -> list[Reference]:
    """Every reference of every character linked to the shot (FR-011); the old single LIMIT 1 pick is gone."""
    return [Reference(r["character"], Path(r["path"]), r["purpose"], r["primary"], r["description"])
            for r in characters.shot_references(conn, shot_id)]


def request_plates(conn: sqlite3.Connection, project: dict, adapter_name: str, ords: list[int] | None,
                   confirm_cost: bool, actor: Actor, reference_strategy: str | None = None) -> dict:
    board.require_gates(conn, project["id"], "storyboard")
    art = store.gate_problem(conn, project["id"])
    if art:
        raise MbError("GATE_NOT_APPROVED", art, hint=f"mb art show -p {project['id']} --pending; the creator approves")
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
    negative = compose.negative_text(look, store.approved_body(conn, project["id"])) if look else ""
    strategy = reference_strategy or json.loads(row["config"] or "{}").get("reference_strategy") or "strict"
    capacity = ad.reference_capacity()
    w, h = PLATE_SIZES[project["aspect"]]
    tmp = Path(project["folder"]) / "plates" / "incoming"
    tmp.mkdir(parents=True, exist_ok=True)
    done, pending, failed, spent = [], [], [], 0.0
    for s in shots:
        wanted = _references(conn, s["id"])
        try:
            sent, dropped = adapters.select_references(wanted, capacity, strategy, row["name"])
        except MbError as e:
            failed.append({"shot": s["ord"], "error": e.message, "hint": e.hint,
                           "references": [r.as_dict() for r in wanted]})
            continue
        refs = [r.as_dict() for r in sent]
        rid = repo.insert(conn, "plate_request", {
            "shot_id": s["id"], "adapter_id": row["id"], "prompt": s["plate_prompt"],
            "reference_image": refs[0]["path"] if refs else None, "refs": refs, "refs_dropped": dropped,
            "state": "approved_cost" if est > 0 else "pending",
            "est_cost_usd": float(row["cost_per_image_usd"]), "created_at": repo.now()}, actor)
        req = PlateRequest(rid, s["id"], s["ord"], s["plate_prompt"], negative, w, h,
                           tmp / f"shot-{s['ord']:02d}-{rid[-6:].lower()}.png", references=sent)
        ref_info = {"references": refs, "references_dropped": dropped}
        try:
            res = ad.request(req)
        except MbError as e:
            repo.update(conn, "plate_request", rid, {"state": "failed"}, actor)
            failed.append({"shot": s["ord"], "error": e.message, **ref_info})
            continue
        if isinstance(res, Pending):
            repo.update(conn, "shot", s["id"], {"state": "plate_requested", "updated_at": repo.now()}, actor)
            pending.append({"shot": s["ord"], "request": rid, "prompt": s["plate_prompt"], "negative": negative,
                            "reference_image": refs[0]["path"] if refs else None, **ref_info})
            continue
        a = assets.store_plate(conn, project, s, res.path, row["name"], actor, res.cost_usd)
        repo.update(conn, "plate_request", rid, {"state": "done", "result_asset_id": a["id"]}, actor)
        spent += res.cost_usd
        done.append({"shot": s["ord"], "path": a["path"], **ref_info})
    return {"adapter": row["name"], "kind": row["kind"], "done": done, "pending": pending, "failed": failed,
            "spent_usd": round(spent, 4), "est_cost_usd": est, "size": f"{w}x{h}",
            "reference_capacity": "unlimited" if capacity is None else capacity, "reference_strategy": strategy}


def pending_requests(conn: sqlite3.Connection, project_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT pr.id, pr.prompt, pr.reference_image, pr.refs, pr.refs_dropped, s.ord FROM plate_request pr "
        "JOIN shot s ON s.id = pr.shot_id WHERE s.project_id = ? AND pr.state IN ('pending', 'approved_cost') "
        "ORDER BY s.ord, pr.created_at", (project_id,)).fetchall()
    return [{"request": r["id"], "shot": r["ord"], "prompt": r["prompt"], "reference_image": r["reference_image"],
             "references": json.loads(r["refs"] or "[]"), "references_dropped": json.loads(r["refs_dropped"] or "[]")}
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
