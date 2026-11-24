"""Fit check refuses oversize requests with useful suggestions (T067); setup never downloads."""

import json
import subprocess

from typer.testing import CliRunner

from motionboard.backends.ltx23 import LTX23Backend
from motionboard.cli import app
from motionboard.guard import fitcheck, presets
from motionboard.guard.monitor import Sample
from motionboard.setup.models import CATALOG

BALANCED = presets.BUILTIN[1]


def test_ltx_fits_with_room():
    s = Sample(free_pct=74, swap_used_mb=0, total_gb=36.0)
    r = fitcheck.fit(LTX23Backend(), "i2v", 576, 1024, 97, BALANCED, sample=s)
    assert r.fits and 15 < r.est_peak_gb < 19


def test_ltx_refused_when_tight_with_suggestions():
    s = Sample(free_pct=50, swap_used_mb=0, total_gb=36.0)  # 15 GB headroom
    r = fitcheck.fit(LTX23Backend(), "i2v", 1080, 1920, 241, BALANCED, sample=s)
    assert not r.fits
    assert any("frames" in x for x in r.suggestions) or any("x" in x for x in r.suggestions)


def test_unknown_profile_refuses():
    class Bare(LTX23Backend):
        name = "bare"

        def profile(self):
            return {"backend": "bare", "base_gb": 0, "points": []}

    r = fitcheck.fit(Bare(), "i2v", 576, 1024, 97, BALANCED, sample=Sample(90, 0, 36.0))
    assert not r.fits and "test shot" in r.suggestions[0]


def test_download_commands_resume_safely_and_never_run():
    for m in CATALOG:
        if not m.repo.startswith("(") and not m.backlog:
            assert m.download_command().startswith("HF_HUB_DISABLE_XET=1 hf download")


def test_setup_reports_without_downloading(mb_home, monkeypatch):
    calls = []
    real = subprocess.run

    def spy(cmd, *a, **k):
        calls.append(cmd)
        return real(cmd, *a, **k)

    monkeypatch.setattr(subprocess, "run", spy)
    out = json.loads(CliRunner().invoke(app, ["setup", "--quick", "--fix-plan", "--json"]).stdout)
    assert out["ok"]
    assert {"machine", "tools", "models", "gaps", "fix_plan"} <= set(out["data"])
    assert not any("download" in " ".join(map(str, c)) for c in calls)
