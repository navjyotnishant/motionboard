"""Where a shot contradicts the active direction (feature 003, FR-028 to FR-030).

Custom authoring is kept: nothing here rewrites a prompt. It reports
- motion_grammar: an action or a motion prompt that asks for movement the effective grammar forbids (the look, the
  approved Bible and the rules of the characters in the shot);
- plate_direction: an authored plate prompt that adds something the approved Bible forbids or excludes;
- undesigned_character: under an approved full Bible, a character in the shot with no design and no recorded
  exception.

An authored override the creator chose to keep for the current art direction version is still listed, marked kept,
and does not hold up plate generation.
"""

import json
import sqlite3

from motionboard.direction import bible as bible_mod
from motionboard.direction import grammar as grammar_mod
from motionboard.direction import store

PARTS = ("plate", "motion")


def _count(term: str, text: str) -> int:
    return len(grammar_mod._pattern(term).findall(text or ""))


def plate_terms(text: str, base: str, body: dict | None) -> list[str]:
    """Forbidden or excluded things an authored plate prompt names more often than the generated one does (the
    look's own "no people" line is not a conflict)."""
    b = body or {}
    terms = list((b.get("constraints") or {}).get("forbidden") or []) + list((b.get("world") or {}).get("excluded")
                                                                             or [])
    return [t for t in dict.fromkeys(terms) if str(t).strip() and _count(t, text) > _count(t, base or "")]


def version_of(conn: sqlite3.Connection, project_id: str) -> int:
    row = store.approved(conn, project_id)
    return row["version"] if row else 0


def kept(shot: dict, part: str, version: int) -> bool:
    try:
        return json.loads(shot.get("override_kept") or "{}").get(part) == version
    except (json.JSONDecodeError, AttributeError):
        return False


def _join(terms: list[str]) -> str:
    return ", ".join(f"'{t}'" for t in terms)


def for_shot(conn: sqlite3.Connection, project: dict, shot: dict, look, body: dict | None = None,
             approved: dict | None = None) -> list[dict]:
    from motionboard.storyboard import compose

    if look is None:
        return []
    if approved is None:
        approved = store.approved(conn, project["id"])
    if body is None:
        body = store.body(approved) if approved else None
    version = approved["version"] if approved else 0
    pr = compose.for_shot(conn, project, shot, look, body)
    g, n, out = pr.rules, shot["ord"], []

    def add(part: str, kind: str, terms: list[str], message: str, authored: bool = False) -> None:
        out.append({"shot": n, "part": part, "kind": kind, "terms": terms, "authored": authored,
                    "kept": authored and kept(shot, part, version), "message": f"shot {n} {message}"})

    in_action = grammar_mod.forbidden_hits(shot["action"], g)
    if in_action:
        add("action", "motion_grammar", in_action,
            f"action asks for {_join(in_action)}, which the motion grammar ({g.source}) forbids")
    in_motion = grammar_mod.forbidden_hits(shot["motion_prompt"], g)
    if shot.get("motion_authored"):
        if in_motion:
            add("motion", "motion_grammar", in_motion,
                f"authored motion prompt asks for {_join(in_motion)}, which the motion grammar ({g.source}) forbids",
                True)
    elif set(in_motion) - set(in_action):
        extra = [t for t in in_motion if t not in in_action]
        add("motion", "motion_grammar", extra,
            f"motion prompt names {_join(extra)}, which the motion grammar ({g.source}) forbids")
    if shot.get("plate_authored"):
        terms = plate_terms(shot["plate_prompt"], shot.get("plate_base") or pr.plate, body)
        if terms:
            add("plate", "plate_direction", terms,
                f"authored plate prompt adds {_join(terms)}, which art direction version {version} forbids", True)
    if approved and approved["profile"] == "full" and shot["has_figure"]:
        excused = bible_mod.excused_characters(body)
        for c in compose.cast_rows(conn, shot["id"]):
            if not bible_mod.character_entry(body, c["name"]) and c["name"].upper() not in excused:
                add("cast", "undesigned_character", [c["name"]],
                    f"shows {c['name']}, who has no design in art direction version {version}")
    return out


def for_project(conn: sqlite3.Connection, project: dict, look, ords: list[int] | None = None) -> list[dict]:
    if look is None:
        return []
    approved = store.approved(conn, project["id"])
    body = store.body(approved) if approved else None
    rows = [dict(r) for r in conn.execute("SELECT * FROM shot WHERE project_id = ? ORDER BY ord", (project["id"],))]
    out: list[dict] = []
    for s in rows:
        if ords is None or s["ord"] in ords:
            out += for_shot(conn, project, s, look, body, approved)
    return out


def blocking(found: list[dict]) -> list[dict]:
    return [c for c in found if not c["kept"]]


def overrides(conn: sqlite3.Connection, project: dict, look) -> list[dict]:
    """Every authored override with its generated baseline, whether it was kept, and its conflicts now."""
    approved = store.approved(conn, project["id"])
    body = store.body(approved) if approved else None
    version = approved["version"] if approved else 0
    out = []
    for r in conn.execute("SELECT * FROM shot WHERE project_id = ? ORDER BY ord", (project["id"],)):
        s = dict(r)
        if not (s["plate_authored"] or s["motion_authored"]):
            continue
        found = for_shot(conn, project, s, look, body, approved) if look is not None else []
        for part in PARTS:
            if s[f"{part}_authored"]:
                out.append({"shot": s["ord"], "part": part, "text": s[f"{part}_prompt"],
                            "generated": s[f"{part}_base"] or "", "kept": kept(s, part, version),
                            "conflicts": [c["message"] for c in found if c["part"] == part]})
    return out
