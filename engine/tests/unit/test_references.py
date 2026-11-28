"""Several references per character, every cast member's references on a plate request, honest adapter capacity
(US2, FR-009 to FR-013)."""

import json
import sys
import urllib.request
from pathlib import Path

import pytest
from typer.testing import CliRunner

from motionboard.cli import app
from motionboard.plates.adapter import Reference, select_references
from motionboard.plates.command import CommandAdapter
from motionboard.plates.http_api import HttpAdapter
from motionboard.report import MbError

runner = CliRunner()
FIX = Path(__file__).resolve().parents[1] / "fixtures" / "almost-yours"


def mb(*args):
    return json.loads(runner.invoke(app, [*args, "--json"]).stdout)


@pytest.fixture
def project(mb_home, fixtures_dir, monkeypatch):
    """Shots 3 and 4 have HER and HIM; each has a face and a silhouette reference."""
    monkeypatch.setenv("MB_BACKEND", "stub")
    pid = mb("project", "new", "--title", "Refs", "--song", str(fixtures_dir / "song10s.wav"),
             "--lyrics-file", str(fixtures_dir / "lyrics.txt"))["project"]
    mb("analyze", "-p", pid)
    mb("draft", "-p", pid, "--mode", "two-lovers", "--look", "origami", "--shots-file", str(FIX / "shots.json"))
    plates = fixtures_dir / "plates"
    for name, a, b in (("HER", "shot-01.png", "shot-02.png"), ("HIM", "shot-03.png", "shot-04.png")):
        assert mb("character", "ref", "add", "-p", pid, "--name", name, "--file", str(plates / a),
                  "--purpose", "face")["ok"]
        assert mb("character", "ref", "add", "-p", pid, "--name", name, "--file", str(plates / b),
                  "--purpose", "silhouette", "--description", "full figure")["ok"]
    mb("approve", "-p", pid, "--stage", "storyboard")
    return pid


def cast(pid):
    return {c["name"]: c for c in mb("character", "list", "-p", pid)["data"]["characters"]}


def test_first_reference_is_primary_and_legacy_field_mirrors_it(project):
    chars = cast(project)
    her = chars["HER"]["references"]
    assert [(r["purpose"], r["primary"]) for r in her] == [("face", True), ("silhouette", False)]
    assert chars["HER"]["reference_image"] == her[0]["path"]
    assert Path(her[0]["path"]).name == "her.png" and Path(her[1]["path"]).name.startswith("her-silhouette")
    out = mb("character", "ref", "primary", "-p", project, "--id", her[1]["id"])
    assert out["data"]["reference"]["primary"]
    assert cast(project)["HER"]["reference_image"] == her[1]["path"]
    mb("character", "ref", "remove", "-p", project, "--id", her[1]["id"])
    after = cast(project)["HER"]
    assert [r["id"] for r in after["references"]] == [her[0]["id"]] and after["references"][0]["primary"]
    assert after["reference_image"] == her[0]["path"] and Path(her[1]["path"]).exists(), "file kept on disk"


def test_two_character_shot_carries_both_characters_references(project):
    assert mb("adapter", "--add", "muse", "--kind", "handoff")["ok"]
    out = mb("plates", "-p", project, "--adapter", "muse")
    assert out["ok"]
    reqs = {r["shot"]: r for r in mb("plate", "requests", "-p", project)["data"]["pending"]}
    both = reqs[3]["references"]
    assert [(r["character"], r["purpose"], r["primary"]) for r in both] == [
        ("HER", "face", True), ("HER", "silhouette", False), ("HIM", "face", True), ("HIM", "silhouette", False)]
    assert reqs[3]["reference_image"] == both[0]["path"] and reqs[3]["references_dropped"] == []
    assert [r["character"] for r in reqs[2]["references"]] == ["HER", "HER"]
    assert reqs[1]["references"] == []
    assert any("10 character reference images" in v for v in out["verified"])


def test_single_reference_command_refuses_instead_of_dropping(project, tmp_path):
    cmd = [sys.executable, "-c", "import sys, shutil; shutil.copy(sys.argv[2], sys.argv[1])", "{out}", "{ref}"]
    assert mb("adapter", "--add", "one", "--kind", "command", "--config", json.dumps({"cmd": cmd}))["ok"]
    listing = {a["name"]: a for a in mb("adapter", "--list")["data"]["adapters"]}
    assert listing["one"]["reference_capacity"] == 1 and listing["manual"]["reference_capacity"] == "unlimited"
    out = mb("plates", "-p", project, "--adapter", "one", "--shots", "3")
    failed = out["data"]["failed"][0]
    assert failed["shot"] == 3 and "4 reference images (HER, HIM)" in failed["error"]
    assert "--reference-strategy" in failed["hint"]
    assert not out["data"]["done"]
    # primary keeps HER face and HIM face: still two for one slot, so it still refuses
    assert mb("plates", "-p", project, "--adapter", "one", "--shots", "3", "--reference-strategy",
              "primary")["data"]["failed"]
    # first sends one and says exactly which three were not sent
    out = mb("plates", "-p", project, "--adapter", "one", "--shots", "3", "--reference-strategy", "first")
    done = out["data"]["done"][0]
    assert [(r["character"], r["purpose"]) for r in done["references"]] == [("HER", "face")]
    assert [(d["character"], d["purpose"], d["reason"]) for d in done["references_dropped"]] == [
        ("HER", "silhouette", "adapter takes 1"), ("HIM", "face", "adapter takes 1"),
        ("HIM", "silhouette", "adapter takes 1")]
    assert sum("reference not sent" in v for v in out["not_verified"]) == 3


def test_refs_placeholder_passes_every_reference(project, tmp_path):
    log = tmp_path / "argv.json"
    script = (f"import sys, json, shutil; json.dump(sys.argv[2:], open({str(log)!r}, 'w')); "
              "shutil.copy(sys.argv[2], sys.argv[1])")
    cmd = [sys.executable, "-c", script, "{out}", "{refs}"]
    mb("adapter", "--add", "many", "--kind", "command", "--config", json.dumps({"cmd": cmd}))
    out = mb("plates", "-p", project, "--adapter", "many", "--shots", "4")
    assert out["data"]["done"], out
    assert len(json.loads(log.read_text())) == 4


def test_missing_reference_file_is_reported_not_sent(project):
    her = cast(project)["HER"]["references"]
    Path(her[1]["path"]).unlink()
    mb("adapter", "--add", "muse", "--kind", "handoff")
    mb("plates", "-p", project, "--adapter", "muse", "--shots", "2")
    req = mb("plate", "requests", "-p", project)["data"]["pending"][0]
    assert [r["purpose"] for r in req["references"]] == ["face"]
    assert req["references_dropped"][0]["reason"] == "file missing"


def test_capacity_of_each_adapter_kind():
    assert CommandAdapter("c", {"cmd": ["x", "{out}"]}, 0).reference_capacity() == 0
    assert CommandAdapter("c", {"cmd": ["x", "--ref={ref}"]}, 0).reference_capacity() == 1
    assert CommandAdapter("c", {"cmd": ["x", "{refs}"]}, 0).reference_capacity() is None
    assert HttpAdapter("h", {"url": "u", "body": {"prompt": "{prompt}"}}, 0).reference_capacity() == 0
    assert HttpAdapter("h", {"url": "u", "body": {"image": "{ref_b64}"}}, 0).reference_capacity() == 1
    assert HttpAdapter("h", {"url": "u", "refs_field": "input.images"}, 0).reference_capacity() is None


def test_http_adapter_sends_every_reference_in_refs_field(tmp_path, monkeypatch, fixtures_dir):
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
    from motionboard.plates.adapter import PlateRequest

    refs = [Reference("HER", fixtures_dir / "plates/shot-01.png", "face", True),
            Reference("HIM", fixtures_dir / "plates/shot-03.png", "face", True)]
    ad = HttpAdapter("h", {"url": "http://x", "body": {"prompt": "{prompt}"}, "refs_field": "input.images",
                           "refs_encoding": "data_url"}, 0)
    ad.request(PlateRequest("r", "s", 1, "a museum", "", 8, 8, tmp_path / "o.png", references=refs))
    assert sent["body"]["prompt"] == "a museum"
    assert len(sent["body"]["input"]["images"]) == 2
    assert all(x.startswith("data:image/png;base64,") for x in sent["body"]["input"]["images"])


def test_selection_rules(tmp_path):
    f = tmp_path / "a.png"
    f.write_bytes(b"x")
    refs = [Reference("HER", f, "face", True), Reference("HER", f, "detail"), Reference("HIM", f, "face", True)]
    assert select_references(refs, None, "strict", "a") == (refs, [])
    with pytest.raises(MbError) as e:
        select_references(refs, 2, "strict", "a")
    assert e.value.code == "INVALID_INPUT" and e.value.data["capacity"] == 2
    sent, dropped = select_references(refs, 2, "primary", "a")
    assert [r.character for r in sent] == ["HER", "HIM"] and dropped[0]["reason"] == "reference strategy primary"
    sent, dropped = select_references(refs, 5, "none", "a")
    assert sent == [] and len(dropped) == 3
    with pytest.raises(MbError):
        select_references(refs, 1, "best", "a")
