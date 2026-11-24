"""Export then import gives the same board (T037), plus storyboard flow checks."""

import json

import pytest
from typer.testing import CliRunner

from motionboard.cli import app

runner = CliRunner()


def mb(*args):
    r = runner.invoke(app, [*args, "--json"])
    out = json.loads(r.stdout)
    return out


@pytest.fixture
def project(mb_home, fixtures_dir):
    out = mb("project", "new", "--title", "Fixture", "--song", str(fixtures_dir / "song10s.wav"),
             "--lyrics-file", str(fixtures_dir / "lyrics.txt"), "--idea", "paper boats")
    assert out["ok"], out
    pid = out["project"]
    a = mb("analyze", "-p", pid)
    assert a["ok"], a
    assert a["data"]["duration"] == pytest.approx(10.0, abs=0.05)
    d = mb("draft", "-p", pid, "--mode", "two-lovers", "--look", "origami")
    assert d["ok"], d
    return pid


def board(pid):
    return mb("draft", "-p", pid, "--mode", "two-lovers", "--look", "origami")


def test_round_trip_identical(project, tmp_path):
    exp = mb("export", "-p", project, "--out", str(tmp_path / "exp"))
    assert exp["ok"]
    doc1 = json.loads((tmp_path / "exp" / "project.json").read_text())
    imp = mb("import", "--file", str(tmp_path / "exp"))
    assert imp["ok"], imp
    mb("export", "-p", imp["project"], "--out", str(tmp_path / "exp2"))
    doc2 = json.loads((tmp_path / "exp2" / "project.json").read_text())
    assert doc1["shots"] == doc2["shots"]
    assert doc1["analysis"] == doc2["analysis"]
    for k in ("title", "aspect", "mode", "visual_look", "segment", "lyrics"):
        assert doc1["project"][k] == doc2["project"][k]


def test_draft_refuses_to_overwrite_without_replace(project):
    again = board(project)
    assert not again["ok"] and again["error"]["code"] == "INVALID_INPUT"
    ok = mb("draft", "-p", project, "--mode", "mood-loop", "--look", "cosmic", "--replace")
    assert ok["ok"]
    assert all(s["has_figure"] == 0 for s in ok["data"]["list"])


def test_object_shots_carry_no_figure_line(project):
    r = mb("shot", "set", "-p", project, "--shot", "1", "--field", "has_figure", "--value", "false")
    assert "no people" in r["data"]["plate_prompt"]


def test_gate_rules(project):
    assert mb("approve", "-p", project, "--stage", "plates")["error"]["code"] == "GATE_NOT_APPROVED"
    assert mb("approve", "-p", project, "--stage", "storyboard")["ok"]
    redraft = board(project)
    assert not redraft["ok"]  # approved storyboard blocks redraft
    assert mb("approve", "-p", project, "--stage", "storyboard", "--revoke")["ok"]


def test_lip_sync_needs_a_figure(project):
    mb("shot", "set", "-p", project, "--shot", "1", "--field", "has_figure", "--value", "false")
    r = mb("shot", "set", "-p", project, "--shot", "1", "--field", "lip_sync", "--value", "true")
    assert not r["ok"]


def test_contact_sheet(project):
    r = mb("sheet", "-p", project)
    assert r["ok"] and r["data"]["sheet"].endswith("sheet-storyboard.png")


def test_concepts(project, tmp_path):
    f = tmp_path / "c.json"
    f.write_text(json.dumps([{"title": "Paper river", "premise": "boats carry wishes"},
                             {"title": "Night museum", "premise": "exhibits of almosts"},
                             {"title": "Folded map", "premise": "a journey on paper"}]))
    r = mb("concepts", "add", "-p", project, "--file", str(f))
    assert r["ok"] and len(r["data"]["concepts"]) == 3
    cid = r["data"]["concepts"][1]["id"]
    assert mb("concepts", "choose", "-p", project, "--concept", cid)["data"]["chosen"] == "Night museum"


def test_shot_ideas_file(project, tmp_path):
    f = tmp_path / "shots.json"
    f.write_text(json.dumps({"shots": [
        {"visual": "a paper river under the moon", "action": "a paper boat drifts left to right",
         "camera": "slow pan", "has_figure": False}]}))
    r = mb("draft", "-p", project, "--mode", "two-lovers", "--look", "origami", "--shots-file", str(f), "--replace")
    assert r["ok"]
    assert r["data"]["list"][0]["action"] == "a paper boat drifts left to right"
    assert r["not_verified"]  # fewer ideas than shots is reported


def test_pdf_and_html_exports(mb_home, fixtures_dir, tmp_path, monkeypatch):
    import json as _json

    from typer.testing import CliRunner

    from motionboard.cli import app

    monkeypatch.setenv("MB_BACKEND", "stub")
    run = CliRunner()

    def mb(*a):
        return _json.loads(run.invoke(app, [*a, "--json"]).stdout)

    pid = mb("project", "new", "--title", "Docs <b>", "--song", str(fixtures_dir / "song10s.wav"),
             "--lyrics-file", str(fixtures_dir / "lyrics.txt"))["project"]
    mb("analyze", "-p", pid)
    mb("draft", "-p", pid, "--mode", "travel", "--look", "origami")
    pdf = mb("export", "-p", pid, "--out", str(tmp_path / "board.pdf"), "--format", "pdf")
    assert pdf["ok"] and (tmp_path / "board.pdf").read_bytes()[:5] == b"%PDF-"
    page = mb("export", "-p", pid, "--out", str(tmp_path / "board.html"), "--format", "html")
    assert page["ok"]
    text = (tmp_path / "board.html").read_text()
    assert "Docs &lt;b&gt;" in text and "<b>" not in text.split("<title>")[1].split("</title>")[0]
    assert "data:audio/mpeg;base64," in text and "http" not in text.split("<script>")[1]
