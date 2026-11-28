"""Structured creative reviews (FR-020, FR-021).

A finding has four parts: what is seen, what the audience will feel, why it matters for the story, and a specific
change. Reviews never block approvals; open ones are listed as not verified when a gate is approved.
"""

import json
import sqlite3
from pathlib import Path

import yaml

from motionboard.db import repo
from motionboard.db.events import Actor
from motionboard.direction import store
from motionboard.report import MbError

STAGES = ("concept", "art_direction", "plate", "rough_cut")
ROLES = ("director", "production_designer", "cinematographer", "editor", "emotion_editor", "creator")
VERDICTS = ("ready", "revise", "blocked")
PARTS = ("observation", "audience_impact", "implication", "recommendation")
# Which critiques an approval should mention: the stage being approved and the reviews that feed it.
FOR_GATE = {"storyboard": ("concept",), "plates": ("plate",), "clips": ("plate", "rough_cut"),
            "final": ("rough_cut",), "art_direction": ("art_direction",)}


def _load(path: Path) -> dict:
    try:
        text = Path(path).expanduser().read_text()
        data = yaml.safe_load(text) if Path(path).suffix.lower() in (".yaml", ".yml") else json.loads(text)
    except (OSError, json.JSONDecodeError, yaml.YAMLError) as e:
        raise MbError("INVALID_INPUT", f"cannot read critique file: {e}") from e
    if not isinstance(data, dict):
        raise MbError("INVALID_INPUT", "a critique file is one object with summary, findings, checked, not_checked")
    return data


def _clean_findings(findings, shots_in_project: set[int]) -> list[dict]:
    if not isinstance(findings, list):
        raise MbError("INVALID_INPUT", "findings must be a list")
    out = []
    for i, f in enumerate(findings, 1):
        if not isinstance(f, dict):
            raise MbError("INVALID_INPUT", f"finding {i} must be an object")
        missing = [p for p in PARTS if not str(f.get(p, "")).strip()]
        if missing:
            raise MbError("INVALID_INPUT", f"finding {i} is missing {', '.join(missing)}",
                          hint="a finding says what is seen, what the audience feels, why it matters, what to change")
        shots = [int(s) for s in f.get("shots") or []]
        unknown = sorted(set(shots) - shots_in_project)
        if unknown:
            raise MbError("INVALID_INPUT", f"finding {i} names shots that do not exist: {unknown}")
        out.append({**{p: str(f[p]).strip() for p in PARTS}, "shots": shots,
                    **({"motif": str(f["motif"]).strip()} if f.get("motif") else {})})
    return out


def add(conn: sqlite3.Connection, project: dict, stage: str, role: str, verdict: str, path: Path,
        actor: Actor) -> dict:
    for value, allowed, what in ((stage, STAGES, "stage"), (role, ROLES, "role"), (verdict, VERDICTS, "verdict")):
        if value not in allowed:
            raise MbError("INVALID_INPUT", f"{what} must be one of {', '.join(allowed)}")
    data = _load(path)
    shots = {r[0] for r in conn.execute("SELECT ord FROM shot WHERE project_id = ?", (project["id"],))}
    findings = _clean_findings(data.get("findings") or [], shots)
    if verdict != "ready" and not findings:
        raise MbError("INVALID_INPUT", f"a {verdict} review needs at least one finding")
    ad = None
    if stage == "art_direction":
        ad = store.open_version(conn, project["id"]) or store.approved(conn, project["id"])
    cid = repo.insert(conn, "critique", {
        "project_id": project["id"], "stage": stage, "role": role, "verdict": verdict,
        "summary": str(data.get("summary", "")).strip(), "findings": findings,
        "checked": [str(x) for x in data.get("checked") or []],
        "not_checked": [str(x) for x in data.get("not_checked") or []],
        "art_direction_id": ad["id"] if ad else None, "created_at": repo.now()}, actor)
    return _out(repo.get(conn, "critique", cid))


def _out(row: dict) -> dict:
    return {**{k: row[k] for k in ("id", "stage", "role", "verdict", "summary", "created_at", "resolved_at")},
            "findings": json.loads(row["findings"]), "checked": json.loads(row["checked"]),
            "not_checked": json.loads(row["not_checked"])}


def listing(conn: sqlite3.Connection, project_id: str, stage: str | None = None, shot: int | None = None,
            open_only: bool = False) -> list[dict]:
    rows = [_out(dict(r)) for r in conn.execute(
        "SELECT * FROM critique WHERE project_id = ? ORDER BY created_at DESC", (project_id,))]
    if stage:
        rows = [r for r in rows if r["stage"] == stage]
    if open_only:
        rows = [r for r in rows if not r["resolved_at"]]
    if shot is not None:
        rows = [{**r, "findings": [f for f in r["findings"] if shot in f["shots"]]} for r in rows]
        rows = [r for r in rows if r["findings"]]
    return rows


def resolve(conn: sqlite3.Connection, project_id: str, critique_id: str, actor: Actor) -> dict:
    row = repo.get(conn, "critique", critique_id)
    if not row or row["project_id"] != project_id:
        raise MbError("NOT_FOUND", f"no critique '{critique_id}' in this project")
    repo.update(conn, "critique", critique_id, {"resolved_at": repo.now()}, actor)
    return _out(repo.get(conn, "critique", critique_id))


def open_for_gate(conn: sqlite3.Connection, project_id: str, gate: str) -> list[str]:
    """One line per open revise or blocked critique that feeds this gate, for the approval's not_verified list."""
    stages = FOR_GATE.get(gate, ())
    out = []
    for r in listing(conn, project_id, open_only=True):
        if r["stage"] in stages and r["verdict"] != "ready":
            shots = sorted({s for f in r["findings"] for s in f["shots"]})
            out.append(f"open {r['verdict']} review by the {r['role'].replace('_', ' ')} ({r['stage']})"
                       + (f" on shots {', '.join(map(str, shots))}" if shots else "") + f": {r['summary'] or r['id']}")
    return out
