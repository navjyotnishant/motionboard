"""The Art Direction Bible: shape, profile checks and the readable Markdown view.

The shape is `art_direction.schema.json` (a copy of specs/003 contracts/art-direction.schema.json, kept equal by a
test). Structure errors refuse the save. Profile gaps are errors that block approval. Warnings are reported only.
"""

import json
import re
from importlib import resources
from pathlib import Path
from typing import Any

import yaml

from motionboard.report import MbError

PROFILES = ("compact", "full")
SECTIONS = ("identity", "world", "characters", "materials", "objects", "color", "lighting", "camera", "motifs",
            "motion", "constraints")

# Words that say nothing about a particular film on their own ("make it cinematic").
VAGUE = {"cinematic", "beautiful", "consistent", "stunning", "epic", "nice", "good", "moody", "aesthetic", "pretty",
         "dramatic", "amazing", "gorgeous", "atmospheric"}
_FILLER = {"make", "it", "very", "really", "and", "more", "look", "looks", "feel", "feels", "should", "be", "the", "a",
           "so", "keep", "everything", "all", "of", "shots", "shot", "visually", "film"}


def schema() -> dict:
    return json.loads(resources.files("motionboard.direction").joinpath("art_direction.schema.json").read_text())


def load_file(path: Path) -> dict:
    """Read a Bible from JSON or YAML."""
    path = Path(path).expanduser()
    try:
        text = path.read_text()
    except OSError as e:
        raise MbError("NOT_FOUND", f"cannot read {path}: {e}") from e
    try:
        data = yaml.safe_load(text) if path.suffix.lower() in (".yaml", ".yml") else json.loads(text)
    except (json.JSONDecodeError, yaml.YAMLError) as e:
        raise MbError("INVALID_INPUT", f"{path.name} cannot be read as JSON or YAML: {e}") from e
    if not isinstance(data, dict):
        raise MbError("INVALID_INPUT", "an art direction file is one object with sections like identity, world, color")
    return data


# --- structure -----------------------------------------------------------------------------------------------

def _resolve(node: dict, root: dict) -> dict:
    ref = node.get("$ref")
    if not ref:
        return node
    target: Any = root
    for part in ref.lstrip("#/").split("/"):
        target = target[part]
    return target


def _check(value: Any, node: dict, root: dict, path: str, errors: list[str]) -> None:
    node = _resolve(node, root)
    if "enum" in node and value not in node["enum"]:
        errors.append(f"{path}: must be one of {', '.join(node['enum'])}")
        return
    kind = node.get("type")
    if kind == "object":
        if not isinstance(value, dict):
            errors.append(f"{path}: must be an object")
            return
        props = node.get("properties", {})
        for k in node.get("required", []):
            if k not in value or value[k] in (None, ""):
                errors.append(f"{path}.{k}: required")
        for k, v in value.items():
            if k in props:
                _check(v, props[k], root, f"{path}.{k}", errors)
            elif node.get("additionalProperties") is False:
                errors.append(f"{path}.{k}: unknown field (allowed: {', '.join(props)})")
    elif kind == "array":
        if not isinstance(value, list):
            errors.append(f"{path}: must be a list")
            return
        for i, v in enumerate(value):
            _check(v, node.get("items", {}), root, f"{path}[{i}]", errors)
    elif kind == "string":
        if not isinstance(value, str):
            errors.append(f"{path}: must be text")
        elif "pattern" in node and not re.fullmatch(node["pattern"], value):
            errors.append(f"{path}: '{value}' does not match {node['pattern']}")


def structure_errors(body: dict) -> list[str]:
    root = schema()
    errors: list[str] = []
    _check(body, root, root, "bible", errors)
    return [e.replace("bible.", "", 1) for e in errors]


# --- profile -------------------------------------------------------------------------------------------------

def _has(d: Any, *keys: str) -> bool:
    for k in keys:
        if not isinstance(d, dict) or not d.get(k):
            return False
        d = d[k]
    return bool(d)


def profile_errors(body: dict, profile: str) -> list[str]:
    if profile not in PROFILES:
        raise MbError("INVALID_INPUT", f"profile must be {' or '.join(PROFILES)}")
    e: list[str] = []
    color = body.get("color") or {}
    if profile == "compact":
        if not _has(body, "identity", "concept"):
            e.append("identity.concept: say in a line what the film is")
        if not _has(body, "world", "description"):
            e.append("world.description: describe the world the film happens in")
        if not (color.get("palette") or color.get("prompt_line")):
            e.append("color: give a palette or a colour line")
        return e
    for k in ("premise", "emotional_intention", "central_metaphor", "song_relationship"):
        if not _has(body, "identity", k):
            e.append(f"identity.{k}: required for a full Bible")
    if not _has(body, "world", "description"):
        e.append("world.description: required for a full Bible")
    if not _has(body, "world", "physical_rules"):
        e.append("world.physical_rules: list at least one rule of how this world behaves")
    if len(color.get("palette") or []) < 2:
        e.append("color.palette: at least two named colours with hex values")
    for k in ("sources", "quality"):
        if not _has(body, "lighting", k):
            e.append(f"lighting.{k}: required for a full Bible")
    for k in ("framing", "movement"):
        if not _has(body, "camera", k):
            e.append(f"camera.{k}: required for a full Bible")
    motifs = body.get("motifs") or []
    if not motifs:
        e.append("motifs: at least one recurring motif with its meaning, evolution and payoff")
    for m in motifs:
        name = m.get("name", "?")
        if not m.get("meaning"):
            e.append(f"motifs[{name}].meaning: what it stands for")
        if len(m.get("evolution") or []) < 2:
            e.append(f"motifs[{name}].evolution: at least two stages, so it changes across the film")
        if not m.get("payoff"):
            e.append(f"motifs[{name}].payoff: how it resolves")
    for k in ("allowed", "forbidden"):
        if not _has(body, "motion", k):
            e.append(f"motion.{k}: required for a full Bible (how things move and what never moves)")
    if not _has(body, "constraints", "never_change"):
        e.append("constraints.never_change: what must stay the same in every shot")
    return e


def _texts(obj: Any, path: str = ""):
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _texts(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _texts(v, f"{path}[{i}]")


def vague_warnings(body: dict) -> list[str]:
    out = []
    for path, text in _texts(body):
        words = re.findall(r"[a-z]+", text.lower())
        if words and all(w in VAGUE | _FILLER for w in words) and any(w in VAGUE for w in words):
            out.append(f"{path}: '{text}' does not say what it means for this film; describe the light, material "
                       "or camera choice instead")
    return out


def cast_warnings(body: dict, project_characters: dict[str, list[int]]) -> list[str]:
    """project_characters: name -> shot numbers the character appears in."""
    named = {str(c.get("name", "")).strip().upper() for c in body.get("characters") or []}
    out = []
    for name, shots in sorted(project_characters.items()):
        if shots and name not in named:
            out.append(f"characters: {name} appears in shots {', '.join(map(str, shots))} but has no design here")
    for name in sorted(named - set(project_characters)):
        out.append(f"characters: {name} is designed here but is not a character in the project")
    return out


def character_entry(body: dict | None, name: str) -> dict | None:
    for c in (body or {}).get("characters") or []:
        if str(c.get("name", "")).strip().upper() == name.upper():
            return c
    return None


def motif_entry(body: dict | None, name: str) -> dict | None:
    for m in (body or {}).get("motifs") or []:
        if str(m.get("name", "")).strip().lower() == name.strip().lower():
            return m
    return None


# --- Markdown view -------------------------------------------------------------------------------------------

def _para(label: str, value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [f"**{label}**", "", *[f"- {v}" for v in value], ""]
    return [f"**{label}**: {value}", ""]


def _section(title: str, d: dict | None, fields: list[tuple[str, str]]) -> list[str]:
    if not d:
        return []
    out = [f"## {title}", ""]
    for key, label in fields:
        out += _para(label, d.get(key))
    return out


def render_markdown(body: dict, header: dict) -> str:
    """A readable Bible for the crew and the creator. `header`: title, version, status, profile, approved_at, note."""
    h = header
    lines = [
        f"# Art Direction: {h.get('title', '')}",
        "",
        f"Version {h.get('version')} · {h.get('status')} · {h.get('profile')} profile"
        + (f" · approved {h['approved_at'][:10]} via {h.get('approved_via')}" if h.get("approved_at") else ""),
        "",
        "> Generated from the Motionboard database. Edit with `mb art draft` or the Studio; changes made in this "
        "file are overwritten.",
        "",
    ]
    if h.get("note"):
        lines += [f"Change note: {h['note']}", ""]
    lines += _section("A. Film identity", body.get("identity"), [
        ("title", "Title"), ("concept", "Concept"), ("premise", "Premise"),
        ("emotional_intention", "Emotional intention"),
        ("audience_experience", "Audience experience"), ("central_metaphor", "Central visual metaphor"),
        ("song_relationship", "Song and image")])
    lines += _section("B. World", body.get("world"), [
        ("description", "World"), ("physical_rules", "Physical rules"), ("architecture", "Architecture and space"),
        ("environment", "Environment"), ("scale", "Scale"), ("time_and_light", "Time and light"),
        ("belongs", "Belongs in this world"), ("excluded", "Never in this world"), ("prompt_line", "Prompt line")])
    chars = body.get("characters") or []
    if chars:
        lines += ["## C. Characters", ""]
        for c in chars:
            lines += [f"### {c.get('name')}", ""]
            for key, label in (("silhouette", "Silhouette and proportions"), ("construction", "Construction"),
                               ("materials", "Materials"), ("costume", "Costume or structure"), ("color", "Colour"),
                               ("details", "Distinguishing details"), ("constraints", "Constraints"),
                               ("references_note", "References"), ("prompt_line", "Prompt line")):
                lines += _para(label, c.get(key))
            m = c.get("motion") or {}
            lines += _para("Moves", m.get("allowed")) + _para("Never", m.get("forbidden"))
    mats, objs = body.get("materials") or [], body.get("objects") or []
    if mats or objs:
        lines += ["## D. Materials and objects", ""]
        for m in mats:
            lines += [f"### {m.get('name')}", ""]
            for key, label in (("properties", "Properties"), ("light_response", "With light"),
                               ("motion_response", "In motion"), ("prompt_line", "Prompt line")):
                lines += _para(label, m.get(key))
        for o in objs:
            lines += [f"### {o.get('name')} ({o.get('role', 'prop')})", ""]
            for key, label in (("meaning", "Meaning"), ("appearance", "Appearance"), ("prompt_line", "Prompt line")):
                lines += _para(label, o.get(key))
    color, light = body.get("color") or {}, body.get("lighting") or {}
    if color or light:
        lines += ["## E. Colour and light", ""]
        if color.get("palette"):
            lines += ["| Colour | Hex | Role |", "|---|---|---|"]
            lines += [f"| {p.get('name')} | `{p.get('hex')}` | {p.get('role', '')} |" for p in color["palette"]]
            lines.append("")
        for key, label in (("relationships", "Relationships"), ("contrast", "Contrast"),
                           ("prompt_line", "Colour line")):
            lines += _para(label, color.get(key))
        for key, label in (("sources", "Light sources"), ("quality", "Quality"), ("shadows", "Shadows"),
                           ("atmosphere", "Atmosphere and depth"), ("prompt_line", "Light line")):
            lines += _para(label, light.get(key))
    lines += _section("F. Cinematic language", body.get("camera"), [
        ("framing", "Framing and composition"), ("distance", "Distance and perspective"), ("lens", "Lens"),
        ("depth_of_field", "Depth of field"), ("movement", "Camera movement"), ("negative_space", "Negative space"),
        ("rhythm", "Visual rhythm"), ("transitions", "Transitions")])
    motifs = body.get("motifs") or []
    if motifs:
        lines += ["## G. Motifs and progression", ""]
        for m in motifs:
            lines += [f"### {m.get('name')}", ""]
            lines += _para("Meaning", m.get("meaning")) + _para("First appears", m.get("first_appearance"))
            if m.get("evolution"):
                lines += ["| Stage | State | Meaning |", "|---|---|---|"]
                lines += [f"| {e.get('stage', '')} | {e.get('state', '')} | {e.get('meaning', '')} |"
                          for e in m["evolution"]]
                lines.append("")
            lines += _para("Payoff", m.get("payoff")) + _para("Prompt line", m.get("prompt_line"))
    lines += _section("H. Motion grammar", body.get("motion"), [
        ("subject", "Subject"), ("figure", "Figure movement"), ("ambient", "Ambient movement"),
        ("allowed", "Allowed"), ("forbidden", "Forbidden"), ("materials", "Material behaviour"),
        ("camera", "Camera movement"), ("invariants", "Continuity invariants")])
    lines += _section("I. Visual constraints", body.get("constraints"), [
        ("required", "Required"), ("forbidden", "Forbidden"), ("negative", "Negative prompt"),
        ("never_change", "Never changes between shots"), ("may_evolve", "May evolve on purpose")])
    return "\n".join(lines).rstrip() + "\n"
