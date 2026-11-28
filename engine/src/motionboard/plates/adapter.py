"""Plate adapters (contracts/plate-adapter.md). Any image source plugs in: manual files,
a local command, an HTTP API, or a handoff that Claude fulfils with an MCP tool."""

import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from motionboard.db import repo
from motionboard.db.events import Actor
from motionboard.report import MbError

KINDS = ("manual", "command", "http", "handoff")
STRATEGIES = ("strict", "primary", "first", "none")


@dataclass
class Reference:
    """One character reference image sent with a plate request (feature 003)."""
    character: str
    path: Path
    purpose: str = "other"
    primary: bool = False
    description: str = ""

    def as_dict(self) -> dict:
        return {"character": self.character, "path": str(self.path), "purpose": self.purpose,
                "primary": self.primary, "description": self.description}


# What an adapter can be told about each reference, so a provider can tell HER's face from HIM's silhouette.
REF_FIELDS = ("index", "character", "purpose", "primary", "path", "description")


def reference_meta(refs: list[Reference]) -> list[dict]:
    """One entry per reference sent, in the order sent (`index` counts from 0)."""
    return [{"index": i, "character": r.character, "purpose": r.purpose, "primary": bool(r.primary),
             "path": str(r.path), "description": r.description} for i, r in enumerate(refs)]


def reference_manifest(req: "PlateRequest") -> dict:
    return {"request": req.request_id, "shot": req.shot_ord, "references": reference_meta(req.references)}


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
    references: list[Reference] = field(default_factory=list)

    def __post_init__(self):
        if self.references and self.reference_image is None:
            self.reference_image = self.references[0].path
        elif self.reference_image is not None and not self.references:
            self.references = [Reference("", Path(self.reference_image), "other", True)]


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

    def reference_capacity(self) -> int | None:
        """How many reference images this adapter can use. None means no limit."""
        ...


def select_references(refs: list[Reference], capacity: int | None, strategy: str,
                      adapter_name: str) -> tuple[list[Reference], list[dict]]:
    """Choose what to send. Never silently drops: everything not sent comes back with a reason (research R8)."""
    if strategy not in STRATEGIES:
        raise MbError("INVALID_INPUT", f"reference strategy must be one of {', '.join(STRATEGIES)}")
    dropped = [{**r.as_dict(), "reason": "file missing"} for r in refs if not Path(r.path).exists()]
    usable = [r for r in refs if Path(r.path).exists()]
    if strategy == "none":
        return [], dropped + [{**r.as_dict(), "reason": "reference strategy none"} for r in usable]
    if strategy == "primary":
        keep = [r for r in usable if r.primary]
        dropped += [{**r.as_dict(), "reason": "reference strategy primary"} for r in usable if not r.primary]
        usable = keep
    if capacity is None or len(usable) <= capacity:
        return usable, dropped
    if strategy == "first":
        return usable[:capacity], dropped + [{**r.as_dict(), "reason": f"adapter takes {capacity}"}
                                             for r in usable[capacity:]]
    who = ", ".join(sorted({r.character or "?" for r in usable}))
    raise MbError("INVALID_INPUT",
                  f"this shot has {len(usable)} reference images ({who}) but adapter '{adapter_name}' can use "
                  f"{capacity}", hint="give the adapter more reference slots ({refs} for a command, refs_field for "
                  "an API), or choose what to drop: --reference-strategy primary, first or none (or set "
                  "reference_strategy in the adapter config)",
                  data={"references": [r.as_dict() for r in usable], "capacity": capacity})


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
    _check_reference_config(kind, config)
    if cost < 0:
        raise MbError("INVALID_INPUT", "cost cannot be negative")
    if repo.find(conn, "plate_adapter", name=name):
        raise MbError("INVALID_INPUT", f"an adapter named '{name}' already exists")
    rid = repo.insert(conn, "plate_adapter", {"name": name, "kind": kind, "config": config,
                                              "cost_per_image_usd": cost, "enabled": True}, actor)
    return repo.get(conn, "plate_adapter", rid)


def _check_reference_config(kind: str, config: dict) -> None:
    """Reference metadata settings (contracts/plate-adapter-references.md) are checked when the adapter is added."""
    if "refs_format" in config:
        if kind != "command" or "{refs}" not in config.get("cmd", []):
            raise MbError("INVALID_INPUT", "refs_format shapes each {refs} argument of a command adapter",
                          hint='add "{refs}" as its own element of cmd')
        try:
            str(config["refs_format"]).format(**dict.fromkeys(REF_FIELDS, ""))
        except (KeyError, IndexError, ValueError) as e:
            raise MbError("INVALID_INPUT", f"refs_format can use {', '.join('{' + f + '}' for f in REF_FIELDS)}",
                          hint=f"not understood: {e}") from e
    if "refs_meta" in config:
        meta = config["refs_meta"]
        sources = ("image", *REF_FIELDS)
        if kind != "http" or not config.get("refs_field"):
            raise MbError("INVALID_INPUT", "refs_meta describes the objects an http adapter puts at refs_field",
                          hint="set refs_field too")
        if not isinstance(meta, dict) or not meta or any(v not in sources for v in meta.values()):
            raise MbError("INVALID_INPUT", "refs_meta maps a field name of the API to one of: " + ", ".join(sources))
    if "refs_manifest_field" in config and kind != "http":
        raise MbError("INVALID_INPUT", "refs_manifest_field belongs to http adapters; a command takes "
                                       "{refs_manifest} or {refs_json}")


def ensure_default_manual(conn: sqlite3.Connection) -> None:
    if not repo.find(conn, "plate_adapter", name="manual"):
        repo.insert(conn, "plate_adapter", {"name": "manual", "kind": "manual",
                                            "config": {"watch_folder": "plates/inbox"},
                                            "cost_per_image_usd": 0, "enabled": True}, "chat")
