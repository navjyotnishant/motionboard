"""Prompt composition in three parts (feature 003, FR-017).

- plate: what the first frame looks like (image models)
- motion: what moves and how (video models), from the look's motion grammar refined by the art direction
- continuity: what must stay the same, from the approved Bible, the grammar and the shot's own requirements

Each part is composed by its own function. The plate and motion results are stored in `shot.plate_prompt` and
`shot.motion_prompt`; `mb shot prompts` shows all parts. Only the approved Bible reaches prompts, never a draft.
Without a Bible, motifs or continuity, and on a look without a grammar, the output equals the pre-003 prompts.
"""

import json
import re
import sqlite3
from dataclasses import dataclass, field

from motionboard.db import repo
from motionboard.db.events import Actor
from motionboard.direction import assoc, store
from motionboard.direction import bible as bible_mod
from motionboard.direction import grammar as grammar_mod
from motionboard.direction.grammar import Grammar

MAX_WORDS = 200  # LTX guidance: one flowing paragraph, under about 200 words

# What the a2v model needs to hear for clear lip-sync. Proven on the Almost Yours singer tests: without it,
# words like "softly" make the mouth barely move and similar sounds blur ("dark" reads as "bark").
SINGING = ("singing the words with clear, precise lip movement exactly in sync with the vocal, "
           "the mouth opening and closing on each syllable, natural jaw and throat movement, "
           "stable face, the head moving gently with the melody")

CREATIVE_KEYS = ("intent", "audience", "metaphor", "motifs", "continuity", "materials", "objects")
PARTS = ("plate", "motion")


@dataclass
class Prompts:
    plate: str
    motion: str
    continuity_plate: list[str] = field(default_factory=list)
    continuity_motion: list[str] = field(default_factory=list)
    negative: str = ""
    grammar: str = ""
    warnings: list[str] = field(default_factory=list)
    rules: Grammar | None = None  # the effective grammar for this shot (look + Bible + its characters)
    materials: list[dict] = field(default_factory=list)  # [{name, why}] the Bible materials of this shot
    objects: list[dict] = field(default_factory=list)


def _sentence(text: str) -> str:
    t = (text or "").strip().rstrip(". ")
    return (t[0].upper() + t[1:] + ".") if t else ""


def _for_motion(style: str) -> str:
    """A look's style line describes a still frame; for video, 'still' asks for no motion, so drop it."""
    return re.sub(r"\bfilm still\b", "film shot", style or "")


# --- the three parts -----------------------------------------------------------------------------------------

def _fresh(lines: list[str] | None, parts: list[str], style: str) -> list[str]:
    """Lines that say something the prompt does not say yet (a material line equal to part of the look is skipped)."""
    out: list[str] = []
    for line in lines or []:
        low = (line or "").strip().lower()
        if low and not any(low in p.lower() for p in [*parts, *out, style or ""]):
            out.append(line.strip())
    return out


def plate_text(visual: str, has_figure: bool, look, cast_lines: list[str], *, motif_lines: list[str] | None = None,
               object_lines: list[str] | None = None, material_lines: list[str] | None = None,
               world_lines: list[str] | None = None, continuity: list[str] | None = None) -> str:
    """The first frame: the shot, who is in it, the motifs' state, this shot's objects and materials, the film's
    world, the look, what stays fixed."""
    parts = [visual.rstrip(". ")]
    if has_figure:
        parts += [c for c in cast_lines if c]
    parts += [m for m in motif_lines or [] if m]
    parts += _fresh(object_lines, parts, look.style_line)
    parts += _fresh(material_lines, parts, look.style_line)
    parts += [w for w in world_lines or [] if w]
    parts.append(look.style_line)
    if not has_figure:
        parts.append(look.no_figure_line)
    if continuity:
        parts.append("Keep consistent with the rest of the film: " + "; ".join(continuity))
    return ". ".join(p.strip() for p in parts if p) + "."


def motion_text(action: str, camera: str, has_figure: bool, look, lip_sync: bool = False, visual: str = "",
                cast: list[str] | None = None, *, grammar: Grammar | None = None,
                character_motion: list[str] | None = None, continuity: list[str] | None = None) -> str:
    """What moves and how, in the order LTX reads best: action, continuity, movement, people, scene, camera, light.

    The plate fixes the first frame, so this says what moves and keeps the scene and the cast stable. Forbidden
    movement is never named here. Continuity sits early so the word limit trims the generic style tail first.
    """
    g = grammar or look.grammar
    parts = [_sentence(action),
             f"One continuous shot with no cut: the place, the time of day, the light, {g.subject} and the framing "
             "stay exactly as in the first frame for the whole shot"]
    # The look's no figure line is written for image models ("only rooms, windows, streets and objects, no
    # people"). A video model reads it as a list of things to show, so it is not used here: the first
    # frame is the whole cast and the whole set. It sits early so the word limit never cuts it.
    parts.append(f"Nobody and nothing new enters the frame, and {g.identity}" if has_figure else
                 "Nobody and nothing new enters the frame: only what the first frame shows")
    if continuity:
        parts.append("Throughout the shot: " + "; ".join(continuity))
    if has_figure:
        parts.append(g.figure)
        if lip_sync:
            parts.append(_sentence(SINGING))
        parts += [_sentence(c) for c in (cast or []) if c]
        parts += [_sentence(c) for c in (character_motion or []) if c]
    else:
        parts.append(g.ambient)
    if visual:
        parts.append(_sentence(f"The scene: {visual}"))
    # The plate fixes the place and the light. Naming the look's world here ("late at night, rain...") made
    # the model leave the plate on shots that differ from it (a sunny street, a wide silhouette), so the
    # motion prompt only asks it to stay where the first frame is.
    if camera:
        parts.append(_sentence(f"Camera: {camera}, smooth and steady, one continuous shot with no cuts"))
    if getattr(look, "realistic", False):
        parts.append("Photorealistic and cinematic, keeping the colour and light of the first frame, gentle film grain")
    else:
        parts.append(_sentence(_for_motion(look.style_line)))
    text = " ".join(_sentence(p) if not p.endswith(".") else p for p in parts if p)
    words = text.split()
    return text if len(words) <= MAX_WORDS else " ".join(words[:MAX_WORDS]).rstrip(",;:") + "."


def continuity_items(body: dict | None, creative: dict, g: Grammar | None = None) -> tuple[list[str], list[str]]:
    """(for the plate, for the motion): the Bible's never-change rules, the shot's own requirement, and for movement
    the grammar's invariants."""
    never = [str(x).strip().rstrip(".") for x in ((body or {}).get("constraints") or {}).get("never_change") or []]
    own = [str(creative.get("continuity") or "").strip().rstrip(".")]
    plate = [x for x in never + own if x]
    motion = [x for x in list(g.invariants if g else ()) + never + own if x]
    return plate, motion


def negative_text(look, body: dict | None) -> str:
    c = (body or {}).get("constraints") or {}
    w = (body or {}).get("world") or {}
    parts = [look.negative if look else "", c.get("negative", ""), ", ".join(c.get("forbidden") or []),
             ", ".join(w.get("excluded") or [])]
    return ", ".join(p.strip(" ,") for p in parts if p and p.strip(" ,"))


# --- from the shot's data ------------------------------------------------------------------------------------

def creative_of(shot: dict) -> dict:
    try:
        c = json.loads(shot.get("creative") or "{}") if isinstance(shot.get("creative"), str) else (
            shot.get("creative") or {})
    except json.JSONDecodeError:
        c = {}
    return c if isinstance(c, dict) else {}


def cast_lines(cast: list[dict], body: dict | None) -> list[str]:
    """Each character's description: the approved Bible's prompt line wins over the style line (research R6)."""
    out = []
    for c in cast:
        entry = bible_mod.character_entry(body, c["name"])
        out.append((entry or {}).get("prompt_line") or c.get("style_line") or "")
    return out


def motif_lines(creative: dict, body: dict | None) -> list[str]:
    out = []
    for m in creative.get("motifs") or []:
        name, state = str(m.get("name", "")).strip(), str(m.get("state", "")).strip()
        if not name:
            continue
        entry = bible_mod.motif_entry(body, name)
        base = ((entry or {}).get("prompt_line") or name).rstrip(". ")
        out.append(f"{base}, {state}" if state else base)
    return out


def world_lines(body: dict | None) -> list[str]:
    b = body or {}
    return [x for x in ((b.get("world") or {}).get("prompt_line"), (b.get("color") or {}).get("prompt_line"),
                        (b.get("lighting") or {}).get("prompt_line")) if x]


def effective_grammar(look, body: dict | None) -> Grammar:
    return grammar_mod.refine(look.grammar, (body or {}).get("motion"))


def compose(look, body: dict | None, *, visual: str, action: str, camera: str, has_figure: bool, lip_sync: bool,
            cast: list[dict], creative: dict) -> Prompts:
    """All parts for one shot from plain values (used while drafting, before the shot row exists)."""
    names = [c["name"] for c in cast] if has_figure else []
    bible_chars = (body or {}).get("characters") or []
    mats = assoc.materials(body, visual=visual, creative=creative, cast=names)
    objs = assoc.objects(body, visual=visual, creative=creative)
    g = grammar_mod.with_characters(effective_grammar(look, body), bible_chars, names)
    g = grammar_mod.with_materials(g, [m.get("motion_response") for m, _ in mats])
    c_plate, c_motion = continuity_items(body, creative, g)
    lines = cast_lines(cast, body) if has_figure else []
    char_motion = grammar_mod.character_lines(bible_chars, names)
    plate = plate_text(visual, has_figure, look, lines, motif_lines=motif_lines(creative, body),
                       object_lines=[assoc.object_line(o) for o, _ in objs],
                       material_lines=[assoc.material_line(m) for m, _ in mats],
                       world_lines=world_lines(body), continuity=c_plate)
    motion = motion_text(action, camera, has_figure, look, lip_sync, visual, lines, grammar=g,
                         character_motion=char_motion, continuity=c_motion)
    warnings = [f"the action asks for '{t}', which the motion grammar ({g.source}) forbids"
                for t in grammar_mod.forbidden_hits(action, g)] + assoc.unknown(body, creative)
    return Prompts(plate, motion, c_plate, c_motion, negative_text(look, body), g.source, warnings, g,
                   [{"name": m["name"], "why": why} for m, why in mats],
                   [{"name": o["name"], "why": why} for o, why in objs])


def cast_rows(conn: sqlite3.Connection, shot_id: str) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT c.name, c.style_line FROM shot_character sc JOIN character c ON c.id = sc.character_id "
        "WHERE sc.shot_id = ? ORDER BY c.name", (shot_id,))]


def for_shot(conn: sqlite3.Connection, project: dict, shot: dict, look, body: dict | None = None,
             overrides: dict | None = None) -> Prompts:
    """Compose a stored shot, with optional field overrides (an edit about to be saved)."""
    s = {**shot, **(overrides or {})}
    if body is None:
        body = store.approved_body(conn, project["id"])
    return compose(look, body, visual=s["visual"], action=s["action"], camera=s["camera"],
                   has_figure=bool(s["has_figure"]), lip_sync=bool(s["lip_sync"]), cast=cast_rows(conn, shot["id"]),
                   creative=creative_of(s))


def settle(conn: sqlite3.Connection, project: dict, look, actor: Actor,
           shot_ids: list[str] | None = None) -> list[dict]:
    """Give shots made before prompt baselines existed (`plate_base` is NULL) a baseline, before anything changes.

    The baseline is what the engine generates from the direction as it stands now. A stored prompt that differs
    from it is kept as the creator's override, never assumed to be stale: a hand edit and a prompt written by an
    older engine look the same, and losing a hand edit is the worse mistake. Returns the overrides adopted."""
    if look is None:
        return []
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM shot WHERE project_id = ? AND (plate_base IS NULL OR motion_base IS NULL) ORDER BY ord",
        (project["id"],))]
    if shot_ids is not None:
        rows = [r for r in rows if r["id"] in set(shot_ids)]
    if not rows:
        return []
    body = store.approved_body(conn, project["id"])
    adopted = []
    for s in rows:
        p = for_shot(conn, project, s, look, body)
        fields: dict = {}
        for part, new in (("plate", p.plate), ("motion", p.motion)):
            if s[f"{part}_base"] is not None:
                continue
            stored = (s[f"{part}_prompt"] or "").strip()
            authored = bool(stored) and stored != new
            fields[f"{part}_base"] = new
            fields[f"{part}_authored"] = authored
            if authored:
                adopted.append({"shot": s["ord"], "part": part})
        repo.update(conn, "shot", s["id"], fields, actor)
    return adopted


def recompose(conn: sqlite3.Connection, project: dict, shot_ids: list[str] | None, look, actor: Actor,
              mark_redo: bool, report: dict | None = None) -> list[int]:
    """Regenerate prompt baselines from the current direction. A generated prompt follows its baseline; an authored
    override is never rewritten (FR-031) and is listed in `report["overrides"]` with whether the baseline under it
    moved. With `mark_redo`, a finished plate whose prompt changed is marked for redo (a cast or reference edit).
    Without it nothing but prompts changes: an art direction approval reports affected shots instead (research R4,
    R5). Returns the shot numbers whose effective prompt was rewritten."""
    from motionboard.storyboard.board import PLATE_DONE

    if look is None:
        return []
    body = store.approved_body(conn, project["id"])
    if shot_ids is None:
        shot_ids = [r["id"] for r in conn.execute("SELECT id FROM shot WHERE project_id = ? ORDER BY ord",
                                                  (project["id"],))]
    changed = []
    for sid in shot_ids:
        s = repo.get(conn, "shot", sid)
        if not s:
            continue
        p = for_shot(conn, project, s, look, body)
        fields: dict = {}
        for part, new in (("plate", p.plate), ("motion", p.motion)):
            moved = s[f"{part}_base"] != new
            if moved:
                fields[f"{part}_base"] = new
            if s[f"{part}_authored"]:
                if report is not None:
                    report.setdefault("overrides", []).append({
                        "shot": s["ord"], "part": part, "baseline_changed": moved and s[f"{part}_base"] is not None})
                continue
            if s[f"{part}_prompt"] != new:
                fields[f"{part}_prompt"] = new
        if not fields:
            continue
        rewritten = "plate_prompt" in fields or "motion_prompt" in fields
        if mark_redo and "plate_prompt" in fields and s["state"] in PLATE_DONE:
            fields.update(state="needs_redo", dirty=True)
        if rewritten:
            fields["updated_at"] = repo.now()
            changed.append(s["ord"])
        repo.update(conn, "shot", sid, fields, actor)
    return changed
