"""Project export and import (contracts/storyboard.schema.json, T033).

Export writes a folder: project.json plus media copied under media/ with
relative paths, so the folder can be zipped and moved. Import creates a new
project from such a folder (or from a bare project.json without media).
"""

import json
import shutil
import sqlite3
from pathlib import Path

from motionboard import projects
from motionboard.db import repo
from motionboard.db.events import Actor
from motionboard.report import MbError

FORMAT = "motionboard.project.v1"
PROJECT_KEYS = ("title", "lyrics", "idea", "aspect", "look", "mode", "visual_look", "synthetic_people")
SHOT_KEYS = ("ord", "start", "end", "frames", "lyric", "visual", "action", "camera", "has_figure", "lip_sync",
             "plate_prompt", "motion_prompt", "state", "plate_base", "motion_base", "plate_authored",
             "motion_authored", "override_kept")


def _kept(value) -> dict:
    """A shot's keep decisions, {part: art direction version}, from a stored JSON string or an export's object.
    Art direction versions keep their numbers through export and import, so a decision still points at the version
    it was made for; anything malformed is dropped."""
    if isinstance(value, str):
        try:
            value = json.loads(value or "{}")
        except json.JSONDecodeError:
            return {}
    if not isinstance(value, dict):
        return {}
    return {k: v for k, v in value.items()
            if k in ("plate", "motion") and isinstance(v, int) and not isinstance(v, bool)}


def _copy(src: str | None, folder: Path, rel: str) -> str | None:
    if not src or not Path(src).exists():
        return None
    dst = folder / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return rel


def export(conn: sqlite3.Connection, project: dict, out: Path, with_media: bool = True) -> Path:
    pid = project["id"]
    out.mkdir(parents=True, exist_ok=True)
    a = repo.get(conn, "song_analysis", pid, key="project_id") or {}
    doc = {
        "format": FORMAT,
        "project": {
            **{k: project.get(k) for k in PROJECT_KEYS},
            "synthetic_people": bool(project.get("synthetic_people")),
            "segment": {"start": project.get("segment_start"), "end": project.get("segment_end")},
            "theme": json.loads(project.get("theme") or "{}"),
            "template": project.get("mode"),
            "song": _copy(project.get("song_path"), out, f"media/{Path(project['song_path']).name}")
            if with_media and project.get("song_path") else None,
        },
        "analysis": {
            "tempo_bpm": a.get("tempo_bpm"),
            "beats": json.loads(a.get("beats") or "[]"),
            "lines": json.loads(a.get("lines") or "[]"),
            "verified_vocal_alignment": bool(a.get("verified_vocal_alignment")),
        },
        "concepts": [
            {k: c[k] for k in ("title", "premise", "hero_image_idea", "chosen")}
            | {"sample_shots": json.loads(c["sample_shots"] or "[]"), "chosen": bool(c["chosen"])}
            for c in repo.find(conn, "concept", project_id=pid)
        ],
        "characters": [
            {"name": c["name"], "style_line": c["style_line"],
             "reference_image": _copy(c["reference_image"], out, f"media/characters/{Path(c['reference_image']).name}")
             if with_media and c["reference_image"] else None,
             "references": [
                 {"path": _copy(r["path"], out, f"media/characters/{Path(r['path']).name}") if with_media else None,
                  "purpose": r["purpose"], "description": r["description"], "primary": bool(r["is_primary"]),
                  "ord": r["ord"], "meta": json.loads(r["meta"] or "{}")}
                 for r in repo.find(conn, "character_reference", order="ord", character_id=c["id"])]}
            for c in repo.find(conn, "character", project_id=pid)
        ],
        "shots": [],
        "approvals": {r["stage"]: r["approved_at"] for r in repo.find(conn, "stage_approval", project_id=pid)},
        "art_direction": [
            {k: v[k] for k in ("version", "profile", "status", "note", "created_at", "approved_at", "approved_via")}
            | {"body": json.loads(v["body"] or "{}"), "impact": json.loads(v["impact"] or "{}")}
            for v in repo.find(conn, "art_direction", order="version", project_id=pid)
        ],
        "critiques": [
            {k: c[k] for k in ("stage", "role", "verdict", "summary", "created_at", "resolved_at")}
            | {k: json.loads(c[k] or "[]") for k in ("findings", "checked", "not_checked")}
            for c in repo.find(conn, "critique", order="created_at", project_id=pid)
        ],
    }
    for s in conn.execute("SELECT * FROM shot WHERE project_id = ? ORDER BY ord", (pid,)):
        s = dict(s)
        entry = {k: s[k] for k in SHOT_KEYS} | {"has_figure": bool(s["has_figure"]), "lip_sync": bool(s["lip_sync"]),
                                                "creative": json.loads(s.get("creative") or "{}"),
                                                "override_kept": _kept(s.get("override_kept"))}
        entry["characters"] = [r["name"] for r in conn.execute(
            "SELECT c.name FROM shot_character sc JOIN character c ON c.id = sc.character_id WHERE sc.shot_id = ?",
            (s["id"],))]
        entry["assets"] = []
        for av in repo.find(conn, "asset_version", order="created_at", shot_id=s["id"]):
            rel = None
            if with_media and av["path"]:
                rel = _copy(av["path"], out, f"media/shots/{s['ord']:03d}/{av['id']}{Path(av['path']).suffix}")
            notes = [{"decision": n["decision"], "text": n["text"], "at": n["at"]}
                     for n in repo.find(conn, "review_note", order="at", asset_version_id=av["id"])]
            entry["assets"].append({"kind": av["kind"], "path": rel, "text": av["text"], "source": av["source"],
                                    "active": bool(av["active"]), "cost_usd": av["cost_usd"], "notes": notes})
        doc["shots"].append(entry)
    path = out / "project.json"
    path.write_text(json.dumps(doc, indent=2))
    return path


def import_(conn: sqlite3.Connection, src: Path, actor: Actor = "chat") -> dict:
    src = Path(src)
    path = src / "project.json" if src.is_dir() else src
    base = path.parent
    try:
        doc = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        raise MbError("INVALID_INPUT", f"cannot read {path}: {e}") from e
    if doc.get("format") != FORMAT:
        raise MbError("INVALID_INPUT", f"not a {FORMAT} file")
    pj = doc["project"]
    song = base / pj["song"] if pj.get("song") else None
    p = projects.create(conn, pj["title"], song if song and song.exists() else None, pj.get("lyrics", ""),
                        pj.get("idea", ""), pj["aspect"], pj.get("look", "stylized"), actor)
    pid, folder = p["id"], Path(p["folder"])
    seg = pj["segment"]
    ts = repo.now()
    with repo.tx(conn):
        repo.update(conn, "project", pid, {
            "segment_start": seg.get("start"), "segment_end": seg.get("end"), "mode": pj.get("mode") or pj.get(
                "template"), "visual_look": pj.get("visual_look"), "theme": pj.get("theme") or {},
            "synthetic_people": bool(pj.get("synthetic_people")), "updated_at": ts}, actor)
        an = doc.get("analysis", {})
        repo.insert(conn, "song_analysis", {
            "project_id": pid, "tempo_bpm": an.get("tempo_bpm"), "beats": an.get("beats", []),
            "lines": an.get("lines", []), "verified_vocal_alignment": bool(an.get("verified_vocal_alignment"))},
            actor, key="project_id")
        for c in doc.get("concepts", []):
            repo.insert(conn, "concept", {"project_id": pid, "title": c["title"], "premise": c.get("premise", ""),
                                          "hero_image_idea": c.get("hero_image_idea", ""),
                                          "sample_shots": c.get("sample_shots", []),
                                          "chosen": bool(c.get("chosen"))}, actor)
        char_ids = {}
        for c in doc.get("characters", []):
            # 003 exports list every reference; older ones carry a single reference_image (made the primary).
            refs = c.get("references") or ([{"path": c["reference_image"], "purpose": "other", "primary": True}]
                                           if c.get("reference_image") else [])
            stored = []
            for r in refs:
                if not r.get("path") or not (base / r["path"]).exists():
                    continue
                dst = folder / "plates" / "characters" / Path(r["path"]).name
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(base / r["path"], dst)
                stored.append({**r, "path": str(dst)})
            if stored and not any(r.get("primary") for r in stored):
                stored[0]["primary"] = True
            primary = next((r["path"] for r in stored if r.get("primary")), None)
            cid = char_ids[c["name"]] = repo.insert(conn, "character", {
                "project_id": pid, "name": c["name"], "style_line": c.get("style_line", ""),
                "reference_image": primary}, actor)
            for i, r in enumerate(stored):
                repo.insert(conn, "character_reference", {
                    "character_id": cid, "path": r["path"], "purpose": r.get("purpose", "other"),
                    "description": r.get("description", ""), "is_primary": bool(r.get("primary")),
                    "ord": r.get("ord", i), "meta": r.get("meta") or {}, "created_at": ts}, actor)
        for s in doc["shots"]:
            sid = repo.insert(conn, "shot", {**{k: s.get(k) for k in SHOT_KEYS if k in s}, "project_id": pid,
                                             "override_kept": _kept(s.get("override_kept")),
                                             "frames": s.get("frames", 0), "state": s.get("state", "draft"),
                                             "creative": s.get("creative") or {}, "updated_at": ts}, actor)
            for name in s.get("characters", []):
                if name in char_ids:
                    conn.execute("INSERT INTO shot_character(shot_id, character_id) VALUES (?, ?)",
                                 (sid, char_ids[name]))
            for av in s.get("assets", []):
                path_abs = None
                if av.get("path") and (base / av["path"]).exists():
                    sub = "plates" if av["kind"] == "plate" else "clips"
                    path_abs = str(folder / sub / f"{s['ord']:03d}-{Path(av['path']).name}")
                    shutil.copy2(base / av["path"], path_abs)
                aid = repo.insert(conn, "asset_version", {
                    "shot_id": sid, "kind": av["kind"], "path": path_abs, "text": av.get("text"),
                    "source": av.get("source", "import"), "cost_usd": av.get("cost_usd", 0),
                    "active": bool(av.get("active")), "created_at": ts}, actor)
                for n in av.get("notes", []):
                    repo.insert(conn, "review_note", {"asset_version_id": aid, "decision": n["decision"],
                                                      "text": n.get("text", ""), "at": n.get("at", ts)}, actor)
        for stage, at in (doc.get("approvals") or {}).items():
            if at:
                conn.execute("INSERT INTO stage_approval(project_id, stage, approved_at, via) VALUES (?, ?, ?, ?)",
                             (pid, stage, at, "chat"))
        versions: dict[int, str] = {}
        last_approved = None
        for v in sorted(doc.get("art_direction") or [], key=lambda x: x["version"]):
            versions[v["version"]] = repo.insert(conn, "art_direction", {
                "project_id": pid, "version": v["version"], "profile": v.get("profile", "compact"),
                "status": v["status"], "body": v.get("body") or {}, "note": v.get("note", ""),
                "based_on": last_approved, "impact": v.get("impact") or {}, "created_at": v.get("created_at") or ts,
                "updated_at": ts, "created_via": "chat", "approved_at": v.get("approved_at"),
                "approved_via": v.get("approved_via")}, actor)
            if v["status"] in ("approved", "superseded"):
                last_approved = versions[v["version"]]
        for c in doc.get("critiques") or []:
            repo.insert(conn, "critique", {
                "project_id": pid, **{k: c[k] for k in ("stage", "role", "verdict")}, "summary": c.get("summary", ""),
                "findings": c.get("findings") or [], "checked": c.get("checked") or [],
                "not_checked": c.get("not_checked") or [], "created_at": c.get("created_at") or ts,
                "resolved_at": c.get("resolved_at")}, actor)
    p = projects.get(conn, pid)
    if doc.get("art_direction"):
        from motionboard.direction import service

        service.write_markdown(conn, p)
    return p
