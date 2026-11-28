"""Reading art direction versions. Writes go through direction.service."""

import json
import sqlite3

OPEN = ("draft", "in_review")


def _row(conn: sqlite3.Connection, sql: str, args: tuple) -> dict | None:
    r = conn.execute(sql, args).fetchone()
    return dict(r) if r else None


def approved(conn: sqlite3.Connection, project_id: str) -> dict | None:
    return _row(conn, "SELECT * FROM art_direction WHERE project_id = ? AND status = 'approved'", (project_id,))


def open_version(conn: sqlite3.Connection, project_id: str) -> dict | None:
    return _row(conn, "SELECT * FROM art_direction WHERE project_id = ? AND status IN ('draft', 'in_review')",
                (project_id,))


def latest(conn: sqlite3.Connection, project_id: str) -> dict | None:
    return _row(conn, "SELECT * FROM art_direction WHERE project_id = ? ORDER BY version DESC LIMIT 1", (project_id,))


def by_version(conn: sqlite3.Connection, project_id: str, version: int) -> dict | None:
    return _row(conn, "SELECT * FROM art_direction WHERE project_id = ? AND version = ?", (project_id, version))


def versions(conn: sqlite3.Connection, project_id: str) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM art_direction WHERE project_id = ? ORDER BY version",
                                          (project_id,))]


def body(row: dict | None) -> dict | None:
    return json.loads(row["body"] or "{}") if row else None


def approved_body(conn: sqlite3.Connection, project_id: str) -> dict | None:
    """The direction prompts follow. Drafts never reach prompts."""
    return body(approved(conn, project_id))


def gate_problem(conn: sqlite3.Connection, project_id: str) -> str | None:
    """A full-profile Bible must be approved before plates. Compact or no Bible never blocks."""
    last = latest(conn, project_id)
    if last and last["profile"] == "full" and not approved(conn, project_id):
        return "approve the art direction first (full Bible; mb art approve after the creator says yes)"
    return None
