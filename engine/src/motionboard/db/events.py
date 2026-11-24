"""Change events. Every write records one so the Studio can stream changes."""

import sqlite3
from typing import Literal

Actor = Literal["chat", "studio", "worker"]
Kind = Literal["insert", "update", "delete"]


def emit(conn: sqlite3.Connection, entity: str, entity_id: str, kind: Kind, actor: Actor) -> int:
    cur = conn.execute(
        "INSERT INTO change_event(at, entity, entity_id, kind, actor) "
        "VALUES (strftime('%Y-%m-%dT%H:%M:%fZ','now'), ?, ?, ?, ?)",
        (entity, entity_id, kind, actor),
    )
    return cur.lastrowid


def since(conn: sqlite3.Connection, seq: int, limit: int = 500) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM change_event WHERE seq > ? ORDER BY seq LIMIT ?", (seq, limit)
    ).fetchall()
