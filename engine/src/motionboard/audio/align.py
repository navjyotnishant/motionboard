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


def _window(lines: list[str], heard: list[str]) -> tuple[int, int]:
    """The run of lyric lines the segment most likely covers. A song repeats its chorus, so matching the
    segment against the whole sheet scatters the hits; slide a window of about the heard length instead."""
    words_per_line = [len([w for w in ln.split() if _norm(w)]) for ln in lines]
    best, best_range = -1.0, (0, len(lines) - 1)
    for i in range(len(lines)):
        n, j = 0, i
        while j < len(lines) and n < len(heard) * 1.25:
            n += words_per_line[j]
            j += 1
        cand = [_norm(w) for ln in lines[i:j] for w in ln.split() if _norm(w)]
        score = difflib.SequenceMatcher(a=cand, b=heard, autojunk=False).ratio()
        if score > best:
            best, best_range = score, (i, j - 1)
    return best_range


def match_lines(lines: list[str], words: list[tuple[str, float, float]], duration: float) -> list[Line] | None:
    """Map the lyric lines sung in this segment to runs of transcribed words. Lines outside the segment
    are left out. Needs most lines in the sung run to match."""
    heard = [w[0] for w in words]
    lo, hi = _window(lines, heard)
    lyric_words, owner = [], []
    for i in range(lo, hi + 1):
        for w in lines[i].split():
            if _norm(w):
                lyric_words.append(_norm(w))
                owner.append(i)
    sm = difflib.SequenceMatcher(a=lyric_words, b=heard, autojunk=False)
    hits: dict[int, list[int]] = {}
    for a, b, size in sm.get_matching_blocks():
        for k in range(size):
            hits.setdefault(owner[a + k], []).append(b + k)
    if not hits:
        return None
    first, last = min(hits), max(hits)
    run = list(range(first, last + 1))
    if len(run) < 2 or sum(1 for i in run if i in hits) < max(2, int(0.6 * len(run))):
        return None
    starts: dict[int, float] = {i: words[min(hits[i])][1] for i in run if i in hits}
    for i in run:  # fill gaps by interpolation between known starts
        if i not in starts:
            prev = next((starts[j] for j in range(i - 1, first - 1, -1) if j in starts), 0.0)
            nxt = next((starts[j] for j in range(i + 1, last + 1) if j in starts), duration)
            starts[i] = (prev + nxt) / 2
    out = []
    for k, i in enumerate(run):
        end = starts[run[k + 1]] if k + 1 < len(run) else words[max(hits[last])][2] + 0.4
        end = min(end, duration)
        out.append(Line(round(starts[i], 3), round(max(end, starts[i] + 0.1), 3), lines[i],
                        "aligned" if i in hits else "beat"))
    while len(out) > 2 and out[-1].end - out[-1].start < 0.5:  # a line cut off by the segment end
        out.pop()
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
