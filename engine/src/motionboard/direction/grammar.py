"""Motion grammar: how the subjects of a look move, what never moves, and what must not change (research R9).

A look may define a `motion` block in its YAML. Without one the default human grammar applies, and it reproduces
the motion text Motionboard wrote before feature 003 word for word. The approved Bible can refine the grammar for
a film and for each character. Forbidden movement is never written into the positive prompt, even negated; video
backends take no negative prompt, so a check warns when an action asks for it (research R10).
"""

import re
from dataclasses import dataclass, field, replace

KEYS = ("subject", "identity", "figure", "ambient", "allowed", "forbidden", "materials", "camera", "invariants")
LIST_KEYS = ("allowed", "forbidden", "materials", "camera", "invariants")


@dataclass(frozen=True)
class Grammar:
    source: str
    subject: str
    identity: str
    figure: str
    ambient: str
    allowed: tuple[str, ...] = field(default_factory=tuple)
    forbidden: tuple[str, ...] = field(default_factory=tuple)
    materials: tuple[str, ...] = field(default_factory=tuple)
    camera: tuple[str, ...] = field(default_factory=tuple)
    invariants: tuple[str, ...] = field(default_factory=tuple)


DEFAULT = Grammar(
    source="default (people)",
    subject="the people",
    identity="each person keeps the same face, hair and clothes from the first frame to the last",
    figure=("The movement is slow, natural and continuous, with small lifelike details: steady breathing, "
            "soft blinking, hair and fabric shifting slightly, no sudden jumps"),
    ambient=("Subtle natural motion runs through the frame: light flickers softly, the air and small "
             "particles drift, reflections shimmer"),
    allowed=("natural breathing", "blinking", "weight shifts", "facial expressions", "hair and fabric movement"),
)


def validate(block: dict, where: str) -> list[str]:
    """Problems with a motion block from a look or a Bible."""
    if not isinstance(block, dict):
        return [f"{where}: motion must be a mapping"]
    out = [f"{where}.motion.{k}: unknown key (allowed: {', '.join(KEYS)}, description)"
           for k in block if k not in KEYS and k != "description"]
    for k in LIST_KEYS:
        if k in block and not (isinstance(block[k], list) and all(isinstance(x, str) for x in block[k])):
            out.append(f"{where}.motion.{k}: must be a list of text")
    return out


def _apply(g: Grammar, block: dict | None, source: str) -> Grammar:
    if not block:
        return g
    changes: dict = {}
    for k in KEYS:
        v = block.get(k)
        if not v:
            continue
        changes[k] = tuple(v) if k in LIST_KEYS else str(v).strip().rstrip(".")
    # A Bible that lists what is allowed but writes no figure sentence still gets a figure sentence from the list,
    # so the default human sentence never survives a film that redefined movement.
    if "figure" not in changes and "allowed" in changes:
        changes["figure"] = "Movement: " + _join(changes["allowed"])
    if "figure" not in changes and block.get("description"):
        changes["figure"] = str(block["description"]).strip().rstrip(".")
    return replace(g, source=f"{g.source} + {source}", **changes) if changes else g


def for_look(motion_block: dict | None, look_slug: str) -> Grammar:
    if not motion_block:
        return DEFAULT
    return replace(_apply(DEFAULT, motion_block, f"look {look_slug}"), source=f"look {look_slug}")


def refine(g: Grammar, bible_motion: dict | None) -> Grammar:
    return _apply(g, bible_motion, "art direction")


def character_lines(bible_characters: list[dict], names: list[str]) -> list[str]:
    """Character-specific movement for the characters in a shot, from the approved Bible."""
    wanted = {n.upper() for n in names}
    out = []
    for c in bible_characters or []:
        name = str(c.get("name", "")).strip().upper()
        m = c.get("motion") or {}
        if name not in wanted or not m:
            continue
        if m.get("description"):
            out.append(f"{name}: {str(m['description']).strip().rstrip('.')}")
        elif m.get("allowed"):
            out.append(f"{name} moves with {_join(m['allowed'])}")
    return out


def _join(items) -> str:
    items = [str(i).strip() for i in items if str(i).strip()]
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1] if items else ""


def _pattern(term: str) -> re.Pattern:
    words = re.findall(r"[a-z]+", term.lower())
    if len(words) == 1:
        stem = re.sub(r"(ing|ed|es|s)$", "", words[0]) if len(words[0]) > 5 else words[0]
        return re.compile(rf"\b{re.escape(stem)}", re.I)
    return re.compile(r"\b" + r"\W+".join(map(re.escape, words)) + r"\b", re.I)


def forbidden_hits(text: str, g: Grammar, extra: tuple[str, ...] = ()) -> list[str]:
    """Forbidden movements named in `text` (an action or a composed motion prompt)."""
    return [t for t in (*g.forbidden, *extra) if t.strip() and _pattern(t).search(text or "")]
