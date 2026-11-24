"""Shot timing grid (T027).

Shots tile the segment exactly: first starts at 0, last ends at the segment
length, no gaps, no overlaps. Boundaries sit on sung line starts or beat groups,
long shots split on the beat nearest the middle, short shots merge forward.
Frames are rounded up to the backend frame rule so every clip covers its shot.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass

FPS = 24


@dataclass
class Rhythm:
    unit: str = "line"          # "line" or "beats"
    beats_per_shot: int = 8
    min_shot_s: float = 2.0
    max_shot_s: float = 5.0


@dataclass
class Slot:
    start: float
    end: float
    lyric: str = ""

    @property
    def dur(self) -> float:
        return self.end - self.start


def frames_for(seconds: float, frame_rule: Callable[[int], int], fps: int = FPS) -> int:
    need = max(1, math.ceil(seconds * fps - 1e-6))
    n = need
    while frame_rule(n) < need:
        n += 1
    return frame_rule(n)


def _nearest(beats: list[float], t: float, lo: float, hi: float) -> float | None:
    inside = [b for b in beats if lo < b < hi]
    return min(inside, key=lambda b: abs(b - t)) if inside else None


def _boundaries(duration: float, beats: list[float], lines: list[dict], r: Rhythm) -> list[Slot]:
    if r.unit == "line" and lines:
        starts = sorted({0.0, *[round(float(ln["start"]), 3) for ln in lines if 0 < ln["start"] < duration]})
        text_at = {round(float(ln["start"]), 3): ln["text"] for ln in lines}
        if lines and lines[0]["start"] <= 0.05:
            text_at[0.0] = lines[0]["text"]
    else:
        usable = [b for b in beats if 0 < b < duration]
        starts = [0.0] + usable[r.beats_per_shot - 1 :: r.beats_per_shot] if usable else [0.0]
        text_at = {}
    starts = sorted(set(starts))
    ends = starts[1:] + [duration]
    slots = [Slot(s, e, text_at.get(s, "")) for s, e in zip(starts, ends, strict=True)]
    if not lines or r.unit != "line":
        for sl in slots:
            sl.lyric = " / ".join(ln["text"] for ln in lines if sl.start <= ln["start"] < sl.end)
    return slots


def _split_long(slots: list[Slot], beats: list[float], r: Rhythm) -> list[Slot]:
    out: list[Slot] = []
    queue = list(slots)
    while queue:
        sl = queue.pop(0)
        if sl.dur <= r.max_shot_s:
            out.append(sl)
            continue
        mid = sl.start + sl.dur / 2
        cut = _nearest(beats, mid, sl.start + r.min_shot_s, sl.end - r.min_shot_s) or round(mid, 3)
        queue[:0] = [Slot(sl.start, cut, sl.lyric), Slot(cut, sl.end, sl.lyric)]
    return out


def _merge_short(slots: list[Slot], r: Rhythm) -> list[Slot]:
    out: list[Slot] = []
    for sl in slots:
        if out and (out[-1].dur < r.min_shot_s or sl.dur < r.min_shot_s) and out[-1].dur + sl.dur <= r.max_shot_s:
            prev = out.pop()
            parts = [x for x in (prev.lyric, sl.lyric) if x]
            lyric = " / ".join(dict.fromkeys(parts))
            out.append(Slot(prev.start, sl.end, lyric))
        else:
            out.append(sl)
    return out


def build(duration: float, beats: list[float], lines: list[dict], rhythm: Rhythm) -> list[Slot]:
    slots = _boundaries(duration, beats, lines, rhythm)
    slots = _split_long(slots, beats, rhythm)
    slots = _merge_short(slots, rhythm)
    slots = [Slot(round(s.start, 3), round(s.end, 3), s.lyric) for s in slots]
    validate(slots, duration)
    return slots


def validate(slots: list[Slot] | list[dict], duration: float, tol: float = 0.002) -> None:
    get = (lambda s, k: s[k]) if slots and isinstance(slots[0], dict) else (lambda s, k: getattr(s, k))
    if not slots:
        raise ValueError("storyboard has no shots")
    if abs(get(slots[0], "start")) > tol:
        raise ValueError("first shot must start at 0")
    if abs(get(slots[-1], "end") - duration) > tol:
        raise ValueError(f"last shot must end at the segment length {duration}")
    for a, b in zip(slots, slots[1:], strict=False):
        if abs(get(a, "end") - get(b, "start")) > tol:
            raise ValueError(f"gap or overlap at {get(a, 'end')}")
    for s in slots:
        if get(s, "end") <= get(s, "start"):
            raise ValueError(f"empty shot at {get(s, 'start')}")
