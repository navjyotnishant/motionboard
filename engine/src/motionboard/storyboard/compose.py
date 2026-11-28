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
from motionboard.direction import bible as bible_mod
from motionboard.direction import grammar as grammar_mod
from motionboard.direction import store
from motionboard.direction.grammar import Grammar

MAX_WORDS = 200  # LTX guidance: one flowing paragraph, under about 200 words

# What the a2v model needs to hear for clear lip-sync. Proven on the Almost Yours singer tests: without it,
# words like "softly" make the mouth barely move and similar sounds blur ("dark" reads as "bark").
SINGING = ("singing the words with clear, precise lip movement exactly in sync with the vocal, "
           "the mouth opening and closing on each syllable, natural jaw and throat movement, "
           "stable face, the head moving gently with the melody")

CREATIVE_KEYS = ("intent", "audience", "metaphor", "motifs", "continuity")


@dataclass
class Prompts:
    plate: str
    motion: str
    continuity_plate: list[str] = field(default_factory=list)
    continuity_motion: list[str] = field(default_factory=list)
    negative: str = ""
    grammar: str = ""
    warnings: list[str] = field(default_factory=list)


def _sentence(text: str) -> str:
    t = (text or "").strip().rstrip(". ")
    return (t[0].upper() + t[1:] + ".") if t else ""


def _for_motion(style: str) -> str:
    """A look's style line describes a still frame; for video, 'still' asks for no motion, so drop it."""
    return re.sub(r"\bfilm still\b", "film shot", style or "")


# --- the three parts -----------------------------------------------------------------------------------------

def plate_text(visual: str, has_figure: bool, look, cast_lines: list[str], *, motif_lines: list[str] | None = None,
               world_lines: list[str] | None = None, continuity: list[str] | None = None) -> str:
    """The first frame: the shot, who is in it, the motifs' state, the film's world, the look, what stays fixed."""
    parts = [visual.rstrip(". ")]
    if has_figure:
        parts += [c for c in cast_lines if c]
    parts += [m for m in motif_lines or [] if m]
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
    g = effective_grammar(look, body)
    c_plate, c_motion = continuity_items(body, creative, g)
    names = [c["name"] for c in cast]
    lines = cast_lines(cast, body) if has_figure else []
    char_motion = grammar_mod.character_lines((body or {}).get("characters") or [], names) if has_figure else []
    plate = plate_text(visual, has_figure, look, lines, motif_lines=motif_lines(creative, body),
                       world_lines=world_lines(body), continuity=c_plate)
    motion = motion_text(action, camera, has_figure, look, lip_sync, visual, lines, grammar=g,
                         character_motion=char_motion, continuity=c_motion)
    warnings = [f"the action asks for '{t}', which the motion grammar ({g.source}) forbids"
                for t in grammar_mod.forbidden_hits(action, g)]
    return Prompts(plate, motion, c_plate, c_motion, negative_text(look, body), g.source, warnings)


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


def recompose(conn: sqlite3.Connection, project: dict, shot_ids: list[str] | None, look, actor: Actor,
              mark_redo: bool) -> list[int]:
    """Rewrite plate and motion prompts from the current direction. With `mark_redo`, a finished plate whose prompt
    changed is marked for redo (a cast or reference edit). Without it nothing but the prompts changes: an art
    direction approval reports affected shots instead (research R4, R5). Returns the shot numbers rewritten."""
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
        fields = {}
        if p.plate != s["plate_prompt"]:
            fields["plate_prompt"] = p.plate
        if p.motion != s["motion_prompt"]:
            fields["motion_prompt"] = p.motion
        if not fields:
            continue
        if mark_redo and "plate_prompt" in fields and s["state"] in PLATE_DONE:
            fields.update(state="needs_redo", dirty=True)
        fields["updated_at"] = repo.now()
        repo.update(conn, "shot", sid, fields, actor)
        changed.append(s["ord"])
    return changed
