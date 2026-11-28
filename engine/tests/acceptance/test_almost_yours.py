"""Feature 003 acceptance: Almost Yours, The Museum of Almosts (brief section 12, requirements 1 to 14).

Runs the real engine on real rows: a project from the fixture song with the two-lovers mode and origami look, HER
and HIM linked to shots, two references each, the Museum of Almosts Bible, plate requests through real adapters,
uploaded plates, a revision and an editor's review. Stub video backend only: no image or video model runs, so
nothing here is a visual validation of a render.
"""

import json
import re
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from motionboard.cli import app
from motionboard.storyboard import templates

runner = CliRunner()
FIX = Path(__file__).resolve().parents[1] / "fixtures"
AY = FIX / "almost-yours"
REPO = Path(__file__).resolve().parents[3]
HUMAN_MOTION = re.compile(r"breath|blink|\bhair\b|fabric|skin", re.I)


def mb(*args):
    out = runner.invoke(app, [*args, "--json"]).stdout
    return json.loads(out)


@pytest.fixture
def museum(mb_home, monkeypatch):
    monkeypatch.setenv("MB_BACKEND", "stub")
    pid = mb("project", "new", "--title", "Almost Yours", "--song", str(FIX / "song10s.wav"),
             "--lyrics-file", str(FIX / "lyrics.txt"), "--idea", "The Museum of Almosts")["project"]
    assert mb("analyze", "-p", pid)["ok"]
    assert mb("draft", "-p", pid, "--mode", "two-lovers", "--look", "origami",
              "--shots-file", str(AY / "shots.json"))["ok"]
    for name, face, silhouette in (("HER", "shot-01.png", "shot-02.png"), ("HIM", "shot-03.png", "shot-04.png")):
        assert mb("character", "ref", "add", "-p", pid, "--name", name, "--file", str(FIX / "plates" / face),
                  "--purpose", "face")["ok"]
        assert mb("character", "ref", "add", "-p", pid, "--name", name, "--file", str(FIX / "plates" / silhouette),
                  "--purpose", "silhouette")["ok"]
    return pid


def shots(pid, tmp_path, name="b"):
    mb("export", "-p", pid, "--out", str(tmp_path / name), "--no-media")
    return {s["ord"]: s for s in json.loads((tmp_path / name / "project.json").read_text())["shots"]}


def test_almost_yours_acceptance(museum, tmp_path):
    pid = museum
    bible = json.loads((AY / "bible.json").read_text())

    # 1. The production designer's complete Bible saves with no gaps for a full profile.
    d = mb("art", "draft", "-p", pid, "--file", str(AY / "bible.json"), "--profile", "full",
           "--note", "the museum, the two figures, the ruby thread")
    assert d["ok"] and d["data"]["errors"] == [] and d["data"]["warnings"] == []

    # 2. It explains why origami is right for this song.
    song = bible["identity"]["song_relationship"]
    assert "Paper suits that" in song and "fold" in song and bible["identity"]["central_metaphor"].startswith("Origami")

    # 13. The creator keeps final approval: drafting and submitting approve nothing, plates wait.
    mb("approve", "-p", pid, "--stage", "storyboard")
    assert mb("art", "submit", "-p", pid)["data"]["status"] == "in_review"
    assert mb("plates", "-p", pid)["error"]["code"] == "GATE_NOT_APPROVED"
    approved = mb("art", "approve", "-p", pid, "--via", "studio")
    assert approved["data"]["status"] == "approved" and approved["data"]["approved_via"] == "studio"

    b = shots(pid, tmp_path)
    figure_shots = [s for s in b.values() if s["has_figure"]]

    # 3. HER and HIM are distinct, reusable designs: the same Bible line in every shot each one is in.
    her_line, him_line = (c["prompt_line"] for c in bible["characters"])
    assert her_line != him_line
    for s in b.values():
        assert (her_line in s["plate_prompt"]) == ("HER" in s["characters"])
        assert (him_line in s["plate_prompt"]) == ("HIM" in s["characters"])

    # 4. One visual universe: world, colour and light lines in every plate; camera and motion rules in the Bible.
    for s in b.values():
        for line in (bible["world"]["prompt_line"], bible["color"]["prompt_line"], bible["lighting"]["prompt_line"]):
            assert line in s["plate_prompt"], (s["ord"], line)
    assert bible["camera"]["movement"] and bible["motion"]["forbidden"] and bible["constraints"]["never_change"]

    # 10. The cinematographer inherits the approved direction: stored prompts are the composed ones.
    for o in b:
        p = mb("shot", "prompts", "-p", pid, "--shot", str(o))["data"]
        assert p["stored_matches"] == {"plate": True, "motion": True}
        assert "photorealistic people, skin, text" in p["negative"]

    # 8. Origami motion: no breathing, blinking or human movement anywhere; paper behaviour instead.
    for s in b.values():
        assert not HUMAN_MOTION.search(s["motion_prompt"]), (s["ord"], s["motion_prompt"])
        assert len(s["motion_prompt"].split()) <= 200
    for s in figure_shots:
        assert "precise pivots at the folds" in s["motion_prompt"]

    # 9. The ruby thread's meaning progresses shot by shot, in the Bible's order, and reaches the plates.
    states = [x["state"] for x in mb("art", "motifs", "-p", pid)["data"]["motifs"][0]["shots"]]
    evolution = [e["state"] for e in bible["motifs"][0]["evolution"]]
    assert states[0] == "slack across the dark floor between two cases" and states[1:] == evolution[1:]
    for o, s in b.items():
        assert f"a thin luminous ruby-red thread, {states[o - 1]}" in s["plate_prompt"]

    # 5 and 6. A shot with HER and HIM carries both characters' references, two each.
    assert mb("adapter", "--add", "muse", "--kind", "handoff")["ok"]
    assert mb("plates", "-p", pid, "--adapter", "muse")["ok"]
    reqs = {r["shot"]: r for r in mb("plate", "requests", "-p", pid)["data"]["pending"]}
    both = [(r["character"], r["purpose"]) for r in reqs[3]["references"]]
    assert both == [("HER", "face"), ("HER", "silhouette"), ("HIM", "face"), ("HIM", "silhouette")]

    # 7. An adapter that takes one reference never drops the rest silently.
    cmd = [sys.executable, "-c", "import sys, shutil; shutil.copy(sys.argv[2], sys.argv[1])", "{out}", "{ref}"]
    mb("adapter", "--add", "one", "--kind", "command", "--config", json.dumps({"cmd": cmd}))
    strict = mb("plates", "-p", pid, "--adapter", "one", "--shots", "3")
    assert strict["data"]["failed"] and not strict["data"]["done"]
    first = mb("plates", "-p", pid, "--adapter", "one", "--shots", "3", "--reference-strategy", "first")
    assert len(first["data"]["done"][0]["references_dropped"]) == 3

    # 11. A revision to HER's palette names exactly HER's shots and their plates, and regenerates nothing.
    for o in b:
        mb("plate", "upload", "-p", pid, "--shot", str(o), "--file", str(FIX / "plates" / f"shot-0{o}.png"))
    before = shots(pid, tmp_path, "before")
    rev = mb("art", "draft", "-p", pid, "--file", str(AY / "bible-v2.json"), "--note", "HER deeper garnet")
    preview = {s["shot"] for s in rev["data"]["impact"]["shots"]}
    her_shots = {o for o, s in b.items() if "HER" in s["characters"]}
    assert preview == her_shots and 1 not in preview
    approved2 = mb("art", "approve", "-p", pid)
    impact = approved2["data"]["impact"]
    assert {s["shot"] for s in impact["shots"]} == her_shots
    assert all(a["kind"] == "plate" for s in impact["shots"] for a in s["assets"])
    after = shots(pid, tmp_path, "after")
    for o in b:
        assert after[o]["state"] == before[o]["state"], "approval never re-states or regenerates assets"
        assert [a["path"] for a in after[o]["assets"]] == [a["path"] for a in before[o]["assets"]]
    assert "garnet" in after[2]["plate_prompt"] and "garnet" not in after[1]["plate_prompt"]

    # 12. The editor can flag a beautiful shot that does not serve the story; it stays open on that shot.
    assert mb("critique", "add", "-p", pid, "--stage", "plate", "--role", "editor", "--verdict", "revise",
              "--file", str(AY / "critique-editor.json"))["ok"]
    flagged = mb("critique", "list", "-p", pid, "--shot", "2", "--open")["data"]["critiques"]
    assert flagged and "gorgeous" in flagged[0]["findings"][0]["observation"]
    for o in b:
        mb("review", "-p", pid, "--shot", str(o), "--kind", "plate", "--decision", "approve")
    gate = mb("approve", "-p", pid, "--stage", "plates")
    assert gate["ok"] and any("open revise review by the editor (plate) on shots 2" in v for v in gate["not_verified"])

    md = (Path(mb("project", "list")["data"]["projects"][0]["folder"]) / "art-direction.md").read_text()
    assert "Version 2 · approved" in md and "garnet" in md


def test_existing_modes_looks_packs_and_old_exports_still_work(mb_home, monkeypatch, tmp_path):
    """14. Nothing that worked before 003 stops working."""
    monkeypatch.setenv("MB_BACKEND", "stub")
    modes = templates.list_modes()
    for m in modes:
        assert (REPO / "modes" / m.slug / "animation").is_dir(), m.slug
    looks = templates.list_looks()
    assert len(looks) >= 6 and all(lk.style_line for lk in looks)
    old = mb("import", "--file", str(FIX / "export80.json"))
    assert old["ok"]
    assert mb("art", "history", "-p", old["project"])["data"]["versions"] == []
    pid = mb("project", "new", "--title", "Neon", "--song", str(FIX / "song10s.wav"),
             "--lyrics-file", str(FIX / "lyrics.txt"))["project"]
    mb("analyze", "-p", pid)
    assert mb("draft", "-p", pid, "--mode", "studio-session", "--look", "neon-night")["ok"]
    mb("approve", "-p", pid, "--stage", "storyboard")
    assert mb("plates", "-p", pid)["ok"], "no Bible: plates are not gated"
    people = [s for s in shots(pid, tmp_path).values() if s["has_figure"]]
    assert people and all("steady breathing, soft blinking" in s["motion_prompt"] for s in people)
