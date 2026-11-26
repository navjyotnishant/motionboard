"""LTX-2.5 via ltx-2-mlx (same runtime as LTX-2.3, newer weights with their own text encoder).

Measured on shot 14 of "You Only Miss Me in the Dark": lip-sync follows the vocal more closely than
LTX-2.3. The fast path (--distilled) is slightly soft; with the detail add-on installed, lip-sync shots
use --dfr, whose second pass runs at full resolution and keeps faces sharp.

Settings (env):
  MB_LTX25_SNAPSHOT        local snapshot folder of dgrauet/ltx-2.5-mlx-q8
  MB_LTX25_DETAIL_LORA     local folder or file of the detail add-on (default: the Hugging Face cache)
"""

import os
import re
from pathlib import Path

from motionboard.backends.base import ClipJob, InstallStatus
from motionboard.backends.ltx23 import LTX23Backend, find_snapshot

HF_REPO = "dgrauet/ltx-2.5-mlx-q8"
DETAIL_REPO = "Lightricks/LTX-2.5-22b-IC-LoRA-Pixel-Spatial-Upscaler"  # gated: accept its licence once


def find_detail_lora() -> Path | None:
    env = os.environ.get("MB_LTX25_DETAIL_LORA")
    root = Path(env).expanduser() if env else find_snapshot(DETAIL_REPO)
    if not root or not root.exists():
        return None
    if root.is_file():
        return root
    files = sorted(root.glob("*.safetensors"))
    return files[0] if files else None


class LTX25Backend(LTX23Backend):
    name = "ltx25"
    license_url = "https://github.com/Lightricks/LTX-2/blob/main/LICENSE-2_x"

    @property
    def snapshot(self) -> str | None:
        s = self._snapshot or os.environ.get("MB_LTX25_SNAPSHOT")
        if s:
            return s
        found = find_snapshot(HF_REPO)
        return str(found) if found else None

    def check_installed(self) -> InstallStatus:
        st = InstallStatus(installed=True)
        if Path(self.bin).exists():
            st.details.append(f"ltx-2-mlx: {self.bin}")
        else:
            st.installed = False
            st.missing.append("ltx-2-mlx (run ./install.sh, or set MB_LTX_BIN)")
        snap = self.snapshot
        need = ("transformer-distilled.safetensors", "text_encoder.safetensors")
        if snap and all((Path(snap) / f).exists() for f in need):
            st.details.append(f"LTX-2.5 q8 weights: {snap}")
        else:
            st.installed = False
            st.missing.append(f"LTX-2.5 weights ({HF_REPO}); run ./install.sh")
        lora = find_detail_lora()
        st.details.append(f"detail add-on: {lora}" if lora
                          else f"detail add-on not installed ({DETAIL_REPO}); lip-sync shots use the softer fast path")
        return st

    def build_command(self, job: ClipJob) -> list[str]:
        if not self.snapshot:
            raise FileNotFoundError("LTX-2.5 snapshot not found; run ./install.sh")
        size = ["-W", str(job.width), "-H", str(job.height), "-f", str(self.frame_rule(job.frames)),
                "--frame-rate", str(job.fps), "--seed", str(job.seed)]
        tail = ["--image", str(job.plate), "-p", job.prompt, "-o", str(job.out)]
        if job.mode == "a2v":
            if not job.audio:
                raise ValueError("a2v needs an audio file")
            lora = find_detail_lora()
            mode = ["--dfr", "--detailing-lora", str(lora)] if lora else ["--distilled"]
            return [self.bin, "a2v", "--model", self.snapshot, *mode, "--low-ram", *size,
                    "--audio", str(job.audio), *tail]
        return [self.bin, "generate", "--model", self.snapshot, "--distilled", "--low-ram", "--no-audio", *size, *tail]

    def parse_progress(self, line: str) -> float | None:
        """Two denoising passes (8 then 3 steps) then decode; LTX-2.5 labels them 'Denoising (ancestral)'."""
        m = re.findall(r"Denoising[^:]*:\s+\d+%\|[^|]*\|\s*(\d+)/(\d+)", line)
        if m:
            done, total = map(int, m[-1])
            frac = done / total
            return round(0.3 * frac if total >= 6 else 0.3 + 0.55 * frac, 3)
        if "vae-decode" in line or "Decoding video" in line:
            return 0.92
        if line.startswith("Saved to:"):
            return 1.0
        return None
