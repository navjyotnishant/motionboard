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


def test_module_entry_has_every_command(mb_home):
    """mb worker --detach runs `python -m motionboard worker`; that entry must see all commands."""
    import subprocess
    import sys

    out = subprocess.run([sys.executable, "-m", "motionboard", "worker", "--json"], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert json.loads(out.stdout.strip().splitlines()[-1])["ok"]
