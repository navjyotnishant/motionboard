"""mb art: versions, approval, the plates gate, revisions, impact, Markdown view, export and import (US1)."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from motionboard.cli import app

runner = CliRunner()
FIX = Path(__file__).resolve().parents[1] / "fixtures" / "almost-yours"


def mb(*args):
    return json.loads(runner.invoke(app, [*args, "--json"]).stdout)


@pytest.fixture
def project(mb_home, fixtures_dir, monkeypatch):
    monkeypatch.setenv("MB_BACKEND", "stub")
    pid = mb("project", "new", "--title", "Museum", "--song", str(fixtures_dir / "song10s.wav"),
             "--lyrics-file", str(fixtures_dir / "lyrics.txt"))["project"]
    assert mb("analyze", "-p", pid)["ok"]
    assert mb("draft", "-p", pid, "--mode", "two-lovers", "--look", "origami",
              "--shots-file", str(FIX / "shots.json"))["ok"]
    return pid


def folder(pid):
    return Path(mb("project", "list")["data"]["projects"][0]["folder"]) if pid else None


def test_full_bible_blocks_plates_until_the_creator_approves(project):
    d = mb("art", "draft", "-p", project, "--file", str(FIX / "bible.json"), "--profile", "full")
    assert d["ok"] and d["data"]["version"] == 1 and d["data"]["status"] == "draft"
    assert d["data"]["errors"] == []
    md = folder(project) / "art-direction.md"
    assert md.exists() and "The Museum of Almosts" in md.read_text()
    assert mb("approve", "-p", project, "--stage", "storyboard")["ok"]
    refused = mb("plates", "-p", project)
    assert refused["error"]["code"] == "GATE_NOT_APPROVED" and "art direction" in refused["error"]["message"]
    gate = mb("approve", "-p", project, "--stage", "plates")
    assert any("art direction" in p for p in gate["data"]["problems"])
    assert mb("art", "submit", "-p", project)["data"]["status"] == "in_review"
    ok = mb("approve", "-p", project, "--stage", "art_direction")  # same as mb art approve
    assert ok["ok"] and ok["data"]["status"] == "approved" and ok["data"]["approved_via"] == "chat"
    assert ok["data"]["recomposed"], "prompts follow the approved direction"
    assert mb("plates", "-p", project)["ok"]


def test_compact_or_no_bible_never_blocks(project, tmp_path):
    mb("approve", "-p", project, "--stage", "storyboard")
    compact = tmp_path / "compact.json"
    compact.write_text(json.dumps({"identity": {"concept": "a quiet gallery"}, "world": {"description": "a museum"},
                                   "color": {"prompt_line": "midnight and brass"}}))
    assert mb("art", "draft", "-p", project, "--file", str(compact), "--profile", "compact")["ok"]
    assert mb("plates", "-p", project)["ok"]


def test_revision_never_overwrites_the_approved_version(project):
    mb("art", "draft", "-p", project, "--file", str(FIX / "bible.json"), "--profile", "full")
    mb("art", "approve", "-p", project)
    rev = mb("art", "draft", "-p", project, "--file", str(FIX / "bible-v2.json"), "--note", "HER deeper garnet")
    assert rev["data"]["version"] == 2 and rev["data"]["status"] == "draft" and rev["data"]["profile"] == "full"
    shown = mb("art", "show", "-p", project)["data"]
    assert shown["version"] == 1 and shown["status"] == "approved" and "ruby washi" in json.dumps(shown["body"])
    assert shown["pending"]["version"] == 2
    prompts = mb("shot", "prompts", "-p", project, "--shot", "2")["data"]
    assert "ruby washi" in prompts["plate"] and "garnet" not in prompts["plate"]  # drafts never reach prompts
    md = (folder(project) / "art-direction.md").read_text()
    assert "Pending revision" in md and "garnet" in md
    ok = mb("art", "approve", "-p", project, "--via", "studio")
    assert ok["data"]["version"] == 2 and ok["data"]["superseded"] == 1 and ok["data"]["approved_via"] == "studio"
    hist = {v["version"]: v["status"] for v in mb("art", "history", "-p", project)["data"]["versions"]}
    assert hist == {1: "superseded", 2: "approved"}
    assert "garnet" in mb("shot", "prompts", "-p", project, "--shot", "2")["data"]["plate"]


def test_incomplete_full_bible_cannot_be_submitted_or_approved(project, tmp_path):
    b = json.loads((FIX / "bible.json").read_text())
    del b["motifs"]
    f = tmp_path / "no-motifs.json"
    f.write_text(json.dumps(b))
    d = mb("art", "draft", "-p", project, "--file", str(f), "--profile", "full")
    assert d["ok"] and any("motifs" in e for e in d["data"]["errors"])
    assert mb("art", "submit", "-p", project)["error"]["code"] == "INVALID_INPUT"
    assert mb("art", "approve", "-p", project)["error"]["code"] == "GATE_NOT_APPROVED"


def test_structure_errors_save_nothing(project, tmp_path):
    f = tmp_path / "bad.json"
    f.write_text(json.dumps({"mood": "sad"}))
    out = mb("art", "draft", "-p", project, "--file", str(f))
    assert out["error"]["code"] == "INVALID_INPUT" and "mood" in out["error"]["hint"]
    assert mb("art", "history", "-p", project)["data"]["versions"] == []


def test_reject_needs_a_reason_and_revoke_is_refused(project):
    mb("art", "draft", "-p", project, "--file", str(FIX / "bible.json"), "--profile", "full")
    mb("art", "submit", "-p", project)
    assert mb("art", "reject", "-p", project, "--note", " ")["error"]["code"] == "INVALID_INPUT"
    back = mb("art", "reject", "-p", project, "--note", "the thread needs to start slack")
    assert back["data"]["status"] == "draft" and back["data"]["note"] == "the thread needs to start slack"
    mb("art", "approve", "-p", project)
    assert mb("approve", "-p", project, "--stage", "art_direction", "--revoke")["error"]["code"] == "INVALID_INPUT"


def test_export_and_import_carry_direction_references_creative_and_critiques(project, tmp_path, fixtures_dir):
    mb("art", "draft", "-p", project, "--file", str(FIX / "bible.json"), "--profile", "full")
    mb("art", "approve", "-p", project)
    mb("art", "draft", "-p", project, "--file", str(FIX / "bible-v2.json"))
    mb("character", "ref", "add", "-p", project, "--name", "HER", "--file", str(fixtures_dir / "plates/shot-01.png"),
       "--purpose", "face")
    mb("character", "ref", "add", "-p", project, "--name", "HER", "--file", str(fixtures_dir / "plates/shot-02.png"),
       "--purpose", "silhouette")
    assert mb("critique", "add", "-p", project, "--stage", "plate", "--role", "editor", "--verdict", "revise",
              "--file", str(FIX / "critique-editor.json"))["ok"]
    assert mb("export", "-p", project, "--out", str(tmp_path / "exp"))["ok"]
    new = mb("import", "--file", str(tmp_path / "exp"))["project"]
    hist = {v["version"]: v["status"] for v in mb("art", "history", "-p", new)["data"]["versions"]}
    assert hist == {1: "approved", 2: "draft"}
    refs = mb("character", "ref", "list", "-p", new, "--name", "HER")["data"]["characters"][0]["references"]
    assert [(r["purpose"], r["primary"], r["exists"]) for r in refs] == [("face", True, True),
                                                                         ("silhouette", False, True)]
    states = [m["shots"] for m in mb("art", "motifs", "-p", new)["data"]["motifs"]]
    assert [s["state"] for s in states[0]][-1] == "snapped, the two ends falling apart"
    assert mb("critique", "list", "-p", new, "--shot", "2")["data"]["critiques"][0]["verdict"] == "revise"
