"""Tempo, beats, loudness, onsets and waveform peaks (research R5)."""

from dataclasses import dataclass, field
from pathlib import Path

import librosa
import numpy as np

SR = 22050
FPS = 24
PEAK_BUCKETS = 2000


@dataclass
class Analysis:
    duration: float
    tempo_bpm: float
    beats: list[float]
    loudness: list[float] = field(default_factory=list)   # RMS per video frame, 0..1
    onsets: list[float] = field(default_factory=list)     # onset strength per video frame, 0..1
    peaks: list[float] = field(default_factory=list)      # max abs per bucket, 0..1


def _per_frame(values: np.ndarray, sr: int, hop: int, duration: float, fps: int = FPS) -> list[float]:
    times = librosa.frames_to_time(np.arange(len(values)), sr=sr, hop_length=hop)
    grid = np.arange(0, duration, 1 / fps)
    out = np.interp(grid, times, values) if len(values) else np.zeros_like(grid)
    m = out.max() if out.size and out.max() > 0 else 1.0
    return [round(float(v / m), 4) for v in out]


def peaks(y: np.ndarray, buckets: int = PEAK_BUCKETS) -> list[float]:
    if y.size == 0:
        return []
    n = min(buckets, y.size)
    chunks = np.array_split(np.abs(y), n)
    p = np.array([c.max() for c in chunks])
    m = p.max() or 1.0
    return [round(float(v / m), 4) for v in p]


def analyze(path: Path, start: float = 0.0, end: float | None = None) -> Analysis:
    y, sr = librosa.load(str(path), sr=SR, mono=True, offset=start, duration=None if end is None else end - start)
    duration = len(y) / sr
    hop = 512
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, hop_length=hop)
    tempo = float(np.atleast_1d(tempo)[0])
    beats = [round(float(t), 3) for t in librosa.frames_to_time(beat_frames, sr=sr, hop_length=hop)]
    rms = librosa.feature.rms(y=y, hop_length=hop)[0]
    onset = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
    return Analysis(
        duration=round(duration, 3),
        tempo_bpm=round(tempo, 2),
        beats=beats,
        loudness=_per_frame(rms, sr, hop, duration),
        onsets=_per_frame(onset, sr, hop, duration),
        peaks=peaks(y),
    )
