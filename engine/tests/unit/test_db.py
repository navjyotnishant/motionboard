import json

from typer.testing import CliRunner

from motionboard.backends.base import ClipJob, round_8k1
from motionboard.backends.registry import get as get_backend
from motionboard.cli import app
from motionboard.db import events, repo
from motionboard.db.connection import current_version, latest_version, open_db
from motionboard.guard import fitcheck, presets
from motionboard.guard.monitor import Sample


def test_migrate_is_idempotent(mb_home):
    c = open_db()
    assert current_version(c) == latest_version() == 1
    c2 = open_db()
    assert current_version(c2) == 1
    assert c.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert c.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_writes_emit_change_events(mb_home):
    c = open_db()
    seq0 = c.execute("SELECT coalesce(max(seq),0) FROM change_event").fetchone()[0]
    rid = repo.insert(c, "template", {"name": "t", "source": "user", "body": "x: 1"}, "studio")
    repo.update(c, "template", rid, {"body": "x: 2"}, "chat")
    repo.delete(c, "template", rid, "worker")
    evs = events.since(c, seq0)
    assert [(e["kind"], e["actor"]) for e in evs] == [("insert", "studio"), ("update", "chat"), ("delete", "worker")]


def test_ids_are_sortable_and_unique():
    ids = [repo.new_id() for _ in range(200)]
    assert len(set(ids)) == 200 and all(len(i) == 26 for i in ids)


def test_presets_seeded_and_switchable(mb_home):
    c = open_db()
    assert {p.name for p in presets.list_profiles(c)} == {"safe", "balanced", "max"}
    assert presets.active(c).name == "balanced"
    presets.set_active(c, "safe", "chat")
    assert presets.active(c).name == "safe"


def test_frame_rule():
    assert [round_8k1(n) for n in (1, 9, 12, 13, 96, 97, 100)] == [9, 9, 9, 17, 97, 97, 97]


def test_fit_uses_profile_and_suggests():
    b = get_backend("stub")
    p = presets.BUILTIN[1]
    roomy = Sample(free_pct=70, swap_used_mb=0, total_gb=36.0)
    assert fitcheck.fit(b, "i2v", 576, 1024, 97, p, sample=roomy).fits
    tight = Sample(free_pct=8, swap_used_mb=0, total_gb=36.0)  # at the kill floor: no headroom
    res = fitcheck.fit(b, "i2v", 576, 1024, 97, p, sample=tight)
    assert not res.fits and res.suggestions


def test_stub_backend_command(tmp_path):
    b = get_backend("stub")
    cmd = b.build_command(ClipJob("i2v", tmp_path / "p.png", "boat", 576, 1024, 33, tmp_path / "o.mp4"))
    assert "-frames:v" in cmd and cmd[cmd.index("-frames:v") + 1] == "33"


def test_cli_guard_and_fit_json(mb_home, monkeypatch):
    runner = CliRunner()
    r = runner.invoke(app, ["db", "migrate", "--json"])
    assert r.exit_code == 0 and json.loads(r.stdout)["ok"]
    r = runner.invoke(app, ["guard", "--create", "tight", "--start", "50", "--kill", "20", "--swap", "100",
                            "--set", "tight", "--json"])
    out = json.loads(r.stdout)
    assert out["ok"] and out["data"]["active"] == "tight"
    r = runner.invoke(app, ["guard", "--create", "bad", "--start", "10", "--kill", "20", "--swap", "1", "--json"])
    assert r.exit_code == 1 and json.loads(r.stdout)["error"]["code"] == "INVALID_INPUT"
    r = runner.invoke(app, ["fit", "--backend", "stub", "--width", "576", "--height", "1024", "--frames", "97",
                            "--json"])
    out = json.loads(r.stdout)
    assert "est_peak_gb" in out["data"]
    assert out["not_verified"]
