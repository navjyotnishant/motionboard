"""Pick the song segment and cut it (research R5).

Auto pick: the window of the target length with the highest sustained loudness
(a stand in for the first chorus), started on a beat. A song shorter than the
target is used whole. Cut keeps the recording untouched except a 0.06 s fade in
and a short fade out.
"""

import subprocess
from pathlib import Path

import librosa
import numpy as np

from motionboard.report import MbError

DEFAULT_TARGET = 65.0


def duration(path: Path) -> float:
    return float(librosa.get_duration(path=str(path)))


def auto_pick(path: Path, target: float = DEFAULT_TARGET) -> tuple[float, float]:
    total = duration(path)
    if total <= target + 0.5:
        return 0.0, round(total, 3)
    y, sr = librosa.load(str(path), sr=11025, mono=True)
    hop = 512
    rms = librosa.feature.rms(y=y, hop_length=hop)[0]
    fps = sr / hop
    win = int(target * fps)
    csum = np.concatenate([[0.0], np.cumsum(rms)])
    scores = csum[win:] - csum[:-win]
    best = int(np.argmax(scores)) / fps
    _, beat_frames = librosa.beat.beat_track(y=y, sr=sr, hop_length=hop)
    beats = librosa.frames_to_time(beat_frames, sr=sr, hop_length=hop)
    if len(beats):
        before = beats[beats <= best]
        best = float(before[-1]) if len(before) else float(beats[0])
    start = max(0.0, min(best, total - target))
    return round(start, 3), round(start + target, 3)


def cut(src: Path, dst: Path, start: float, end: float, fade_in: float = 0.06, fade_out: float = 0.5) -> Path:
    if end <= start:
        raise MbError("INVALID_INPUT", f"segment end {end} must be after start {start}")
    length = end - start
    fo = min(fade_out, length / 4)
    af = (
        f"atrim=start={start}:end={end},asetpts=PTS-STARTPTS,"
        f"afade=t=in:st=0:d={fade_in},afade=t=out:st={length - fo:.3f}:d={fo:.3f}"
    )
    dst.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src), "-af", af,
         "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(dst)],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise MbError("MISSING_TOOL" if "not found" in proc.stderr else "INTERNAL", f"ffmpeg cut failed: {proc.stderr}")
    return dst
