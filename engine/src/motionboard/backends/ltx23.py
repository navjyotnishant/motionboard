"""LTX-2.3 via ltx-2-mlx, run as a subprocess from its own venv (research R2).

Settings (workspace_setting or env):
  ltx_bin       path to the ltx-2-mlx executable   (MB_LTX_BIN)
  ltx_snapshot  local snapshot folder of dgrauet/ltx-2.3-mlx-q8 (MB_LTX_SNAPSHOT)
Always pass the local snapshot path as --model so nothing is downloaded.
"""

import os
import re
import shutil
from pathlib import Path

from motionboard.backends.base import ClipJob, InstallStatus, load_profile, round_8k1

HF_REPO = "dgrauet/ltx-2.3-mlx-q8"
TEXT_ENCODER_REPO = "mlx-community/gemma-3-12b-it-4bit"
DEFAULT_BIN = Path.home() / "dev" / "ltx-2-mlx" / ".venv" / "bin" / "ltx-2-mlx"


def _hf_cache() -> Path:
    return Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface")) / "hub"


def find_snapshot(repo: str = HF_REPO) -> Path | None:
    snaps = _hf_cache() / f"models--{repo.replace('/', '--')}" / "snapshots"
    if not snaps.is_dir():
        return None
    candidates = sorted((p for p in snaps.iterdir() if p.is_dir()), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


class LTX23Backend:
    name = "ltx23"
    license_url = "https://huggingface.co/Lightricks/LTX-2.3/blob/main/LICENSE"
    min_frames = 9
    sizes = {"9:16": (576, 1024), "16:9": (1024, 576)}

    def __init__(self, bin_path: str | None = None, snapshot: str | None = None):
        self._bin = bin_path
        self._snapshot = snapshot

    @property
    def bin(self) -> str:
        return self._bin or os.environ.get("MB_LTX_BIN") or shutil.which("ltx-2-mlx") or str(DEFAULT_BIN)

    @property
    def snapshot(self) -> str | None:
        s = self._snapshot or os.environ.get("MB_LTX_SNAPSHOT")
        if s:
            return s
        found = find_snapshot()
        return str(found) if found else None

    def frame_rule(self, frames: int) -> int:
        return round_8k1(frames)

    def check_installed(self) -> InstallStatus:
        st = InstallStatus(installed=True)
        if Path(self.bin).exists():
            st.details.append(f"ltx-2-mlx: {self.bin}")
        else:
            st.installed = False
            st.missing.append("ltx-2-mlx (pip install in its own venv, then set MB_LTX_BIN)")
        snap = self.snapshot
        if snap and Path(snap).is_dir() and any(Path(snap).glob("*.safetensors")):
            st.details.append(f"LTX-2.3 q8 weights: {snap}")
        else:
            st.installed = False
            st.missing.append(f"LTX-2.3 weights ({HF_REPO}); see mb setup --fix-plan")
        if find_snapshot(TEXT_ENCODER_REPO):
            st.details.append(f"text encoder: {TEXT_ENCODER_REPO}")
        else:
            st.installed = False
            st.missing.append(f"text encoder ({TEXT_ENCODER_REPO})")
        return st

    def build_command(self, job: ClipJob) -> list[str]:
        if not self.snapshot:
            raise FileNotFoundError("LTX-2.3 snapshot not found; run mb setup")
        size = ["-W", str(job.width), "-H", str(job.height), "-f", str(self.frame_rule(job.frames)),
                "--frame-rate", str(job.fps), "--seed", str(job.seed)]
        tail = ["--image", str(job.plate), "-p", job.prompt, "-o", str(job.out)]
        if job.mode == "a2v":
            if not job.audio:
                raise ValueError("a2v needs an audio file")
            return [self.bin, "a2v", "--model", self.snapshot, "--distilled", "--low-ram", *size,
                    "--audio", str(job.audio), *tail]
        return [self.bin, "generate", "--model", self.snapshot, "--distilled", "--low-ram", "--no-audio", *size, *tail]

    def parse_progress(self, line: str) -> float | None:
        """Two denoising passes (8 then 3 steps) then decode; map to 0..1."""
        m = re.findall(r"Denoising:\s+\d+%\|[^|]*\|\s*(\d+)/(\d+)", line)
        if m:
            done, total = map(int, m[-1])
            first = total >= 6
            frac = done / total
            return round(0.35 * frac if first else 0.35 + 0.55 * frac, 3)
        if "Decoding video" in line:
            return 0.92
        if line.startswith("Saved to:"):
            return 1.0
        return None

    def profile(self) -> dict:
        return load_profile(self.name)
