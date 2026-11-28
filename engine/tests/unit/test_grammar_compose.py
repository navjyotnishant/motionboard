"""Motion grammar, the three prompt parts, shot creative context and critiques (US3, US5)."""

import json
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from motionboard.cli import app
from motionboard.direction import grammar
from motionboard.storyboard import templates
from motionboard.storyboard.draft import motion_prompt

runner = CliRunner()
FIX = Path(__file__).resolve().parents[1] / "fixtures" / "almost-yours"
HUMAN = re.compile(r"breath|blink|hair|fabric|skin", re.I)


def mb(*args):
    return json.loads(runner.invoke(app, [*args, "--json"]).stdout)


def new_project(fixtures_dir, look="origami", shots_file=True):
    pid = mb("project", "new", "--title", "Paper", "--song", str(fixtures_dir / "song10s.wav"),
             "--lyrics-file", str(fixtures_dir / "lyrics.txt"))["project"]
    mb("analyze", "-p", pid)
    args = ["draft", "-p", pid, "--mode", "two-lovers", "--look", look]
    if shots_file:
        args += ["--shots-file", str(FIX / "shots.json")]
    assert mb(*args)["ok"]
    return pid


def board(pid, tmp_path):
    mb("export", "-p", pid, "--out", str(tmp_path / "b"), "--no-media")
    return {s["ord"]: s for s in json.loads((tmp_path / "b/project.json").read_text())["shots"]}


@pytest.fixture
def stub(mb_home, monkeypatch):
    monkeypatch.setenv("MB_BACKEND", "stub")


def test_every_builtin_look_and_mode_still_loads():
    looks = {lk.slug: lk for lk in templates.list_looks()}
    assert {"origami", "after-dark", "cosmic", "exotic", "neon-night", "vintage-film"} <= set(looks)
    assert looks["origami"].grammar.source == "look origami"
    assert looks["neon-night"].grammar is grammar.DEFAULT
    assert {m.slug for m in templates.list_modes()} >= {"two-lovers", "lyric-story", "mood-loop", "travel",
                                                       "studio-session"}


def test_origami_motion_prompts_have_no_human_motion(stub, fixtures_dir, tmp_path):
    pid = new_project(fixtures_dir, shots_file=False)
    b = board(pid, tmp_path)
    figure_shots = [s for s in b.values() if s["has_figure"]]
    assert figure_shots
    for s in b.values():
        assert not HUMAN.search(s["motion_prompt"]), (s["ord"], s["motion_prompt"])
        assert len(s["motion_prompt"].split()) <= 200
    for s in figure_shots:
        assert "precise pivots at the folds" in s["motion_prompt"]
        assert "each paper figure keeps the same folds, colour and proportions" in s["motion_prompt"]


def test_looks_without_a_grammar_keep_the_old_motion_text():
    neon = templates.get_look("neon-night")
    p = motion_prompt("he turns", "close-up", True, neon)
    assert ("The movement is slow, natural and continuous, with small lifelike details: steady breathing, soft "
            "blinking, hair and fabric shifting slightly, no sudden jumps.") in p
    assert "each person keeps the same face, hair and clothes from the first frame to the last" in p


def test_forbidden_movement_in_an_action_is_warned(stub, fixtures_dir):
    pid = new_project(fixtures_dir)
    mb("shot", "set", "-p", pid, "--shot", "2", "--field", "action", "--value", "she breathes slowly and blinks")
    sheet = mb("sheet", "-p", pid)
    warn = [v for v in sheet["not_verified"] if v.startswith("shot 2 action asks for")]
    assert warn and "breathing" in warn[0] and "blinking" in warn[0]
    prompts = mb("shot", "prompts", "-p", pid, "--shot", "2")
    assert any("breathing" in w for w in prompts["not_verified"])


def test_approved_direction_reaches_all_three_parts(stub, fixtures_dir):
    pid = new_project(fixtures_dir)
    mb("art", "draft", "-p", pid, "--file", str(FIX / "bible.json"), "--profile", "full")
    before = mb("shot", "prompts", "-p", pid, "--shot", "3")["data"]
    assert "ruby washi" not in before["plate"]  # a draft never reaches prompts
    mb("art", "approve", "-p", pid)
    d = mb("shot", "prompts", "-p", pid, "--shot", "3")["data"]
    plate, motion = d["plate"], d["motion"]
    # cast from the Bible's prompt lines (they win over style lines), both characters
    assert "deep ruby washi paper" in plate and "charcoal grey heavyweight paper" in plate
    # the motif's look and this shot's state
    assert "a thin luminous ruby-red thread, the two ends almost touching between the cases" in plate
    # the world, colour and light lines
    assert "midnight museum gallery" in plate and "warm amber practical lamps" in plate
    # continuity: Bible never-change rules and the shot's own requirement, in plate and motion
    assert d["continuity"]["plate"] == ["HER is deep ruby paper and HIM charcoal grey paper",
                                        "the figures have no drawn faces",
                                        "HIM stays turned slightly away even while reaching"]
    assert "Keep consistent with the rest of the film: HER is deep ruby paper" in plate
    assert "Throughout the shot: the cases stay closed; HER is deep ruby paper" in motion
    # motion from the Bible's grammar (allowed list) and HER's own movement; no human motion
    assert "Movement: precise pivots at the folds" in motion
    assert "HER moves with a slow turn at the waist fold" in motion
    assert not HUMAN.search(motion) and len(motion.split()) <= 200
    assert "photorealistic people, skin, text" in d["negative"] and "daylight" in d["negative"]
    assert d["stored_matches"] == {"plate": True, "motion": True}  # approval recomposed the stored prompts


def test_creative_context_is_optional_and_only_motifs_and_continuity_touch_prompts(stub, fixtures_dir, tmp_path):
    pid = new_project(fixtures_dir, shots_file=False)
    b = board(pid, tmp_path)
    assert all(s["creative"] == {} for s in b.values())
    before = b[2]
    out = mb("shot", "set", "-p", pid, "--shot", "2", "--field", "intent", "--value", "she notices him")
    assert out["data"]["plate_prompt"] == before["plate_prompt"]
    out = mb("shot", "set", "-p", pid, "--shot", "2", "--field", "motifs", "--value", "ruby thread: taut toward HIM")
    assert "ruby thread, taut toward HIM" in out["data"]["plate_prompt"]
    assert mb("shot", "set", "-p", pid, "--shot", "2", "--field", "motifs",
              "--value", '[{"state": "x"}]')["error"]["code"] == "INVALID_INPUT"
    after = board(pid, tmp_path)[2]["creative"]
    assert after == {"intent": "she notices him", "motifs": [{"name": "ruby thread", "state": "taut toward HIM"}]}
    progress = mb("art", "motifs", "-p", pid)["data"]["motifs"]
    assert progress == [{"name": "ruby thread", "meaning": "", "payoff": "", "shots": [
        {"shot": 2, "state": "taut toward HIM"}]}]


def test_motif_state_change_marks_a_finished_plate_for_redo(stub, fixtures_dir):
    pid = new_project(fixtures_dir)
    mb("approve", "-p", pid, "--stage", "storyboard")
    mb("plate", "upload", "-p", pid, "--shot", "2", "--file", str(fixtures_dir / "plates/shot-02.png"))
    mb("review", "-p", pid, "--shot", "2", "--kind", "plate", "--decision", "approve")
    mb("shot", "set", "-p", pid, "--shot", "2", "--field", "metaphor", "--value", "leaning on her own glass")
    assert mb("shot", "prompts", "-p", pid, "--shot", "2")["data"]["creative"]["metaphor"]
    s = mb("shot", "set", "-p", pid, "--shot", "2", "--field", "motifs", "--value", "ruby thread: slack")
    assert s["data"]["shot"]["state"] == "needs_redo"


def test_critiques_need_four_parts_and_show_on_approval(stub, fixtures_dir, tmp_path):
    pid = new_project(fixtures_dir)
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"findings": [{"observation": "pretty", "shots": [2]}]}))
    out = mb("critique", "add", "-p", pid, "--stage", "concept", "--role", "director", "--verdict", "revise",
             "--file", str(bad))
    assert out["error"]["code"] == "INVALID_INPUT" and "audience_impact" in out["error"]["message"]
    nine = tmp_path / "nine.json"
    nine.write_text(json.dumps({"findings": [{"observation": "a", "audience_impact": "b", "implication": "c",
                                              "recommendation": "d", "shots": [9]}]}))
    assert mb("critique", "add", "-p", pid, "--stage", "concept", "--role", "director", "--verdict", "revise",
              "--file", str(nine))["error"]["code"] == "INVALID_INPUT"
    ok = mb("critique", "add", "-p", pid, "--stage", "concept", "--role", "emotion_editor", "--verdict", "revise",
            "--file", str(FIX / "critique-editor.json"))
    assert ok["ok"] and ok["not_verified"] == ["not checked: motion: no clips rendered yet"]
    approved = mb("approve", "-p", pid, "--stage", "storyboard")
    assert approved["ok"], "reviews never block approval"
    assert any("open revise review by the emotion editor (concept) on shots 2" in v for v in approved["not_verified"])
    cid = ok["data"]["critique"]["id"]
    mb("critique", "resolve", "-p", pid, "--id", cid)
    assert mb("critique", "list", "-p", pid, "--open")["data"]["critiques"] == []
