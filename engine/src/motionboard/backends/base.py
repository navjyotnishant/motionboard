"""Video backend interface (contracts/video-backend.md)."""

import json
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Literal, Protocol

Mode = Literal["i2v", "a2v"]


@dataclass
class ClipJob:
    mode: Mode
    plate: Path
    prompt: str
    width: int
    height: int
    frames: int
    out: Path
    fps: int = 24
    seed: int = 42
    audio: Path | None = None


@dataclass
class InstallStatus:
    installed: bool
    details: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)


class VideoBackend(Protocol):
    name: str
    license_url: str
    min_frames: int
    sizes: dict[str, tuple[int, int]]  # aspect -> (width, height)

    def frame_rule(self, frames: int) -> int: ...
    def check_installed(self) -> InstallStatus: ...
    def build_command(self, job: ClipJob) -> list[str]: ...
    def parse_progress(self, line: str) -> float | None: ...
    def profile(self) -> dict: ...


def round_8k1(frames: int) -> int:
    """LTX frame rule: nearest count of the form 8k+1, at least 9."""
    k = max(1, round((frames - 1) / 8))
    return 8 * k + 1


def load_profile(name: str) -> dict:
    """Measured memory and speed points shipped with the engine (backends/profiles/<name>.json)."""
    try:
        text = resources.files("motionboard.backends.profiles").joinpath(f"{name}.json").read_text()
    except FileNotFoundError:
        return {"backend": name, "base_gb": 0.0, "points": []}
    return json.loads(text)
