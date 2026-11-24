import json

from typer.testing import CliRunner

from motionboard.cli import app


def test_version_json():
    result = CliRunner().invoke(app, ["version", "--json"])
    assert result.exit_code == 0
    out = json.loads(result.stdout)
    assert out["ok"] is True
    assert out["data"]["version"]


def test_fixtures_present(fixtures_dir):
    assert (fixtures_dir / "song10s.wav").exists()
    assert (fixtures_dir / "lyrics.txt").exists()
    assert len(list((fixtures_dir / "plates").glob("shot-*.png"))) == 4
    assert (fixtures_dir / "export80.json").exists()
