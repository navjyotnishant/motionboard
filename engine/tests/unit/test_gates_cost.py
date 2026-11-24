"""Clips refused before gates; paid adapters refused without a confirmed cost (T051)."""

import json
import shutil

import pytest
from typer.testing import CliRunner

from motionboard.cli import app

runner = CliRunner()


def mb(*args):
    return json.loads(runner.invoke(app, [*args, "--json"]).stdout)


@pytest.fixture
def project(mb_home, fixtures_dir, monkeypatch):
    monkeypatch.setenv("MB_BACKEND", "stub")
    pid = mb("project", "new", "--title", "Gates", "--song", str(fixtures_dir / "song10s.wav"),
             "--lyrics-file", str(fixtures_dir / "lyrics.txt"))["project"]
    assert mb("analyze", "-p", pid)["ok"]
    assert mb("draft", "-p", pid, "--mode", "two-lovers", "--look", "origami")["ok"]
    return pid


def test_plates_need_storyboard_gate(project):
    out = mb("plates", "-p", project)
    assert out["error"]["code"] == "GATE_NOT_APPROVED"


def test_clips_need_both_gates(project):
    assert mb("clips", "-p", project)["error"]["code"] == "GATE_NOT_APPROVED"
    mb("approve", "-p", project, "--stage", "storyboard")
    assert mb("clips", "-p", project)["error"]["code"] == "GATE_NOT_APPROVED"


def test_paid_adapter_refused_without_confirm_and_sends_nothing(project):
    mb("approve", "-p", project, "--stage", "storyboard")
    cfg = json.dumps({"url": "http://127.0.0.1:9/never-called", "key_env": "MB_TEST_KEY"})
    assert mb("adapter", "--add", "paid", "--kind", "http", "--config", cfg, "--cost", "0.01")["ok"]
    out = mb("plates", "-p", project, "--adapter", "paid")
    assert out["error"]["code"] == "COST_NOT_CONFIRMED"
    assert out["data"]["est_cost_usd"] == pytest.approx(0.04)
    assert mb("plate", "requests", "-p", project)["data"]["pending"] == []


def test_adapter_refuses_inline_keys(mb_home):
    cfg = json.dumps({"url": "https://x", "api_key": "sk-" + "a" * 40})
    out = mb("adapter", "--add", "bad", "--kind", "http", "--config", cfg)
    assert not out["ok"]
    assert "sk-aaaa" not in json.dumps(out)


def test_handoff_requests_and_fulfil(project, fixtures_dir, tmp_path):
    mb("approve", "-p", project, "--stage", "storyboard")
    assert mb("adapter", "--add", "muse", "--kind", "handoff", "--config", '{"hint": "Muse"}')["ok"]
    out = mb("plates", "-p", project, "--adapter", "muse")
    assert len(out["data"]["pending"]) == 4
    reqs = mb("plate", "requests", "-p", project)["data"]["pending"]
    img = tmp_path / "p.png"
    shutil.copy(fixtures_dir / "plates" / "shot-01.png", img)
    assert mb("plate", "fulfil", "-p", project, "--request", reqs[0]["request"], "--file", str(img))["ok"]
    assert len(mb("plate", "requests", "-p", project)["data"]["pending"]) == 3


def test_reject_needs_a_note(project, fixtures_dir):
    mb("approve", "-p", project, "--stage", "storyboard")
    mb("plate", "upload", "-p", project, "--shot", "1", "--file", str(fixtures_dir / "plates" / "shot-01.png"))
    assert not mb("review", "-p", project, "--shot", "1", "--decision", "reject")["ok"]
    out = mb("review", "-p", project, "--shot", "1", "--decision", "reject", "--note", "stray figure")
    assert out["data"]["state"] == "needs_redo"
