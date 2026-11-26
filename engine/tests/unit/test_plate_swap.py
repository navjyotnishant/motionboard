"""A plate swapped after its clip was queued must reach the render, not the old image."""

import json
import os
import sqlite3
import struct
import zlib

import pytest
from typer.testing import CliRunner

from motionboard.cli import app

runner = CliRunner()


def mb(*args):
    return json.loads(runner.invoke(app, [*args, "--json"]).stdout)


def png(path):
    """Write a 2x2 grey PNG."""
    raw = b"".join(b"\x00" + b"\x80\x80\x80" * 2 for _ in range(2))
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 2, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
    return path


@pytest.fixture
def queued(mb_home, fixtures_dir, monkeypatch, tmp_path):
    monkeypatch.setenv("MB_BACKEND", "stub")
    pid = mb("project", "new", "--title", "Swap", "--song", str(fixtures_dir / "song10s.wav"),
             "--lyrics-file", str(fixtures_dir / "lyrics.txt"))["project"]
    assert mb("analyze", "-p", pid)["ok"]
    assert mb("draft", "-p", pid, "--mode", "mood-loop", "--look", "origami")["ok"]
    assert mb("approve", "-p", pid, "--stage", "storyboard")["ok"]
    first = png(tmp_path / "a.png")
    o = 1
    while mb("plate", "upload", "-p", pid, "--shot", str(o), "--file", str(first))["ok"]:
        o += 1
    assert o > 1
    assert mb("review", "-p", pid, "--shot", "0", "--kind", "plate", "--decision", "approve", "--all")["ok"]
    assert mb("approve", "-p", pid, "--stage", "plates")["ok"]
    out = mb("clips", "-p", pid)
    assert out["ok"], out
    return pid, tmp_path


def test_swapped_plate_retargets_queued_job(queued):
    pid, tmp = queued
    new = png(tmp / "b.png")
    assert mb("plate", "upload", "-p", pid, "--shot", "1", "--file", str(new))["ok"]
    db = sqlite3.connect(os.environ["MB_DB"])
    rows = db.execute("SELECT j.settings, s.state FROM render_job j JOIN shot s ON s.id = j.shot_id "
                      "WHERE s.ord = 1 AND j.state = 'queued'").fetchall()
    assert len(rows) == 1
    assert json.loads(rows[0][0])["plate"].endswith("shot-01-v2.png")
    assert rows[0][1] == "clip_queued"


def test_cancel_takes_only_named_shots_out_of_the_queue(queued):
    pid, _ = queued
    out = mb("queue", "-p", pid, "--cancel", "1")
    assert out["ok"] and out["data"]["cancelled"] == [1]
    db = sqlite3.connect(os.environ["MB_DB"])
    rows = dict(db.execute("SELECT s.ord, j.state FROM render_job j JOIN shot s ON s.id = j.shot_id "
                           "WHERE s.project_id = ?", (pid,)).fetchall())
    assert rows[1] == "stopped"
    assert all(state == "queued" for o, state in rows.items() if o != 1)
    state = db.execute("SELECT state FROM shot WHERE project_id = ? AND ord = 1", (pid,)).fetchone()[0]
    assert state == "plate_approved"


def test_seeds_queue_one_take_per_seed_as_new_versions(queued):
    pid, _ = queued
    assert mb("queue", "-p", pid, "--cancel", "1")["ok"]
    out = mb("clips", "-p", pid, "--shots", "1", "--redo", "--seeds", "7,8")
    assert out["ok"], out
    takes = [q for q in out["data"]["queued"] if q["shot"] == 1]
    assert [t["seed"] for t in takes] == [7, 8]
    assert len({t["version"] for t in takes}) == 2
    db = sqlite3.connect(os.environ["MB_DB"])
    outs = [json.loads(r[0])["out"] for r in db.execute(
        "SELECT j.settings FROM render_job j JOIN shot s ON s.id = j.shot_id "
        "WHERE s.ord = 1 AND j.state = 'queued'").fetchall()]
    assert len(outs) == 2 and len(set(outs)) == 2


def test_use_makes_an_earlier_version_active(queued):
    pid, tmp = queued
    assert mb("plate", "upload", "-p", pid, "--shot", "2", "--file", str(png(tmp / "c.png")))["ok"]
    db = sqlite3.connect(os.environ["MB_DB"])
    first = db.execute("SELECT a.id FROM asset_version a JOIN shot s ON s.id = a.shot_id WHERE s.project_id = ? "
                       "AND s.ord = 2 AND a.kind = 'plate' ORDER BY a.created_at LIMIT 1", (pid,)).fetchone()[0]
    out = mb("use", "-p", pid, "--asset", first)
    assert out["ok"] and out["data"]["shot"] == 2
    assert db.execute("SELECT active FROM asset_version WHERE id = ?", (first,)).fetchone()[0] == 1
    assert not mb("use", "-p", pid, "--asset", "NOPE000000000")["ok"]
