"""Vocal audio for lip-sync shots (research R6).

demucs (optional extra `vocals`) separates the segment once into audio/vocals.wav,
under the memory guard. Each lip-sync shot gets its own slice. Without demucs the
full mix is sliced instead and the caller reports that the vocal was not isolated.
"""

import importlib.util
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from motionboard.guard.presets import GuardProfile
from motionboard.guard.run import run_guarded
from motionboard.report import MbError


def demucs_available() -> bool:
    return importlib.util.find_spec("demucs") is not None


def separate(segment: Path, out: Path, profile: GuardProfile) -> bool:
    """Write the vocal stem of the whole segment to `out`. Returns False when demucs is missing."""
    if out.exists():
        return True
    if not demucs_available():
        return False
    with tempfile.TemporaryDirectory() as d:
        res = run_guarded([sys.executable, "-m", "demucs", "--two-stems=vocals", "-n", "htdemucs", "-o", d,
                           str(segment)], profile, log_path=out.with_suffix(".log"))
        if res.stopped:
            raise MbError("GUARD_STOPPED", res.stop_reason or "vocal separation stopped")
        found = list(Path(d).rglob("vocals.wav"))
        if res.exit_code != 0 or not found:
            raise MbError("INTERNAL", f"vocal separation failed; see {out.with_suffix('.log')}")
        shutil.copy2(found[0], out)
    return True


def slice_audio(src: Path, start: float, end: float, out: Path) -> Path:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src),
                        "-af", f"atrim=start={start}:end={end},asetpts=PTS-STARTPTS", "-ac", "1", "-ar", "44100",
                        str(out)], capture_output=True, text=True)
    if r.returncode != 0:
        raise MbError("INTERNAL", f"audio slice failed: {r.stderr.strip()}")
    return out


def shot_vocal(project_folder: Path, shot: dict, profile: GuardProfile) -> tuple[Path, bool]:
    """Audio for one lip-sync shot. Returns (path, isolated)."""
    seg = project_folder / "audio" / "segment.wav"
    vocals = project_folder / "audio" / "vocals.wav"
    isolated = separate(seg, vocals, profile)
    src = vocals if isolated else seg
    out = project_folder / "audio" / f"shot-{shot['ord']:02d}-vocal.wav"
    return slice_audio(src, shot["start"], shot["end"], out), isolated
