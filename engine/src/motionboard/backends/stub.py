"""Stub backend: a solid colour clip of exactly the requested frames, made with ffmpeg.
Used by tests and CI so the whole pipeline runs without a GPU or model weights."""

import re
import shutil
import zlib

from motionboard.backends.base import ClipJob, InstallStatus, load_profile


class StubBackend:
    name = "stub"
    license_url = "https://github.com/navjyotnishant/motionboard/blob/main/LICENSE"
    min_frames = 1
    sizes = {"9:16": (576, 1024), "16:9": (1024, 576)}

    def frame_rule(self, frames: int) -> int:
        return max(1, frames)

    def check_installed(self) -> InstallStatus:
        ff = shutil.which("ffmpeg")
        return InstallStatus(installed=bool(ff), details=[f"ffmpeg: {ff}"] if ff else [],
                             missing=[] if ff else ["ffmpeg"])

    def build_command(self, job: ClipJob) -> list[str]:
        colour = "0x%06x" % (zlib.crc32(job.prompt.encode()) % 0xFFFFFF)
        return [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", f"color=c={colour}:s={job.width}x{job.height}:r={job.fps}",
            "-frames:v", str(job.frames), "-pix_fmt", "yuv420p", "-c:v", "libx264", "-progress", "pipe:1",
            str(job.out),
        ]

    def parse_progress(self, line: str) -> float | None:
        m = re.match(r"frame=(\d+)", line)
        return float(m.group(1)) if m else None

    def profile(self) -> dict:
        return load_profile(self.name)
