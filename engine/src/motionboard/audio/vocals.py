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


def slice_audio(src: Path, start: float, end: float, out: Path, min_seconds: float = 0.0) -> Path:
    """Cut [start, end) from src. Pads with silence up to min_seconds when the clip is longer than the shot
    (frames are rounded up to the backend's frame rule, and the audio must cover every frame)."""
    af = f"atrim=start={start}:end={max(end, start + min_seconds)},asetpts=PTS-STARTPTS"
    if min_seconds > 0:
        af += f",apad=whole_dur={min_seconds:.3f}"
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src),
                        "-af", af, "-ac", "1", "-ar", "44100", str(out)], capture_output=True, text=True)
    if r.returncode != 0:
        raise MbError("INTERNAL", f"audio slice failed: {r.stderr.strip()}")
    return out


AUDIO_MARGIN_S = 0.3  # the a2v encoder needs a little more audio than frames / fps


def shot_vocal(project_folder: Path, shot: dict, profile: GuardProfile, frames: int = 0,
               fps: float = 24.0) -> tuple[Path, bool]:
    """Audio for one lip-sync shot, long enough for every rendered frame. Returns (path, isolated)."""
    seg = project_folder / "audio" / "segment.wav"
    vocals = project_folder / "audio" / "vocals.wav"
    isolated = separate(seg, vocals, profile)
    src = vocals if isolated else seg
    out = project_folder / "audio" / f"shot-{shot['ord']:02d}-vocal.wav"
    need = frames / fps + AUDIO_MARGIN_S if frames else 0.0
    return slice_audio(src, shot["start"], shot["end"], out, need), isolated
