"""Paths and environment.

MB_HOME      workspace folder (default ~/.motionboard)
MB_DB        SQLite file (default $MB_HOME/motionboard.db)
MB_PROJECTS  root for project folders (default ~/Motionboard/projects)
"""

import os
from pathlib import Path

PROJECT_SUBDIRS = ("audio", "plates", "clips", "out", "logs")


def home() -> Path:
    p = Path(os.environ.get("MB_HOME", Path.home() / ".motionboard")).expanduser()
    p.mkdir(parents=True, exist_ok=True)
    return p


def db_path() -> Path:
    return Path(os.environ.get("MB_DB", home() / "motionboard.db")).expanduser()


def projects_root() -> Path:
    p = Path(os.environ.get("MB_PROJECTS", Path.home() / "Motionboard" / "projects")).expanduser()
    p.mkdir(parents=True, exist_ok=True)
    return p


def engine_root() -> Path:
    """engine/ folder of the installed plugin."""
    return Path(__file__).resolve().parents[2]


def repo_root() -> Path:
    return engine_root().parent


def ACTOR() -> str:  # noqa: N802
    """Who is making a change: chat (default), or studio when the Studio bridge runs mb with MB_ACTOR=studio."""
    a = os.environ.get("MB_ACTOR", "chat")
    return a if a in ("chat", "studio") else "chat"
