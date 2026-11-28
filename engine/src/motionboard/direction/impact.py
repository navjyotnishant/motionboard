"""What a change to the approved art direction affects (research R4).

Identifies shots and their active plates and clips; changes nothing. The creator decides what to redo.
"""

import json
import sqlite3

# Sections whose change alters every first frame, and those that only alter movement.
PLATE_SECTIONS = ("world", "color", "lighting", "materials", "objects", "constraints")
CLIP_SECTIONS = ("motion",)
FRAME_AND_MOVE = ("camera",)
REVIEW_ONLY = ("identity",)


def _by_name(items: list | None, key: str = "name") -> dict[str, dict]:
    return {str(i.get(key, "")).strip().lower(): i for i in items or [] if isinstance(i, dict)}


def changes(old: dict | None, new: dict) -> dict:
    """Sections that differ, plus which characters and motifs differ by name."""
    old = old or {}
    sections = sorted(k for k in set(old) | set(new) if old.get(k) != new.get(k))
    oc, nc = _by_name(old.get("characters")), _by_name(new.get("characters"))
    om, nm = _by_name(old.get("motifs")), _by_name(new.get("motifs"))
    def look(c: dict | None) -> dict | None:
        return {k: v for k, v in c.items() if k != "motion"} if c else None

    chars = sorted(n for n in set(oc) | set(nc) if look(oc.get(n)) != look(nc.get(n)))
    char_motion = sorted(n for n in set(oc) | set(nc)
                         if (oc.get(n) or {}).get("motion") != (nc.get(n) or {}).get("motion"))
    motifs = sorted(n for n in set(om) | set(nm) if om.get(n) != nm.get(n))
    return {"sections": sections, "characters": chars, "character_motion": char_motion, "motifs": motifs}


def _assets(conn: sqlite3.Connection, shot_id: str, kinds: tuple[str, ...]) -> list[dict]:
    marks = ",".join("?" for _ in kinds)
    return [{"id": r["id"], "kind": r["kind"], "created_at": r["created_at"]} for r in conn.execute(
        f"SELECT id, kind, created_at FROM asset_version WHERE shot_id = ? AND active = 1 AND kind IN ({marks}) "
        "ORDER BY kind", (shot_id, *kinds))]


def affected(conn: sqlite3.Connection, project_id: str, old: dict | None, new: dict) -> dict:
    """Shots with active plates or clips that a change from `old` to `new` touches, with the reasons."""
    ch = changes(old, new)
    shots = [dict(r) for r in conn.execute("SELECT id, ord, creative FROM shot WHERE project_id = ? ORDER BY ord",
                                           (project_id,))]
    cast: dict[str, set[str]] = {}
    for r in conn.execute("SELECT sc.shot_id, c.name FROM shot_character sc JOIN character c ON c.id = sc.character_id "
                          "JOIN shot s ON s.id = sc.shot_id WHERE s.project_id = ?", (project_id,)):
        cast.setdefault(r["shot_id"], set()).add(r["name"].lower())
    out = []
    for s in shots:
        frame, move = [], []
        frame += [f"{sec} changed" for sec in ch["sections"] if sec in PLATE_SECTIONS + FRAME_AND_MOVE]
        move += [f"{sec} changed" for sec in ch["sections"] if sec in CLIP_SECTIONS]
        names = cast.get(s["id"], set())
        frame += [f"character {n.upper()} changed" for n in ch["characters"] if n in names]
        move += [f"character {n.upper()} motion changed" for n in ch["character_motion"] if n in names]
        try:
            shot_motifs = {str(m.get("name", "")).lower() for m in json.loads(s["creative"] or "{}").get("motifs", [])}
        except (json.JSONDecodeError, AttributeError):
            shot_motifs = set()
        frame += [f"motif '{m}' changed" for m in ch["motifs"] if m in shot_motifs]
        assets = []
        if frame:
            assets = _assets(conn, s["id"], ("plate", "clip"))
        elif move:
            assets = _assets(conn, s["id"], ("clip",))
        if assets:
            out.append({"shot": s["ord"], "reasons": frame + move, "assets": assets})
    review = [sec for sec in ch["sections"] if sec in REVIEW_ONLY]
    return {"changed": ch["sections"], "characters": [c.upper() for c in ch["characters"]], "motifs": ch["motifs"],
            "review_only": review, "shots": out}
