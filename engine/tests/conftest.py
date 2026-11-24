"""Shared fixtures: every test gets its own DB file and projects root."""

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def mb_home(tmp_path, monkeypatch) -> Path:
    """Isolated ~/.motionboard and DB for one test."""
    home = tmp_path / "mb_home"
    home.mkdir()
    monkeypatch.setenv("MB_HOME", str(home))
    monkeypatch.setenv("MB_DB", str(home / "motionboard.db"))
    monkeypatch.setenv("MB_PROJECTS", str(tmp_path / "projects"))
    return home


@pytest.fixture
def project_dir(tmp_path) -> Path:
    d = tmp_path / "projects" / "test-project"
    for sub in ("audio", "plates", "clips", "out", "logs"):
        (d / sub).mkdir(parents=True)
    return d
