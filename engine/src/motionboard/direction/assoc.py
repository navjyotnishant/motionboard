"""Which of the Bible's materials and objects belong to one shot (feature 003, FR-027).

A material or an object reaches a shot's plate prompt, and a change to it counts as an impact on that shot, only
when one of these holds. Nothing else is injected, so a prop designed for one scene never appears in every image.

1. The Bible entry says `scope: all` (the world's own surface, for example).
2. The shot lists it by name in its creative context (`materials` or `objects`).
3. Its name appears in the shot's visual ("display cases on both sides" names the object "display case").
4. Materials only: a character in the shot is made of it (the character's `materials` text names it).

The same rules serve prompt composition (storyboard.compose) and the impact report (direction.impact).
"""

import re

ALL = "in every shot"
LISTED = "listed on the shot"
NAMED = "named in the visual"


def named_in(name: str, text: str) -> bool:
    """`name` appears in `text` as whole words; the last word may be plural."""
    words = re.findall(r"[a-z0-9]+", (name or "").lower())
    if not words:
        return False
    return bool(re.search(r"\b" + r"\W+".join(map(re.escape, words)) + r"(?:e?s)?\b", (text or "").lower()))


def _wanted(creative: dict, key: str) -> set[str]:
    return {str(x).strip().lower() for x in (creative or {}).get(key) or [] if str(x).strip()}


def _pick(entries: list | None, listed: set[str], visual: str, extra=None) -> list[tuple[dict, str]]:
    out = []
    for e in entries or []:
        if not isinstance(e, dict):
            continue
        name = str(e.get("name", "")).strip()
        if not name:
            continue
        why = (ALL if e.get("scope") == "all" else LISTED if name.lower() in listed else
               NAMED if named_in(name, visual) else (extra(name) if extra else ""))
        if why:
            out.append((e, why))
    return out


def materials(body: dict | None, *, visual: str, creative: dict, cast: list[str]) -> list[tuple[dict, str]]:
    """(entry, why) for each material of this shot, in Bible order."""
    b = body or {}
    made_of = {str(c.get("name", "")).strip().upper(): str(c.get("materials") or "")
               for c in b.get("characters") or [] if isinstance(c, dict)}
    present = [n.upper() for n in cast]

    def by_cast(name: str) -> str:
        who = [n for n in present if named_in(name, made_of.get(n, ""))]
        return f"{' and '.join(who)} {'is' if len(who) == 1 else 'are'} made of it" if who else ""

    return _pick(b.get("materials"), _wanted(creative, "materials"), visual, by_cast)


def objects(body: dict | None, *, visual: str, creative: dict) -> list[tuple[dict, str]]:
    """(entry, why) for each object of this shot, in Bible order."""
    return _pick((body or {}).get("objects"), _wanted(creative, "objects"), visual)


def unknown(body: dict | None, creative: dict) -> list[str]:
    """Names a shot lists that the Bible does not define."""
    b = body or {}
    out = []
    for key, label in (("materials", "material"), ("objects", "object")):
        have = {str(e.get("name", "")).strip().lower() for e in b.get(key) or [] if isinstance(e, dict)}
        out += [f"{label} '{n}' is listed on the shot but is not in the approved art direction"
                for n in sorted(_wanted(creative, key) - have)]
    return out


def material_line(entry: dict) -> str:
    return str(entry.get("prompt_line") or entry.get("name") or "").strip().rstrip(".")


def object_line(entry: dict) -> str:
    if entry.get("prompt_line"):
        return str(entry["prompt_line"]).strip().rstrip(".")
    name, look = str(entry.get("name") or "").strip(), str(entry.get("appearance") or "").strip().rstrip(".")
    return f"{name}: {look[0].lower() + look[1:]}" if look else name
