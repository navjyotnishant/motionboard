"""Characters, cast links, reference handoff and lip-sync routing (T068 to T072)."""

import json

import pytest
from typer.testing import CliRunner

from motionboard.cli import app
from motionboard.storyboard.draft import chorus_lines

runner = CliRunner()


def mb(*args):
    return json.loads(runner.invoke(app, [*args, "--json"]).stdout)


@pytest.fixture
def project(mb_home, fixtures_dir, monkeypatch):
    monkeypatch.setenv("MB_BACKEND", "stub")
    pid = mb("project", "new", "--title", "Cast", "--song", str(fixtures_dir / "song10s.wav"),
             "--lyrics-file", str(fixtures_dir / "lyrics.txt"))["project"]
    assert mb("analyze", "-p", pid)["ok"]
    assert mb("draft", "-p", pid, "--mode", "two-lovers", "--look", "origami")["ok"]
    return pid


def test_mode_cast_created_on_draft(project):
    names = {c["name"] for c in mb("character", "list", "-p", project)["data"]["characters"]}
    assert {"HER", "HIM"} <= names


def test_style_line_reaches_linked_shots_only(project):
    out = mb("character", "set", "-p", project, "--name", "her", "--field", "style_line",
             "--value", "a woman in a red paper coat")
    assert out["ok"]
    chars = {c["name"]: c for c in mb("character", "list", "-p", project)["data"]["characters"]}
    linked = set(chars["HER"]["shots"])
    assert set(out["data"]["shots_changed"]) == linked
    for o in range(1, 5):
        prompt = mb("shot", "set", "-p", project, "--shot", str(o), "--field", "camera",
                    "--value", "locked off")["data"]["plate_prompt"]
        assert ("red paper coat" in prompt) == (o in linked)


def test_link_needs_a_figure_and_reference_goes_to_plates(project, fixtures_dir):
    ref = fixtures_dir / "plates" / "shot-01.png"
    assert mb("character", "add", "-p", project, "--name", "GUIDE", "--style", "an old guide",
              "--ref", str(ref))["ok"]
    mb("shot", "set", "-p", project, "--shot", "2", "--field", "has_figure", "--value", "false")
    assert mb("character", "link", "-p", project, "--name", "GUIDE", "--shots", "2")["error"]["code"] == "INVALID_INPUT"
    mb("shot", "set", "-p", project, "--shot", "2", "--field", "has_figure", "--value", "true")
    assert mb("character", "link", "-p", project, "--name", "GUIDE", "--shots", "2")["ok"]
    mb("approve", "-p", project, "--stage", "storyboard")
    assert mb("adapter", "--add", "muse", "--kind", "handoff", "--config", '{"hint": "Muse"}')["ok"]
    mb("plates", "-p", project, "--adapter", "muse")
    reqs = {r["shot"]: r for r in mb("plate", "requests", "-p", project)["data"]["pending"]}
    assert reqs[2]["reference_image"] and reqs[2]["reference_image"].endswith("guide.png")


def test_duplicate_character_refused(project):
    assert mb("character", "add", "-p", project, "--name", "her")["error"]["code"] == "INVALID_INPUT"


def test_chorus_is_repeated_lines():
    lyrics = "Verse one\nStay with me\nVerse two\nStay with me!\n"
    assert chorus_lines(lyrics, ["Verse one"]) == {"stay with me"}
    assert chorus_lines("a\nb\n", ["a", "b"]) == {"a", "b"}


def test_studio_session_lip_syncs_sung_shots(mb_home, fixtures_dir, monkeypatch):
    monkeypatch.setenv("MB_BACKEND", "stub")
    pid = mb("project", "new", "--title", "Booth", "--song", str(fixtures_dir / "song10s.wav"),
             "--lyrics-file", str(fixtures_dir / "lyrics.txt"))["project"]
    mb("analyze", "-p", pid)
    shots = mb("draft", "-p", pid, "--mode", "studio-session", "--look", "neon-night")["data"]["list"]
    lip = [s["ord"] for s in shots if s["lip_sync"]]
    assert lip, "studio session should lip-sync sung lines"
    assert all(s["has_figure"] for s in shots if s["lip_sync"])


def test_vocal_slice_covers_every_frame(tmp_path, fixtures_dir):
    import subprocess

    from motionboard.audio.vocals import AUDIO_MARGIN_S, slice_audio

    out = slice_audio(fixtures_dir / "song10s.wav", 8.5, 10.0, tmp_path / "v.wav", 65 / 24 + AUDIO_MARGIN_S)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                str(out)], capture_output=True, text=True).stdout)
    assert dur >= 65 / 24 + AUDIO_MARGIN_S - 0.02
