"""Stub backend end to end; stop mid queue; resume renders no finished shot (T052)."""

import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from motionboard.cli import app
from motionboard.db.connection import open_db
from motionboard.guard.monitor import Sample
from motionboard.jobs import queue, worker

runner = CliRunner()
ROOMY = Sample(free_pct=80, swap_used_mb=0, total_gb=36.0)


def mb(*args):
    return json.loads(runner.invoke(app, [*args, "--json"]).stdout)


@pytest.fixture
def ready(mb_home, fixtures_dir, monkeypatch):
    monkeypatch.setenv("MB_BACKEND", "stub")
    out = mb("project", "new", "--title", "Resume", "--song", str(fixtures_dir / "song10s.wav"),
             "--lyrics-file", str(fixtures_dir / "lyrics.txt"))
    pid, folder = out["project"], Path(out["data"]["folder"])
    mb("analyze", "-p", pid)
    mb("draft", "-p", pid, "--mode", "two-lovers", "--look", "origami")
    mb("approve", "-p", pid, "--stage", "storyboard")
    (folder / "plates" / "inbox").mkdir(parents=True, exist_ok=True)
    for f in (fixtures_dir / "plates").glob("shot-*.png"):
        shutil.copy(f, folder / "plates" / "inbox" / f.name)
    assert mb("plates", "-p", pid)["ok"]
    mb("review", "-p", pid, "--shot", "0", "--decision", "approve", "--all")
    assert mb("approve", "-p", pid, "--stage", "plates")["ok"]
    return pid, folder


def test_render_stop_resume(ready):
    pid, folder = ready
    assert len(mb("clips", "-p", pid)["data"]["queued"]) == 4
    first = worker.run(sampler=lambda _pid: ROOMY, max_jobs=2)
    assert all(r["ok"] for r in first) and len(first) == 2
    conn = open_db()
    assert queue.stop(conn, pid, "chat") == 2  # two still queued
    conn.close()
    again = mb("clips", "-p", pid)
    assert len(again["data"]["queued"]) == 2
    assert {s["reason"] for s in again["data"]["skipped"]} == {"has a finished clip"}
    second = worker.run(sampler=lambda _pid: ROOMY)
    assert len(second) == 2 and all(r["ok"] for r in second)
    clips = sorted(p.name for p in (folder / "clips").glob("*.mp4"))
    assert clips == [f"shot-0{i}-v1.mp4" for i in range(1, 5)]
    for r in first + second:
        assert r["probe"]["width"] == 576 and r["probe"]["height"] == 1024
        assert not r["problems"]


def test_fit_refusal_marks_shot_failed_with_suggestion(ready):
    pid, _ = ready
    mb("clips", "-p", pid)
    starved = Sample(free_pct=8, swap_used_mb=0, total_gb=1.0)
    conn = open_db()
    conn.execute("UPDATE guard_profile SET start_free_pct = 9 WHERE name = 'balanced'")
    conn.close()
    res = worker.run(sampler=lambda _pid: starved, max_jobs=1)
    assert not res[0]["ok"]
    assert "does not fit" in res[0]["reason"]
    conn = open_db()
    job = conn.execute("SELECT state, stop_reason, suggestion FROM render_job WHERE id = ?",
                       (res[0]["job"],)).fetchone()
    shot_state = conn.execute("SELECT s.state FROM shot s JOIN render_job j ON j.shot_id = s.id WHERE j.id = ?",
                              (res[0]["job"],)).fetchone()[0]
    conn.close()
    assert job["state"] == "failed" and job["stop_reason"].startswith("fit check")
    assert shot_state == "clip_failed"
