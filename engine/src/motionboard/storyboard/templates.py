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


def _slug(name: str) -> str:
    import re

    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not s:
        raise MbError("INVALID_INPUT", "template name needs letters or digits")
    return s


def save_from_project(conn: sqlite3.Connection, project: dict, name: str, actor) -> Mode:
    """Save the project's board as a user mode (002 T027). Song specific parts are stripped: lyrics leave the
    visuals, the look's world becomes {world}, timing becomes the base mode's rhythm."""
    from motionboard.db import repo

    slug = _slug(name)
    if any(m.slug == slug or m.name.lower() == name.lower() for m in list_modes(conn)):
        raise MbError("INVALID_INPUT", f"a mode named '{name}' already exists")
    shots = [dict(r) for r in conn.execute("SELECT * FROM shot WHERE project_id = ? ORDER BY ord", (project["id"],))]
    if not shots:
        raise MbError("INVALID_INPUT", "the board has no shots to save")
    base = get_mode(project["mode"], conn) if project.get("mode") else None
    look = get_look(project["visual_look"], conn) if project.get("visual_look") else None
    pattern = []
    for s in shots:
        visual = s["visual"]
        if s["lyric"]:
            visual = visual.replace(s["lyric"], "{lyric}")
        if look and look.world and look.world in visual:
            visual = visual.replace(look.world, "{world}")
        elif "{world}" not in visual:
            visual = visual.rstrip(". ") + ", {world}"
        pattern.append({"role": f"shot-{s['ord']}", "visual": visual, "action": s["action"], "camera": s["camera"],
                        "has_figure": bool(s["has_figure"]), "lip_sync": bool(s["lip_sync"])})
    chars = [r["name"] for r in conn.execute("SELECT name FROM character WHERE project_id = ? ORDER BY name",
                                             (project["id"],))]
    r = base.rhythm if base else Rhythm("line", 8, 2.0, 5.0)
    body = {"kind": "mode", "slug": slug, "name": name, "animation": base.animation if base else "mood-loop",
            "summary": f"Saved from '{project['title']}'" + (f", based on {base.name}" if base else ""),
            "characters": chars, "lip_sync": base.lip_sync if base else "never",
            "rhythm": {"unit": r.unit, "beats_per_shot": r.beats_per_shot, "min_shot_s": r.min_shot_s,
                       "max_shot_s": r.max_shot_s},
            "pattern": pattern}
    mode = _validate_mode(_mode_from(body, "user"))
    with repo.tx(conn):
        repo.insert(conn, "template", {"name": name, "source": "user", "body": yaml.safe_dump(body, sort_keys=False)},
                    actor)
    return mode
