"""SQLite connection and migrations. The engine is the only owner of the schema."""

import sqlite3
from importlib import resources
from pathlib import Path

from motionboard import config

MIGRATIONS_PKG = "motionboard.db.migrations"


def connect(path: Path | None = None) -> sqlite3.Connection:
    path = Path(path or config.db_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=5.0, isolation_level=None)  # autocommit; explicit transactions
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def _migration_files() -> list[tuple[int, str, str]]:
    files = []
    for entry in resources.files(MIGRATIONS_PKG).iterdir():
        name = entry.name
        if name.endswith(".sql") and name[:4].isdigit():
            files.append((int(name[:4]), name, entry.read_text()))
    return sorted(files)


def latest_version() -> int:
    files = _migration_files()
    return files[-1][0] if files else 0


def current_version(conn: sqlite3.Connection) -> int:
    conn.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL, applied_at TEXT NOT NULL)")
    row = conn.execute("SELECT max(version) AS v FROM schema_version").fetchone()
    return row["v"] or 0


def migrate(conn: sqlite3.Connection) -> list[str]:
    """Apply pending migrations in order. Returns names applied."""
    applied = []
    have = current_version(conn)
    for version, name, sql in _migration_files():
        if version <= have:
            continue
        conn.execute("BEGIN IMMEDIATE")
        try:
            for statement in _split(sql):
                conn.execute(statement)
            conn.execute(
                "INSERT INTO schema_version(version, applied_at) VALUES (?, strftime('%Y-%m-%dT%H:%M:%fZ','now'))",
                (version,),
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        applied.append(name)
    return applied


def _split(sql: str) -> list[str]:
    lines = [ln for ln in sql.splitlines() if not ln.strip().startswith("--")]
    return [s.strip() for s in "\n".join(lines).split(";") if s.strip()]


def open_db(path: Path | None = None) -> sqlite3.Connection:
    """Connect and bring the schema up to date."""
    conn = connect(path)
    migrate(conn)
    return conn
