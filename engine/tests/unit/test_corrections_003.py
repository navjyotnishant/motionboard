"""Feature 003 corrective pass (FR-027 to FR-036): materials and objects reach the plates of their own shots, custom
motion prompts cannot slip past the motion grammar unseen, authored prompts survive an art direction approval, a full
Bible designs every storyboard character, and adapters can be told which reference is which.

Real engine, real rows, the Almost Yours Bible. No image or video model runs: nothing here validates a render.
"""

import copy
import json
import sys
import urllib.request
from pathlib import Path

import pytest
from typer.testing import CliRunner

from motionboard.cli import app
from motionboard.db.connection import connect
from motionboard.plates.adapter import PlateRequest, Reference
from motionboard.plates.http_api import HttpAdapter
from motionboard.storyboard import compose, templates

runner = CliRunner()
FIX = Path(__file__).resolve().parents[1] / "fixtures"
AY = FIX / "almost-yours"
WASHI = "translucent washi paper with sharp creases and visible fibres"
CASE = "display case: antique brass frame, smoked glass, a small blank brass label"
BOAT = "paper boat: a small ruby paper boat in an empty case"


def mb(*args):
    return json.loads(runner.invoke(app, [*args, "--json"]).stdout)


def bible(**changes) -> dict:
    b = json.loads((AY / "bible.json").read_text())
    b.update(changes)
    return b


def save(tmp_path, body: dict, name="bible.json") -> str:
    p = tmp_path / name
    p.write_text(json.dumps(body))
    return str(p)


def project(shots_file=None) -> str:
    pid = mb("project", "new", "--title", "Almost Yours", "--song", str(FIX / "song10s.wav"),
             "--lyrics-file", str(FIX / "lyrics.txt"))["project"]
    mb("analyze", "-p", pid)
    assert mb("draft", "-p", pid, "--mode", "two-lovers", "--look", "origami",
              "--shots-file", str(shots_file or AY / "shots.json"))["ok"]
    return pid


def approve_bible(pid, path=None, profile="full"):
    d = mb("art", "draft", "-p", pid, "--file", str(path or AY / "bible.json"), "--profile", profile)
    assert d["ok"] and d["data"]["errors"] == [], d
    out = mb("art", "approve", "-p", pid)
    assert out["ok"], out
    return out


def board(pid, tmp_path, name="b"):
    mb("export", "-p", pid, "--out", str(tmp_path / name), "--no-media")
    return {s["ord"]: s for s in json.loads((tmp_path / name / "project.json").read_text())["shots"]}


def prompts(pid, shot):
    return mb("shot", "prompts", "-p", pid, "--shot", str(shot))


@pytest.fixture
def stub(mb_home, monkeypatch):
    monkeypatch.setenv("MB_BACKEND", "stub")


# --- 1. materials and objects in plate prompts -----------------------------------------------------------------

def test_materials_and_objects_reach_the_plates_of_their_own_shots(stub, tmp_path):
    pid = project()
    assert WASHI not in board(pid, tmp_path, "draft")[2]["plate_prompt"]  # nothing before the Bible is approved
    approve_bible(pid)
    b = board(pid, tmp_path)
    # washi paper: HER is made of it, so it is in her shots and not in the empty gallery
    assert all(WASHI in b[o]["plate_prompt"] for o in (2, 3, 4)) and WASHI not in b[1]["plate_prompt"]
    # the display case: shot 1 names it in the visual, shot 2 lists it; shots 3 and 4 do neither
    assert CASE in b[1]["plate_prompt"] and CASE in b[2]["plate_prompt"]
    assert CASE not in b[3]["plate_prompt"] and CASE not in b[4]["plate_prompt"]
    # an unrelated prop is in no image until a shot selects it
    assert all("paper boat" not in s["plate_prompt"] for s in b.values())
    d = prompts(pid, 2)["data"]
    assert d["materials"] == [{"name": "washi paper", "why": "HER is made of it"}]
    assert d["objects"] == [{"name": "display case", "why": "listed on the shot"}]
    assert prompts(pid, 1)["data"]["objects"] == [{"name": "display case", "why": "named in the visual"}]

    out = mb("shot", "set", "-p", pid, "--shot", "4", "--field", "objects", "--value", "paper boat")
    assert out["ok"] and BOAT in out["data"]["plate_prompt"]
    after = board(pid, tmp_path, "after")
    assert BOAT in after[4]["plate_prompt"] and "paper boat" not in after[3]["plate_prompt"]
    # the object line sits with the shot's content, before the look's style line
    plate = after[4]["plate_prompt"]
    assert plate.index(BOAT) < plate.index("handcrafted origami paper diorama")

    mb("shot", "set", "-p", pid, "--shot", "4", "--field", "objects", "--value", "paper boat, umbrella")
    assert any("object 'umbrella' is listed on the shot but is not in the approved art direction" in v
               for v in prompts(pid, 4)["not_verified"])


def test_scope_all_puts_a_material_in_every_shot_and_duplicates_are_skipped():
    look = templates.get_look("origami")
    body = bible()
    body["materials"][1].update(scope="all", prompt_line="dark smoked glass with soft reflections")
    body["materials"].append({"name": "paper grain", "scope": "all", "prompt_line": "visible paper folds and fibres"})
    p = compose.compose(look, body, visual="an empty corridor", action="dust drifts", camera="locked off",
                        has_figure=False, lip_sync=False, cast=[], creative={})
    assert "dark smoked glass with soft reflections" in p.plate
    assert [m["name"] for m in p.materials] == ["smoked glass", "paper grain"]
    # the look already says "visible paper folds and fibres": the same words are not written twice
    assert p.plate.count("visible paper folds and fibres") == 1
    assert WASHI not in p.plate and "display case:" not in p.plate


def test_impact_of_one_object_or_material_names_only_its_shots(stub, tmp_path):
    pid = project()
    mb("approve", "-p", pid, "--stage", "storyboard")
    approve_bible(pid)
    for o in (1, 2, 3, 4):
        assert mb("plate", "upload", "-p", pid, "--shot", str(o),
                  "--file", str(FIX / "plates" / f"shot-0{o}.png"))["ok"]

    def impact(change) -> tuple[set, dict]:
        body = bible()
        change(body)
        d = mb("art", "draft", "-p", pid, "--file", save(tmp_path, body, "rev.json"), "--note", "one entry")["data"]
        return {s["shot"] for s in d["impact"]["shots"]}, d["impact"]

    shots, imp = impact(lambda b: b["objects"][1].update(appearance="A tiny ruby paper boat with one torn sail."))
    assert shots == set() and imp["objects"] == ["paper boat"], "no shot shows the boat"
    shots, imp = impact(lambda b: b["objects"][0].update(appearance="Antique brass frame, clear glass."))
    assert shots == {1, 2} and imp["objects"] == ["display case"]
    reasons = [r for s in imp["shots"] for r in s["reasons"]]
    assert reasons == ["object 'display case' changed"] * 2
    shots, imp = impact(lambda b: b["materials"][0].update(prompt_line="thick handmade washi paper"))
    assert shots == {2, 3, 4} and imp["materials"] == ["washi paper"]
    shots, _ = impact(lambda b: b["materials"][1].update(properties="Dark and mirror-like."))
    assert shots == set(), "smoked glass belongs to no shot yet"
    shots, _ = impact(lambda b: b["materials"][1].update(scope="all"))
    assert shots == {1, 2, 3, 4}, "scoped to every shot, it touches every shot"


# --- 2. motion grammar and custom prompts ----------------------------------------------------------------------

def test_shots_json_motion_prompt_that_breathes_is_kept_and_reported(stub, tmp_path):
    ideas = json.loads((AY / "shots.json").read_text())
    custom = "HER breathes softly and blinks at the glass, her skirt still"
    ideas["shots"][1]["motion_prompt"] = custom
    f = tmp_path / "shots.json"
    f.write_text(json.dumps(ideas))
    pid = mb("project", "new", "--title", "P", "--song", str(FIX / "song10s.wav"),
             "--lyrics-file", str(FIX / "lyrics.txt"))["project"]
    mb("analyze", "-p", pid)
    d = mb("draft", "-p", pid, "--mode", "two-lovers", "--look", "origami", "--shots-file", str(f))
    assert d["ok"] and d["data"]["authored_prompts"] == ["shot 2 motion"]
    warn = [v for v in d["not_verified"] if v.startswith("shot 2 authored motion prompt asks for")]
    assert warn and "'breathing'" in warn[0] and "'blinking'" in warn[0] and "look origami" in warn[0]
    assert board(pid, tmp_path)[2]["motion_prompt"] == custom, "custom authoring is preserved"

    # the plate workflow shows the conflict before any image is requested
    mb("approve", "-p", pid, "--stage", "storyboard")
    stop = mb("plates", "-p", pid)
    assert not stop["ok"] and stop["error"]["code"] == "DIRECTION_CONFLICT"
    c = stop["data"]["conflicts"]
    assert [(x["shot"], x["part"], x["kind"], x["authored"]) for x in c] == [(2, "motion", "motion_grammar", True)]
    assert mb("plate", "requests", "-p", pid)["data"]["pending"] == []
    go = mb("plates", "-p", pid, "--accept-conflicts")
    assert go["ok"] and len(go["data"]["pending"]) == 4
    assert any("shot 2 authored motion prompt" in v and "accepted for this run" in v for v in go["not_verified"])


def test_cli_motion_prompt_edit_is_checked_and_kept(stub, tmp_path):
    pid = project()
    custom = "she is breathing hard and blinking, hair moving"
    out = mb("shot", "set", "-p", pid, "--shot", "2", "--field", "motion_prompt", "--value", custom)
    assert out["ok"] and out["data"]["motion_prompt"] == custom and out["data"]["authored"]["motion"]
    c = out["data"]["conflicts"]
    assert len(c) == 1 and c[0]["terms"] == ["breathing", "blinking", "hair"] and c[0]["authored"]
    assert any("shot 2 authored motion prompt asks for" in v for v in out["not_verified"])
    assert any("shot 2 authored motion prompt" in v for v in mb("sheet", "-p", pid)["not_verified"])
    # the creator keeps it on purpose: still listed, no longer stops plates
    mb("approve", "-p", pid, "--stage", "storyboard")
    assert mb("plates", "-p", pid)["error"]["code"] == "DIRECTION_CONFLICT"
    kept = mb("shot", "override", "keep", "-p", pid, "--shot", "2", "--part", "motion")
    assert kept["ok"] and kept["data"]["kept"] == ["motion"]
    go = mb("plates", "-p", pid)
    assert go["ok"] and any("kept by the creator" in v for v in go["not_verified"])
    assert board(pid, tmp_path)[2]["motion_prompt"] == custom
    # an action that breaks the grammar is not an override, so nothing can be "kept": it must be fixed or accepted
    mb("shot", "set", "-p", pid, "--shot", "3", "--field", "action", "--value", "they blink at each other")
    stop = mb("plates", "-p", pid, "--shots", "3")
    assert stop["error"]["code"] == "DIRECTION_CONFLICT" and stop["data"]["conflicts"][0]["part"] == "action"


def test_character_rules_join_the_effective_grammar(stub, tmp_path):
    body = bible()
    body["characters"][0]["motion"].update(
        forbidden=["turning the head"], invariants=["the fold across her shoulders stays sharp"],
        materials=["her skirt keeps its triangle"])
    pid = project()
    approve_bible(pid, save(tmp_path, body))
    d = prompts(pid, 2)["data"]
    assert "HER" in d["grammar"]
    assert "turning the head" in d["rules"]["forbidden"] and "breathing" in d["rules"]["forbidden"]
    assert "her skirt keeps its triangle" in d["rules"]["materials"]
    # the washi paper's own behaviour joins the rules of the shots it is in, and is never written into the prompt
    assert "Bends only at folds; edges tremble slightly; never stretches or melts" in d["rules"]["materials"]
    assert "melts" not in d["motion"] and "stretches" not in d["motion"]
    assert "the fold across her shoulders stays sharp" in d["continuity"]["motion"]
    assert "the fold across her shoulders stays sharp" in d["motion"]
    # shot 1 has no HER: her rules do not apply there
    one = prompts(pid, 1)["data"]
    assert "turning the head" not in one["rules"]["forbidden"] and "HER" not in one["grammar"]
    for shot, expect in ((2, True), (1, False)):
        out = mb("shot", "set", "-p", pid, "--shot", str(shot), "--field", "motion_prompt",
                 "--value", "a figure turning the head toward the lamp")
        assert bool(out["data"]["conflicts"]) is expect, (shot, out["data"]["conflicts"])


def test_bible_lines_that_name_forbidden_movement_are_warned(stub, tmp_path):
    body = bible()
    body["motion"]["invariants"] = ["nobody is breathing"]
    pid = project()
    d = mb("art", "draft", "-p", pid, "--file", save(tmp_path, body), "--profile", "full")["data"]
    assert any(w.startswith("motion.invariants: 'nobody is breathing' names breathing") for w in d["warnings"])


# --- 3. authored prompts survive approval ------------------------------------------------------------------------

def test_approval_does_not_erase_authored_prompts(stub, tmp_path):
    pid = project()
    mb("approve", "-p", pid, "--stage", "storyboard")
    approve_bible(pid)
    plate = "HER and HIM under one lamp, an umbrella folded between the cases, my own framing"
    motion = "she turns once at the waist fold, slowly, and stops"
    mb("shot", "set", "-p", pid, "--shot", "3", "--field", "plate_prompt", "--value", plate)
    mb("shot", "set", "-p", pid, "--shot", "2", "--field", "motion_prompt", "--value", motion)
    v2 = json.loads((AY / "bible-v2.json").read_text())
    v2["constraints"]["forbidden"].append("umbrellas")
    assert mb("art", "draft", "-p", pid, "--file", save(tmp_path, v2, "v2.json"), "--note", "garnet")["ok"]
    out = mb("art", "approve", "-p", pid)
    assert out["ok"]

    b = board(pid, tmp_path)
    assert b[3]["plate_prompt"] == plate and b[2]["motion_prompt"] == motion, "authored prompts are untouched"
    assert "garnet" in b[4]["plate_prompt"] and "garnet" in b[2]["plate_prompt"], "generated prompts follow v2"
    over = {(o["shot"], o["part"]): o for o in out["data"]["overrides"]}
    assert set(over) == {(3, "plate"), (2, "motion")}
    assert over[(3, "plate")]["baseline_changed"] and "garnet" in over[(3, "plate")]["generated"]
    assert any("'umbrellas'" in c and "version 2 forbids" in c for c in over[(3, "plate")]["conflicts"])
    assert over[(2, "motion")]["conflicts"] == []
    assert any("shot 3 plate prompt is authored by the creator and was not rewritten" in v and "conflicts" in v
               for v in out["not_verified"])
    assert any("mb shot override keep" in v and "mb shot override clear" in v for v in out["not_verified"])

    d = prompts(pid, 3)["data"]
    assert d["authored"] == {"plate": True, "motion": False} and d["stored"]["plate"] == plate
    assert "garnet" in d["plate"] and d["stored_matches"]["plate"] is False
    listed = mb("shot", "override", "list", "-p", pid)["data"]
    assert [(o["shot"], o["part"], o["kept"]) for o in listed["overrides"]] == [(2, "motion", False),
                                                                                (3, "plate", False)]

    # the conflicting override stops plates until the creator decides
    assert mb("plates", "-p", pid, "--shots", "3")["error"]["code"] == "DIRECTION_CONFLICT"
    # retain
    assert mb("shot", "override", "keep", "-p", pid, "--shot", "3")["data"]["kept"] == ["plate"]
    assert mb("plates", "-p", pid, "--shots", "3")["ok"]
    # revise: still the creator's, and the conflict is gone
    revised = plate.replace("an umbrella folded between the cases, ", "")
    out = mb("shot", "set", "-p", pid, "--shot", "3", "--field", "plate_prompt", "--value", revised)
    assert out["data"]["authored"]["plate"] and out["data"]["conflicts"] == []
    # clear: back to the generated prompt
    cleared = mb("shot", "override", "clear", "-p", pid, "--shot", "3")
    assert cleared["data"]["cleared"] == ["shot 3 plate"]
    d = prompts(pid, 3)["data"]
    assert d["authored"]["plate"] is False and d["stored_matches"]["plate"] is True
    assert board(pid, tmp_path, "end")[2]["motion_prompt"] == motion


def test_an_edit_elsewhere_keeps_the_override_and_moves_only_the_baseline(stub, tmp_path):
    pid = project()
    mine = "my own first frame for shot 2"
    mb("shot", "set", "-p", pid, "--shot", "2", "--field", "plate_prompt", "--value", mine)
    out = mb("shot", "set", "-p", pid, "--shot", "2", "--field", "visual", "--value", "HER alone at the far wall")
    assert out["data"]["plate_prompt"] == mine
    assert any("the plate prompt is authored and was kept as written" in v for v in out["not_verified"])
    d = prompts(pid, 2)["data"]
    assert "HER alone at the far wall" in d["plate"] and d["stored"]["plate"] == mine
    # a character edit recomposes generated prompts and leaves the override alone
    mb("character", "set", "-p", pid, "--name", "HER", "--field", "style_line", "--value", "a red paper woman")
    b = board(pid, tmp_path)
    assert b[2]["plate_prompt"] == mine and "a red paper woman" in b[3]["plate_prompt"]
    # writing the generated text back, or nothing, clears the override
    out = mb("shot", "set", "-p", pid, "--shot", "2", "--field", "plate_prompt", "--value", "")
    assert out["data"]["authored"]["plate"] is False and "a red paper woman" in out["data"]["plate_prompt"]


def test_prompts_from_before_baselines_are_settled_not_erased(stub, tmp_path):
    """A database migrated from schema 3: no baseline yet. A hand-written prompt must survive the next approval."""
    pid = project()
    conn = connect()
    conn.execute("UPDATE shot SET plate_base = NULL, motion_base = NULL, plate_authored = 0, motion_authored = 0")
    conn.execute("UPDATE shot SET motion_prompt = 'written by hand long ago' WHERE ord = 2")
    conn.close()
    out = approve_bible(pid)
    b = board(pid, tmp_path)
    assert b[2]["motion_prompt"] == "written by hand long ago"
    assert {(o["shot"], o["part"]) for o in out["data"]["overrides"]} == {(2, "motion")}
    assert "deep ruby washi paper" in b[2]["plate_prompt"] and "deep ruby washi paper" in b[3]["plate_prompt"]
    assert prompts(pid, 3)["data"]["stored_matches"] == {"plate": True, "motion": True}


# --- 4. full-profile character validation -------------------------------------------------------------------------

def test_full_bible_cannot_be_approved_with_an_undesigned_lead(stub, tmp_path):
    pid = project()
    body = bible()
    body["characters"] = [c for c in body["characters"] if c["name"] != "HIM"]
    d = mb("art", "draft", "-p", pid, "--file", save(tmp_path, body), "--profile", "full")["data"]
    assert d["missing_designs"] == [{"name": "HIM", "shots": [3, 4]}] and d["profile_requires_designs"]
    assert [e for e in d["errors"] if e.startswith("missing character design: HIM appears in shots 3, 4")]
    assert not any("HIM" in w for w in d["warnings"]), "a missing design is an error here, not an advisory"
    stop = mb("art", "submit", "-p", pid)
    assert not stop["ok"] and stop["data"]["missing_designs"][0]["name"] == "HIM"
    stop = mb("art", "approve", "-p", pid)
    assert stop["error"]["code"] == "GATE_NOT_APPROVED" and stop["data"]["missing_designs"]
    assert mb("art", "history", "-p", pid)["data"]["versions"][0]["status"] == "draft"

    # the same gap in a compact Bible stays an advisory
    c = mb("art", "draft", "-p", pid, "--file", save(tmp_path, body), "--profile", "compact")["data"]
    assert c["errors"] == [] and not c["profile_requires_designs"]
    assert any(w.startswith("characters: HIM appears in shots 3, 4 but has no design") for w in c["warnings"])

    # an exception needs a reason, and with one the full Bible can be approved
    body["exceptions"] = {"characters": [{"name": "HIM"}]}
    bad = mb("art", "draft", "-p", pid, "--file", save(tmp_path, body), "--profile", "full")
    assert not bad["ok"] and "exceptions.characters[0].reason: required" in bad["error"]["hint"]
    body["exceptions"] = {"characters": [{"name": "HIM", "reason": "seen only as a shadow; no design wanted"}]}
    ok = mb("art", "draft", "-p", pid, "--file", save(tmp_path, body), "--profile", "full")["data"]
    assert ok["errors"] == [] and ok["missing_designs"] == []
    assert ok["design_exceptions"] == [{"name": "HIM", "reason": "seen only as a shadow; no design wanted"}]
    assert any("HIM appears in shots 3, 4 without a design, as recorded" in w for w in ok["warnings"])
    assert mb("art", "approve", "-p", pid)["ok"]
    assert "Recorded exceptions" in mb("art", "show", "-p", pid, "--markdown")["data"]["markdown"]


def test_a_character_added_after_approval_is_caught_before_plates(stub):
    pid = project()
    mb("approve", "-p", pid, "--stage", "storyboard")
    approve_bible(pid)
    assert mb("character", "add", "-p", pid, "--name", "GUARD")["ok"]
    assert mb("character", "link", "-p", pid, "--name", "GUARD", "--shots", "2")["ok"]
    stop = mb("plates", "-p", pid, "--shots", "2")
    c = stop["data"]["conflicts"]
    assert stop["error"]["code"] == "DIRECTION_CONFLICT" and c[0]["kind"] == "undesigned_character"
    assert c[0]["message"] == "shot 2 shows GUARD, who has no design in art direction version 1"
    errors = mb("art", "check", "-p", pid)["data"]["errors"]
    assert any(e.startswith("missing character design: GUARD") for e in errors)


# --- 5. reference identity in adapter requests --------------------------------------------------------------------

@pytest.fixture
def with_refs(stub):
    pid = project()
    for name, a, b in (("HER", "shot-01.png", "shot-02.png"), ("HIM", "shot-03.png", "shot-04.png")):
        mb("character", "ref", "add", "-p", pid, "--name", name, "--file", str(FIX / "plates" / a), "--purpose", "face")
        mb("character", "ref", "add", "-p", pid, "--name", name, "--file", str(FIX / "plates" / b),
           "--purpose", "silhouette", "--description", "full figure")
    mb("approve", "-p", pid, "--stage", "storyboard")
    return pid


def test_command_adapter_gets_a_manifest_and_labelled_references(with_refs, tmp_path):
    log = tmp_path / "seen.json"
    script = ("import sys, json, shutil; m = json.load(open(sys.argv[2])); "
              "json.dump(dict(argv=sys.argv[3:], manifest=m, inline=json.loads(sys.argv[-1])), "
              f"open({str(log)!r}, 'w')); shutil.copy(m['references'][0]['path'], sys.argv[1])")
    cfg = {"cmd": [sys.executable, "-c", script, "{out}", "{refs_manifest}", "{refs}", "{refs_json}"],
           "refs_format": "{character}:{purpose}:{primary}={path}"}
    assert mb("adapter", "--add", "tagged", "--kind", "command", "--config", json.dumps(cfg))["ok"]
    listing = {a["name"]: a for a in mb("adapter", "--list")["data"]["adapters"]}
    assert listing["tagged"]["reference_capacity"] == "unlimited"
    out = mb("plates", "-p", with_refs, "--adapter", "tagged", "--shots", "3")
    assert out["data"].get("done"), out
    seen = json.loads(log.read_text())
    refs = seen["manifest"]["references"]
    assert seen["manifest"]["shot"] == 3 and seen["manifest"]["request"]
    assert [(r["index"], r["character"], r["purpose"], r["primary"]) for r in refs] == [
        (0, "HER", "face", True), (1, "HER", "silhouette", False), (2, "HIM", "face", True),
        (3, "HIM", "silhouette", False)]
    assert refs[1]["description"] == "full figure" and all(Path(r["path"]).is_file() for r in refs)
    assert len({r["path"] for r in refs}) == 4, "each of the four images is its own file"
    assert seen["argv"][:4] == [f"{r['character']}:{r['purpose']}:{r['primary']}={r['path']}" for r in refs]
    assert seen["inline"] == refs


def test_http_adapter_maps_reference_metadata_to_the_api_fields(tmp_path, monkeypatch):
    sent = {}

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps({"data": [{"b64_json": "aGVsbG8="}]}).encode()

    def fake(req, timeout=0):
        sent["body"] = json.loads(req.data)
        return Resp()

    monkeypatch.setattr(urllib.request, "urlopen", fake)
    p = FIX / "plates"
    refs = [Reference("HER", p / "shot-01.png", "face", True), Reference("HER", p / "shot-02.png", "silhouette"),
            Reference("HIM", p / "shot-03.png", "face", True), Reference("HIM", p / "shot-04.png", "silhouette")]
    base = {"url": "http://x", "body": {"prompt": "{prompt}"}, "refs_field": "input.references"}
    req = PlateRequest("r", "s", 3, "two figures", "", 8, 8, tmp_path / "o.png", references=refs)

    HttpAdapter("h", {**base, "refs_meta": {"image": "image", "subject": "character", "role": "purpose",
                                            "main": "primary"}}, 0).request(req)
    got = sent["body"]["input"]["references"]
    assert [(g["subject"], g["role"], g["main"]) for g in got] == [
        ("HER", "face", True), ("HER", "silhouette", False), ("HIM", "face", True), ("HIM", "silhouette", False)]
    assert all(isinstance(g["image"], str) and len(g["image"]) > 20 for g in got)
    assert len({g["image"] for g in got}) == 4

    HttpAdapter("h", {**base, "refs_encoding": "path", "refs_manifest_field": "input.reference_info"}, 0).request(req)
    body = sent["body"]["input"]
    assert body["references"] == [str(r.path) for r in refs], "without refs_meta the list of images is unchanged"
    assert [(m["index"], m["character"], m["purpose"], m["primary"], m["path"]) for m in body["reference_info"]] == [
        (i, r.character, r.purpose, r.primary, str(r.path)) for i, r in enumerate(refs)]

    plain = copy.deepcopy(base)
    HttpAdapter("h", plain, 0).request(req)
    assert len(sent["body"]["input"]["references"]) == 4 and "reference_info" not in sent["body"]["input"]


def test_reference_metadata_settings_are_checked_when_the_adapter_is_added(stub):
    def add(kind, cfg):
        return mb("adapter", "--add", "x", "--kind", kind, "--config", json.dumps(cfg))

    assert not add("http", {"url": "http://x", "refs_field": "a", "refs_meta": {"who": "name"}})["ok"]
    assert not add("http", {"url": "http://x", "refs_meta": {"who": "character"}})["ok"]
    assert not add("command", {"cmd": ["x", "{out}", "{refs}"], "refs_format": "{nope}"})["ok"]
    assert not add("command", {"cmd": ["x", "{out}"], "refs_format": "{path}"})["ok"]
    assert add("command", {"cmd": ["x", "{out}", "{refs}"], "refs_format": "--ref={character}/{purpose}:{path}"})["ok"]


def test_reference_manifest_field_needs_refs_field(stub):
    """The manifest labels the images at refs_field, so it is refused without one (review finding, P3)."""
    made = []

    def add(kind, cfg):
        made.append(kind)
        return mb("adapter", "--add", f"a{len(made)}", "--kind", kind, "--config", json.dumps(cfg))

    url = {"url": "http://x", "body": {"prompt": "{prompt}"}}
    bad = add("http", {**url, "refs_manifest_field": "input.reference_info"})
    assert not bad["ok"] and bad["error"]["code"] == "INVALID_INPUT" and "refs_field" in bad["error"]["hint"]
    assert not add("http", {**url, "refs_field": "", "refs_manifest_field": "input.reference_info"})["ok"]
    assert not add("http", {**url, "refs_field": "input.images", "refs_manifest_field": ""})["ok"]
    assert not add("command", {"cmd": ["x", "{out}", "{refs}"], "refs_manifest_field": "a.b"})["ok"]
    # valid: manifest beside refs_field, with or without the object mapping
    assert add("http", {**url, "refs_field": "input.images", "refs_manifest_field": "input.reference_info"})["ok"]
    assert add("http", {**url, "refs_field": "input.images", "refs_manifest_field": "input.reference_info",
                        "refs_meta": {"image": "image", "subject": "character"}})["ok"]
    # configurations from before reference metadata existed are untouched
    assert add("http", {**url, "refs_field": "input.images", "refs_encoding": "data_url"})["ok"]
    assert add("http", {"url": "http://x", "body": {"prompt": "{prompt}", "image": "{ref_b64}"}})["ok"]
    assert add("http", url)["ok"]


# --- export and import keep the creator's decisions ----------------------------------------------------------------

def test_export_import_keeps_an_authored_prompt_and_its_keep_decision(stub, tmp_path):
    pid = project()
    approve_bible(pid)
    motion = "she turns once at the waist fold, slowly, and is breathing"
    mb("shot", "set", "-p", pid, "--shot", "2", "--field", "motion_prompt", "--value", motion)
    assert mb("shot", "override", "keep", "-p", pid, "--shot", "2", "--part", "motion")["data"] == {
        "shot": 2, "kept": ["motion"], "art_direction_version": 1}

    assert mb("export", "-p", pid, "--out", str(tmp_path / "exp"), "--no-media")["ok"]
    doc = json.loads((tmp_path / "exp" / "project.json").read_text())
    two = next(s for s in doc["shots"] if s["ord"] == 2)
    assert two["override_kept"] == {"motion": 1} and two["motion_authored"] and two["motion_prompt"] == motion
    assert all(s["override_kept"] == {} for s in doc["shots"] if s["ord"] != 2)

    new = mb("import", "--file", str(tmp_path / "exp" / "project.json"))
    assert new["ok"] and new["project"] != pid
    npid = new["project"]
    listed = mb("shot", "override", "list", "-p", npid)["data"]
    assert listed["art_direction_version"] == 1
    assert [(o["shot"], o["part"], o["text"], o["kept"]) for o in listed["overrides"]] == [(2, "motion", motion, True)]
    assert listed["overrides"][0]["conflicts"], "still reported, as a kept conflict"
    # the decision travels: the kept override does not stop plates in the imported project either
    mb("approve", "-p", npid, "--stage", "storyboard")
    go = mb("plates", "-p", npid, "--shots", "2")
    assert go["ok"] and any("kept by the creator" in v for v in go["not_verified"])

    # a newer art direction version asks again: the decision was for version 1 only
    assert mb("art", "draft", "-p", npid, "--file", str(AY / "bible-v2.json"), "--note", "garnet")["ok"]
    out = mb("art", "approve", "-p", npid)
    assert out["ok"] and out["data"]["version"] == 2
    over = out["data"]["overrides"]
    assert [(o["shot"], o["part"], o["text"], o["kept"]) for o in over] == [(2, "motion", motion, False)]
    assert mb("plates", "-p", npid, "--shots", "2")["error"]["code"] == "DIRECTION_CONFLICT"
    # the stored decision is still the old one; a second round trip carries it unchanged and still not in force
    assert mb("export", "-p", npid, "--out", str(tmp_path / "exp2"), "--no-media")["ok"]
    two = next(s for s in json.loads((tmp_path / "exp2" / "project.json").read_text())["shots"] if s["ord"] == 2)
    assert two["override_kept"] == {"motion": 1}
    again = mb("import", "--file", str(tmp_path / "exp2" / "project.json"))["project"]
    assert mb("shot", "override", "list", "-p", again)["data"]["overrides"][0]["kept"] is False


def test_import_tolerates_exports_without_or_with_bad_keep_decisions(stub, tmp_path):
    pid = project()
    mb("export", "-p", pid, "--out", str(tmp_path / "exp"), "--no-media")
    f = tmp_path / "exp" / "project.json"
    doc = json.loads(f.read_text())
    doc["shots"][0].pop("override_kept")  # an export from before the field existed
    doc["shots"][1]["override_kept"] = {"motion": "yes", "plate": 3, "other": 1}
    doc["shots"][2]["override_kept"] = "not json"
    f.write_text(json.dumps(doc))
    new = mb("import", "--file", str(f))
    assert new["ok"], new
    conn = connect()
    kept = [json.loads(r["override_kept"]) for r in conn.execute(
        "SELECT override_kept FROM shot WHERE project_id = ? ORDER BY ord", (new["project"],))]
    conn.close()
    assert kept == [{}, {"plate": 3}, {}, {}]
