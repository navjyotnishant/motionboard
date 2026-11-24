"""Guard presets. Values come from the Almost Yours runs on a 36 GB M3 Max (research R3).

swap_ceiling_mb is the swap growth allowed while the job runs, not total swap:
macOS often carries several GB of swap from other apps before a job starts.
"""

import sqlite3
from dataclasses import asdict, dataclass

from motionboard.db import repo
from motionboard.db.events import Actor
from motionboard.report import MbError

ACTIVE_KEY = "active_guard_profile"
DEFAULT_PRESET = "balanced"


@dataclass(frozen=True)
class GuardProfile:
    name: str
    start_free_pct: int
    kill_free_pct: int
    swap_ceiling_mb: int
    poll_seconds: float = 2.0
    builtin: bool = False

    def describe(self) -> str:
        return (
            f"guard '{self.name}': start at free >= {self.start_free_pct}%, stop at free < "
            f"{self.kill_free_pct}% or swap growth > {self.swap_ceiling_mb} MB, poll {self.poll_seconds}s"
        )


BUILTIN = [
    GuardProfile("safe", 45, 12, 2048, 2.0, True),
    GuardProfile("balanced", 35, 8, 4096, 2.0, True),
    GuardProfile("max", 25, 6, 8192, 2.0, True),
]


def validate(p: GuardProfile) -> None:
    if not (1 <= p.kill_free_pct <= 50):
        raise MbError("INVALID_INPUT", "kill floor must be between 1 and 50 percent")
    if not (p.kill_free_pct < p.start_free_pct <= 99):
        raise MbError("INVALID_INPUT", "start floor must be above the kill floor and at most 99 percent")
    if p.swap_ceiling_mb < 0:
        raise MbError("INVALID_INPUT", "swap ceiling must be 0 or more")
    if not (0.5 <= p.poll_seconds <= 10):
        raise MbError("INVALID_INPUT", "poll interval must be between 0.5 and 10 seconds")


def seed(conn: sqlite3.Connection) -> None:
    for p in BUILTIN:
        if not repo.find(conn, "guard_profile", name=p.name):
            repo.insert(conn, "guard_profile", asdict(p), actor="chat")
    if repo.get_setting(conn, ACTIVE_KEY) is None:
        repo.set_setting(conn, ACTIVE_KEY, DEFAULT_PRESET, actor="chat")


def _from_row(row: dict) -> GuardProfile:
    return GuardProfile(
        row["name"], row["start_free_pct"], row["kill_free_pct"], row["swap_ceiling_mb"],
        row["poll_seconds"], bool(row["builtin"]),
    )


def list_profiles(conn: sqlite3.Connection) -> list[GuardProfile]:
    seed(conn)
    return [_from_row(r) for r in repo.find(conn, "guard_profile", order="start_free_pct")]


def get(conn: sqlite3.Connection, name: str) -> GuardProfile:
    seed(conn)
    rows = repo.find(conn, "guard_profile", name=name)
    if not rows:
        raise MbError("NOT_FOUND", f"no guard preset named '{name}'", hint="mb guard --list")
    return _from_row(rows[0])


def active(conn: sqlite3.Connection) -> GuardProfile:
    seed(conn)
    return get(conn, repo.get_setting(conn, ACTIVE_KEY, DEFAULT_PRESET))


def set_active(conn: sqlite3.Connection, name: str, actor: Actor) -> GuardProfile:
    p = get(conn, name)
    repo.set_setting(conn, ACTIVE_KEY, name, actor)
    return p


def create(conn: sqlite3.Connection, p: GuardProfile, actor: Actor) -> GuardProfile:
    seed(conn)
    validate(p)
    if repo.find(conn, "guard_profile", name=p.name):
        raise MbError("INVALID_INPUT", f"a preset named '{p.name}' already exists")
    repo.insert(conn, "guard_profile", {**asdict(p), "builtin": False}, actor)
    return p
