"""Repository: the only place that writes rows. Every write emits a change event
and refuses values that look like secrets (constitution, FR-013)."""

import json
import os
import re
import sqlite3
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

from motionboard.db.events import Actor, emit

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),           # OpenAI / Anthropic style
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),        # GitHub tokens
    re.compile(r"hf_[A-Za-z0-9]{30,}"),               # Hugging Face
    re.compile(r"AKIA[0-9A-Z]{16}"),                  # AWS access key
    re.compile(r"xox[abpr]-[A-Za-z0-9\-]{10,}"),      # Slack
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)\b(api[_-]?key|secret|token|password)\b\s*[:=]\s*['\"]?[A-Za-z0-9_\-\.]{16,}"),
]


class SecretValueError(ValueError):
    """A value looked like a credential and was refused."""


def new_id() -> str:
    """ULID: 48 bit ms time + 80 random bits, Crockford base32, sortable."""
    value = (int(time.time() * 1000) << 80) | int.from_bytes(os.urandom(10), "big")
    return "".join(_CROCKFORD[(value >> (5 * i)) & 31] for i in reversed(range(26)))


def now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def looks_secret(value: Any) -> bool:
    if isinstance(value, (dict, list)):
        value = json.dumps(value)
    if not isinstance(value, str):
        return False
    return any(p.search(value) for p in SECRET_PATTERNS)


def _clean(row: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for k, v in row.items():
        if looks_secret(v):
            raise SecretValueError(f"refused to store a credential-like value in field '{k}'")
        if isinstance(v, (dict, list)):
            v = json.dumps(v)
        elif isinstance(v, bool):
            v = int(v)
        out[k] = v
    return out


def _q(name: str) -> str:
    if not re.fullmatch(r"[a-z_]+", name):
        raise ValueError(f"bad identifier {name!r}")
    return f'"{name}"'


@contextmanager
def tx(conn: sqlite3.Connection):
    """Write transaction. Nested use joins the outer transaction."""
    if conn.in_transaction:
        yield conn
        return
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def insert(conn: sqlite3.Connection, table: str, row: dict[str, Any], actor: Actor, key: str = "id") -> str:
    row = dict(row)
    if key == "id":
        row.setdefault("id", new_id())
    row = _clean(row)
    cols = ", ".join(_q(c) for c in row)
    marks = ", ".join("?" for _ in row)
    with tx(conn):
        conn.execute(f"INSERT INTO {_q(table)} ({cols}) VALUES ({marks})", tuple(row.values()))
        emit(conn, table, str(row[key]), "insert", actor)
    return str(row[key])


def update(
    conn: sqlite3.Connection, table: str, row_id: str, fields: dict[str, Any], actor: Actor, key: str = "id"
) -> int:
    if not fields:
        return 0
    fields = _clean(fields)
    sets = ", ".join(f"{_q(c)} = ?" for c in fields)
    with tx(conn):
        cur = conn.execute(
            f"UPDATE {_q(table)} SET {sets} WHERE {_q(key)} = ?", (*fields.values(), row_id)
        )
        if cur.rowcount:
            emit(conn, table, row_id, "update", actor)
    return cur.rowcount


def delete(conn: sqlite3.Connection, table: str, row_id: str, actor: Actor, key: str = "id") -> int:
    with tx(conn):
        cur = conn.execute(f"DELETE FROM {_q(table)} WHERE {_q(key)} = ?", (row_id,))
        if cur.rowcount:
            emit(conn, table, row_id, "delete", actor)
    return cur.rowcount


def get(conn: sqlite3.Connection, table: str, row_id: str, key: str = "id") -> dict | None:
    row = conn.execute(f"SELECT * FROM {_q(table)} WHERE {_q(key)} = ?", (row_id,)).fetchone()
    return dict(row) if row else None


def find(conn: sqlite3.Connection, table: str, order: str | None = None, **where: Any) -> list[dict]:
    sql = f"SELECT * FROM {_q(table)}"
    if where:
        sql += " WHERE " + " AND ".join(f"{_q(k)} = ?" for k in where)
    if order:
        sql += f" ORDER BY {_q(order)}"
    return [dict(r) for r in conn.execute(sql, tuple(where.values())).fetchall()]


# --- workspace settings -------------------------------------------------------

def get_setting(conn: sqlite3.Connection, key: str, default: Any = None) -> Any:
    row = conn.execute("SELECT value FROM workspace_setting WHERE key = ?", (key,)).fetchone()
    return json.loads(row["value"]) if row else default


def set_setting(conn: sqlite3.Connection, key: str, value: Any, actor: Actor) -> None:
    if looks_secret(value):
        raise SecretValueError(f"refused to store a credential-like value for setting '{key}'")
    with tx(conn):
        conn.execute(
            "INSERT INTO workspace_setting(key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, json.dumps(value)),
        )
        emit(conn, "workspace_setting", key, "update", actor)
