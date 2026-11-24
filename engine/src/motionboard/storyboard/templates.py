"""Modes (story structure + animation pack) and looks (visual world). Plain YAML
files in the repo (modes/<slug>/mode.yaml, looks/<slug>.yaml) plus user saved
ones in the template table."""

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from motionboard import config
from motionboard.report import MbError
from motionboard.storyboard.timing import Rhythm


@dataclass
class PatternShot:
    role: str
    visual: str
    action: str
    camera: str
    has_figure: bool = True
    lip_sync: bool = False


@dataclass
class Mode:
    slug: str
    name: str
    summary: str
    animation: str
    rhythm: Rhythm
    pattern: list[PatternShot]
    characters: list[str] = field(default_factory=list)
    lip_sync: str = "never"  # never | chorus | lines
    source: str = "builtin"


@dataclass
class Look:
    slug: str
    name: str
    summary: str
    world: str
    style_line: str
    no_figure_line: str
    negative: str = ""
    realistic: bool = False
    source: str = "builtin"


def modes_dir() -> Path:
    return config.repo_root() / "modes"


def looks_dir() -> Path:
    return config.repo_root() / "looks"


def _mode_from(d: dict, source: str) -> Mode:
    try:
        r = d.get("rhythm", {})
        return Mode(
            slug=d["slug"], name=d["name"], summary=d.get("summary", ""), animation=d.get("animation", d["slug"]),
            rhythm=Rhythm(r.get("unit", "line"), int(r.get("beats_per_shot", 8)),
                          float(r.get("min_shot_s", 2.0)), float(r.get("max_shot_s", 5.0))),
            pattern=[PatternShot(**p) for p in d["pattern"]],
            characters=list(d.get("characters", [])),
            lip_sync=d.get("lip_sync", "never"),
            source=source,
        )
    except (KeyError, TypeError) as e:
        raise MbError("INVALID_INPUT", f"mode '{d.get('slug', '?')}' is invalid: {e}") from e


def _look_from(d: dict, source: str) -> Look:
    try:
        return Look(
            slug=d["slug"], name=d["name"], summary=d.get("summary", ""), world=d["world"],
            style_line=d["style_line"], no_figure_line=d["no_figure_line"], negative=d.get("negative", ""),
            realistic=bool(d.get("realistic", False)), source=source,
        )
    except (KeyError, TypeError) as e:
        raise MbError("INVALID_INPUT", f"look '{d.get('slug', '?')}' is invalid: {e}") from e


def _validate_mode(m: Mode) -> Mode:
    if not m.pattern:
        raise MbError("INVALID_INPUT", f"mode '{m.slug}' needs at least one pattern shot")
    if m.rhythm.unit not in ("line", "beats"):
        raise MbError("INVALID_INPUT", f"mode '{m.slug}': rhythm unit must be line or beats")
    if not (0 < m.rhythm.min_shot_s < m.rhythm.max_shot_s):
        raise MbError("INVALID_INPUT", f"mode '{m.slug}': min_shot_s must be below max_shot_s")
    if m.lip_sync not in ("never", "chorus", "lines"):
        raise MbError("INVALID_INPUT", f"mode '{m.slug}': lip_sync must be never, chorus or lines")
    for p in m.pattern:
        if p.lip_sync and not p.has_figure:
            raise MbError("INVALID_INPUT", f"mode '{m.slug}': lip-sync shot '{p.role}' needs a figure")
    return m


def list_modes(conn: sqlite3.Connection | None = None) -> list[Mode]:
    out = [_validate_mode(_mode_from(yaml.safe_load(f.read_text()), "builtin"))
           for f in sorted(modes_dir().glob("*/mode.yaml"))]
    if conn is not None:
        for row in conn.execute("SELECT body FROM template WHERE source = 'user'"):
            d = yaml.safe_load(row["body"])
            if d.get("kind") == "mode":
                out.append(_validate_mode(_mode_from(d, "user")))
    return out


def list_looks(conn: sqlite3.Connection | None = None) -> list[Look]:
    out = [_look_from(yaml.safe_load(f.read_text()), "builtin") for f in sorted(looks_dir().glob("*.yaml"))]
    if conn is not None:
        for row in conn.execute("SELECT body FROM template WHERE source = 'user'"):
            d = yaml.safe_load(row["body"])
            if d.get("kind") == "look":
                out.append(_look_from(d, "user"))
    return out


def _find(items, key: str, what: str):
    k = key.lower().replace(" ", "-")
    for it in items:
        if k in (it.slug, it.name.lower().replace(" ", "-")):
            return it
    raise MbError("NOT_FOUND", f"no {what} named '{key}'", hint=f"available: {', '.join(i.slug for i in items)}")


def get_mode(key: str, conn: sqlite3.Connection | None = None) -> Mode:
    return _find(list_modes(conn), key, "mode")


def get_look(key: str, conn: sqlite3.Connection | None = None) -> Look:
    return _find(list_looks(conn), key, "look")
