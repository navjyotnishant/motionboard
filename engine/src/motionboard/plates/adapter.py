"""Plate adapters (contracts/plate-adapter.md). Any image source plugs in: manual files,
a local command, an HTTP API, or a handoff that Claude fulfils with an MCP tool."""

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from motionboard.db import repo
from motionboard.db.events import Actor
from motionboard.report import MbError

KINDS = ("manual", "command", "http", "handoff")


@dataclass
class PlateRequest:
    request_id: str
    shot_id: str
    shot_ord: int
    prompt: str
    negative: str
    width: int
    height: int
    out: Path
    reference_image: Path | None = None
    seed: int = 42


@dataclass
class PlateResult:
    path: Path
    cost_usd: float = 0.0


class Pending:
    """The request stays pending until fulfilled (handoff, or manual file not there yet)."""


class PlateAdapter(Protocol):
    name: str
    kind: str
    cost_per_image_usd: float

    def request(self, req: PlateRequest) -> PlateResult | Pending: ...


def build(row: dict, project: dict) -> PlateAdapter:
    cfg = json.loads(row["config"] or "{}")
    kind = row["kind"]
    if kind == "manual":
        from motionboard.plates.manual import ManualAdapter
        return ManualAdapter(row["name"], cfg, project)
    if kind == "command":
        from motionboard.plates.command import CommandAdapter
        return CommandAdapter(row["name"], cfg, row["cost_per_image_usd"])
    if kind == "http":
        from motionboard.plates.http_api import HttpAdapter
        return HttpAdapter(row["name"], cfg, row["cost_per_image_usd"])
    if kind == "handoff":
        from motionboard.plates.handoff import HandoffAdapter
        return HandoffAdapter(row["name"], cfg, row["cost_per_image_usd"])
    raise MbError("INVALID_INPUT", f"unknown adapter kind '{kind}'")


def get_row(conn: sqlite3.Connection, name: str) -> dict:
    rows = repo.find(conn, "plate_adapter", name=name)
    if not rows:
        raise MbError("NOT_FOUND", f"no plate adapter named '{name}'", hint="mb adapter --list")
    return rows[0]


def add(conn: sqlite3.Connection, name: str, kind: str, config: dict, cost: float, actor: Actor) -> dict:
    if kind not in KINDS:
        raise MbError("INVALID_INPUT", f"kind must be one of {', '.join(KINDS)}")
    if kind == "command" and not config.get("cmd"):
        raise MbError("INVALID_INPUT", "command adapters need a cmd list with {prompt} and {out}")
    if kind == "http" and not config.get("url"):
        raise MbError("INVALID_INPUT", "http adapters need a url")
    if cost < 0:
        raise MbError("INVALID_INPUT", "cost cannot be negative")
    if repo.find(conn, "plate_adapter", name=name):
        raise MbError("INVALID_INPUT", f"an adapter named '{name}' already exists")
    rid = repo.insert(conn, "plate_adapter", {"name": name, "kind": kind, "config": config,
                                              "cost_per_image_usd": cost, "enabled": True}, actor)
    return repo.get(conn, "plate_adapter", rid)


def ensure_default_manual(conn: sqlite3.Connection) -> None:
    if not repo.find(conn, "plate_adapter", name="manual"):
        repo.insert(conn, "plate_adapter", {"name": "manual", "kind": "manual",
                                            "config": {"watch_folder": "plates/inbox"},
                                            "cost_per_image_usd": 0, "enabled": True}, "chat")
