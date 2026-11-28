"""Art Direction Bible versions: draft, check, submit, reject, approve, history, Markdown view (FR-001 to FR-008).

One approved version and at most one open version (draft or in review) per project. Approved rows are never
edited; a revision is a new version based on the approved one. Approval is the creator's act and recomposes
prompts; it never regenerates or re-states assets, it reports what they are (research R4, R5).
"""

import json
import sqlite3
from pathlib import Path

from motionboard.db import repo
from motionboard.db.events import Actor
from motionboard.direction import bible, impact, store
from motionboard.report import MbError

MD_NAME = "art-direction.md"


def _via(actor: Actor) -> str:
    return "studio" if actor == "studio" else "chat"


def _cast(conn: sqlite3.Connection, project_id: str) -> dict[str, list[int]]:
    """Project characters with the shots they appear in (for Bible cast warnings)."""
    out: dict[str, list[int]] = {r["name"]: [] for r in conn.execute(
        "SELECT name FROM character WHERE project_id = ?", (project_id,))}
    for r in conn.execute("SELECT c.name, s.ord FROM shot_character sc JOIN character c ON c.id = sc.character_id "
                          "JOIN shot s ON s.id = sc.shot_id WHERE s.project_id = ? ORDER BY s.ord", (project_id,)):
        out.setdefault(r["name"], []).append(r["ord"])
    return out


def check_body(conn: sqlite3.Connection, project_id: str, body: dict, profile: str) -> tuple[list[str], list[str]]:
    errors = bible.structure_errors(body) + bible.profile_errors(body, profile)
    warnings = bible.vague_warnings(body) + bible.cast_warnings(body, _cast(conn, project_id))
    for i, c in enumerate(body.get("characters") or []):
        if isinstance(c, dict) and c.get("motion"):
            from motionboard.direction.grammar import validate

            errors += validate(c["motion"], f"characters[{i}]")
    return errors, warnings


def _summary(row: dict) -> dict:
    return {"version": row["version"], "status": row["status"], "profile": row["profile"], "note": row["note"],
            "created_at": row["created_at"], "approved_at": row["approved_at"], "approved_via": row["approved_via"]}


def write_markdown(conn: sqlite3.Connection, project: dict) -> Path | None:
    """The generated view in the project folder: the approved version, then any pending revision."""
    folder = Path(project["folder"])
    if not folder.exists():
        return None
    path = folder / MD_NAME
    rows = [r for r in (store.approved(conn, project["id"]), store.open_version(conn, project["id"])) if r]
    if not rows:
        if path.exists():
            path.unlink()
        return None
    parts = []
    for r in rows:
        if r["status"] != "approved":
            parts.append("\n---\n\n# Pending revision\n")
        parts.append(bible.render_markdown(store.body(r) or {}, {
            "title": project["title"], **_summary(r)}))
    path.write_text("\n".join(parts))
    return path


def save_draft(conn: sqlite3.Connection, project: dict, body: dict, profile: str | None, note: str,
               actor: Actor) -> dict:
    pid = project["id"]
    open_ = store.open_version(conn, pid)
    approved = store.approved(conn, pid)
    profile = profile or (open_ or approved or {}).get("profile") or "compact"
    errors = bible.structure_errors(body)
    if errors:
        raise MbError("INVALID_INPUT", "the art direction file has structure errors; nothing was saved",
                      hint="; ".join(errors[:8]), data={"errors": errors})
    bible.profile_errors(body, profile)  # validates the profile name
    preview = impact.affected(conn, pid, store.body(approved), body)
    ts = repo.now()
    with repo.tx(conn):
        if open_:
            repo.update(conn, "art_direction", open_["id"], {
                "body": body, "profile": profile, "note": note or open_["note"], "status": "draft",
                "impact": preview, "updated_at": ts}, actor)
            rid = open_["id"]
        else:
            last = store.latest(conn, pid)
            rid = repo.insert(conn, "art_direction", {
                "project_id": pid, "version": (last["version"] + 1) if last else 1, "profile": profile,
                "status": "draft", "body": body, "note": note, "based_on": approved["id"] if approved else None,
                "impact": preview, "created_at": ts, "updated_at": ts, "created_via": _via(actor)}, actor)
        repo.update(conn, "project", pid, {"updated_at": ts}, actor)
    write_markdown(conn, project)
    row = repo.get(conn, "art_direction", rid)
    errs, warns = check_body(conn, pid, body, profile)
    return {**_summary(row), "errors": errs, "warnings": warns, "impact": preview}


def _open_or_fail(conn: sqlite3.Connection, pid: str) -> dict:
    row = store.open_version(conn, pid)
    if not row:
        raise MbError("NOT_FOUND", "no art direction draft or revision is open", hint="mb art draft --file bible.json")
    return row


def check(conn: sqlite3.Connection, project: dict) -> dict:
    row = store.open_version(conn, project["id"]) or store.approved(conn, project["id"])
    if not row:
        raise MbError("NOT_FOUND", "this project has no art direction yet", hint="mb art draft --file bible.json")
    errors, warnings = check_body(conn, project["id"], store.body(row) or {}, row["profile"])
    return {**_summary(row), "errors": errors, "warnings": warnings}


def submit(conn: sqlite3.Connection, project: dict, actor: Actor) -> dict:
    row = _open_or_fail(conn, project["id"])
    errors, warnings = check_body(conn, project["id"], store.body(row) or {}, row["profile"])
    if errors:
        raise MbError("INVALID_INPUT", f"version {row['version']} is not complete enough to review",
                      hint="; ".join(errors[:8]), data={"errors": errors, "warnings": warnings})
    repo.update(conn, "art_direction", row["id"], {"status": "in_review", "updated_at": repo.now()}, actor)
    write_markdown(conn, project)
    return {**_summary(repo.get(conn, "art_direction", row["id"])), "warnings": warnings}


def reject(conn: sqlite3.Connection, project: dict, note: str, actor: Actor) -> dict:
    row = _open_or_fail(conn, project["id"])
    if not note.strip():
        raise MbError("INVALID_INPUT", "say what to change, so the designer can revise it")
    repo.update(conn, "art_direction", row["id"], {"status": "draft", "note": note.strip(),
                                                   "updated_at": repo.now()}, actor)
    write_markdown(conn, project)
    return _summary(repo.get(conn, "art_direction", row["id"]))


def approve(conn: sqlite3.Connection, project: dict, via: str, look, actor: Actor) -> dict:
    """The creator approves the open version. Prompts follow it from now on; affected assets are reported."""
    from motionboard.storyboard import compose

    pid = project["id"]
    row = _open_or_fail(conn, pid)
    body = store.body(row) or {}
    errors, warnings = check_body(conn, pid, body, row["profile"])
    if errors:
        raise MbError("GATE_NOT_APPROVED", f"art direction version {row['version']} cannot be approved yet",
                      hint="; ".join(errors[:8]), data={"errors": errors, "warnings": warnings})
    previous = store.approved(conn, pid)
    result = impact.affected(conn, pid, store.body(previous), body)  # against nothing: plates made before any Bible
    ts = repo.now()
    with repo.tx(conn):
        if previous:
            repo.update(conn, "art_direction", previous["id"], {"status": "superseded", "updated_at": ts}, actor)
        repo.update(conn, "art_direction", row["id"], {
            "status": "approved", "approved_at": ts, "approved_via": "studio" if via == "studio" else "chat",
            "impact": result, "updated_at": ts}, actor)
        recomposed = compose.recompose(conn, project, None, look, actor, mark_redo=False)
        repo.update(conn, "project", pid, {"updated_at": ts}, actor)
    write_markdown(conn, project)
    return {**_summary(repo.get(conn, "art_direction", row["id"])),
            "superseded": previous["version"] if previous else None, "impact": result, "recomposed": recomposed,
            "warnings": warnings}


def show(conn: sqlite3.Connection, project: dict, version: int | None, pending: bool, markdown: bool) -> dict:
    pid = project["id"]
    if version:
        row = store.by_version(conn, pid, version)
    elif pending:
        row = store.open_version(conn, pid)
    else:
        row = store.approved(conn, pid) or store.open_version(conn, pid)
    if not row:
        raise MbError("NOT_FOUND", "no such art direction version", hint="mb art history")
    open_ = store.open_version(conn, pid)
    out = {**_summary(row), "pending": _summary(open_) if open_ and open_["id"] != row["id"] else None,
           "impact": json.loads(row["impact"] or "{}")}
    body = store.body(row) or {}
    if markdown:
        out["markdown"] = bible.render_markdown(body, {"title": project["title"], **_summary(row)})
    else:
        out["body"] = body
    return out


def history(conn: sqlite3.Connection, project_id: str) -> list[dict]:
    return [_summary(r) for r in store.versions(conn, project_id)]


def impact_now(conn: sqlite3.Connection, project_id: str) -> dict:
    """The open version against the approved one (recomputed now), else what the last approval reported."""
    open_, approved = store.open_version(conn, project_id), store.approved(conn, project_id)
    if open_:
        return {"version": open_["version"], "against": approved["version"] if approved else None,
                **impact.affected(conn, project_id, store.body(approved), store.body(open_) or {})}
    if approved:
        return {"version": approved["version"], "against": None, **json.loads(approved["impact"] or "{}")}
    return {"version": None, "against": None, "changed": [], "shots": []}


def motifs(conn: sqlite3.Connection, project_id: str) -> list[dict]:
    """Each motif with its state shot by shot, from the shots' creative context, in Bible order then any others."""
    body = store.approved_body(conn, project_id) or store.body(store.open_version(conn, project_id)) or {}
    rows = [dict(r) for r in conn.execute("SELECT ord, creative FROM shot WHERE project_id = ? ORDER BY ord",
                                          (project_id,))]
    names: list[str] = [str(m.get("name")) for m in body.get("motifs") or [] if m.get("name")]
    per: dict[str, list[dict]] = {}
    for r in rows:
        for m in json.loads(r["creative"] or "{}").get("motifs") or []:
            key = next((n for n in names if n.lower() == m["name"].lower()), m["name"])
            if key not in names:
                names.append(key)
            per.setdefault(key, []).append({"shot": r["ord"], "state": m.get("state", "")})
    out = []
    for n in names:
        entry = bible.motif_entry(body, n) or {}
        out.append({"name": n, "meaning": entry.get("meaning", ""), "payoff": entry.get("payoff", ""),
                    "shots": per.get(n, [])})
    return out
