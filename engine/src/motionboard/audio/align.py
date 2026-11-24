"""Place sung lines in time (research R5).

With mlx-whisper (optional extra `align`): transcribe the segment with word
timestamps and match each given lyric line to the transcribed words.
Without it, or when matching fails: spread the lines over the segment and snap
starts to beats; the result is marked source="beat" and not verified.
"""

import difflib
import os
import re
from dataclasses import dataclass
from pathlib import Path

WHISPER_MODEL = os.environ.get("MB_WHISPER_MODEL", "mlx-community/whisper-large-v3-turbo")


@dataclass
class Line:
    start: float
    end: float
    text: str
    source: str  # "aligned" or "beat"


def lyric_lines(lyrics: str) -> list[str]:
    out = []
    for raw in lyrics.splitlines():
        s = raw.strip()
        if not s or re.fullmatch(r"[\[(].*[\])]", s):  # skip [Chorus] style tags
            continue
        out.append(s)
    return out


def _norm(word: str) -> str:
    return re.sub(r"[^\w']", "", word.lower())


def _snap(t: float, beats: list[float], tol: float = 0.35) -> float:
    if not beats:
        return t
    b = min(beats, key=lambda x: abs(x - t))
    return b if abs(b - t) <= tol else t


def beat_grid(lines: list[str], duration: float, beats: list[float]) -> list[Line]:
    if not lines:
        return []
    step = duration / len(lines)
    starts = [0.0] + [round(_snap(i * step, beats), 3) for i in range(1, len(lines))]
    ends = starts[1:] + [round(duration, 3)]
    return [Line(s, e, t, "beat") for s, e, t in zip(starts, ends, lines, strict=True)]


def transcribe_words(audio: Path) -> list[tuple[str, float, float]] | None:
    try:
        import mlx_whisper  # type: ignore
    except ImportError:
        return None
    try:
        res = mlx_whisper.transcribe(str(audio), path_or_hf_repo=WHISPER_MODEL, word_timestamps=True)
    except Exception:
        return None
    words = []
    for seg in res.get("segments", []):
        for w in seg.get("words", []):
            words.append((_norm(w["word"]), float(w["start"]), float(w["end"])))
    return [w for w in words if w[0]]


def match_lines(lines: list[str], words: list[tuple[str, float, float]], duration: float) -> list[Line] | None:
    """Map each lyric line to a run of transcribed words. Needs most lines to match."""
    lyric_words, owner = [], []
    for i, line in enumerate(lines):
        for w in line.split():
            if _norm(w):
                lyric_words.append(_norm(w))
                owner.append(i)
    sm = difflib.SequenceMatcher(a=lyric_words, b=[w[0] for w in words], autojunk=False)
    hits: dict[int, list[int]] = {}
    for a, b, size in sm.get_matching_blocks():
        for k in range(size):
            hits.setdefault(owner[a + k], []).append(b + k)
    if len(hits) < max(1, int(0.6 * len(lines))):
        return None
    starts: list[float | None] = [words[min(hits[i])][1] if i in hits else None for i in range(len(lines))]
    # fill gaps by interpolation between known starts
    for i, s in enumerate(starts):
        if s is None:
            prev = next((starts[j] for j in range(i - 1, -1, -1) if starts[j] is not None), 0.0)
            nxt = next((starts[j] for j in range(i + 1, len(starts)) if starts[j] is not None), duration)
            starts[i] = (prev + nxt) / 2
    starts[0] = 0.0
    out = []
    for i, line in enumerate(lines):
        end = starts[i + 1] if i + 1 < len(lines) else duration
        out.append(Line(round(starts[i], 3), round(max(end, starts[i] + 0.1), 3), line,
                        "aligned" if i in hits else "beat"))
    return out


def align(audio: Path, lyrics: str, duration: float, beats: list[float]) -> tuple[list[Line], bool]:
    """Returns (lines, verified). verified is True only when lines came from the voice."""
    lines = lyric_lines(lyrics)
    if not lines:
        return [], False
    words = transcribe_words(audio)
    if words:
        matched = match_lines(lines, words, duration)
        if matched:
            return matched, True
    return beat_grid(lines, duration, beats), False
