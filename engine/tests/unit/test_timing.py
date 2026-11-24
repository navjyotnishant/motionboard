"""Timing grid: tiling, frame rule, beat and line alignment (T036)."""

import pytest

from motionboard.backends.base import round_8k1
from motionboard.storyboard import timing
from motionboard.storyboard.timing import Rhythm, frames_for

BEATS = [round(0.5 * i, 3) for i in range(1, 40)]  # 120 bpm over 20 s


def lines(*starts, duration=20.0):
    ends = list(starts[1:]) + [duration]
    return [{"start": s, "end": e, "text": f"line {i + 1}"} for i, (s, e) in enumerate(zip(starts, ends, strict=True))]


def test_line_unit_tiles_segment_and_keeps_line_starts():
    ls = lines(0.0, 4.0, 8.0, 12.0, 16.0)
    slots = timing.build(20.0, BEATS, ls, Rhythm("line", min_shot_s=2.0, max_shot_s=5.0))
    timing.validate(slots, 20.0)
    starts = [s.start for s in slots]
    for ln in ls:
        assert ln["start"] in starts
    assert [s.lyric for s in slots][:2] == ["line 1", "line 2"]


def test_long_line_splits_on_a_beat_near_the_middle():
    slots = timing.build(20.0, BEATS, lines(0.0, 10.0), Rhythm("line", min_shot_s=2.0, max_shot_s=5.0))
    timing.validate(slots, 20.0)
    assert all(s.dur <= 5.0 + 1e-6 for s in slots)
    inner = [s.start for s in slots][1:]
    assert all(min(abs(b - t) for b in BEATS) < 0.1 for t in inner)


def test_short_line_merges_forward():
    slots = timing.build(20.0, BEATS, lines(0.0, 4.0, 4.8, 9.0, 14.0), Rhythm("line", min_shot_s=2.0,
                                                                             max_shot_s=5.0))
    timing.validate(slots, 20.0)
    assert all(s.dur >= 2.0 - 1e-6 for s in slots[:-1])
    assert any(" / " in s.lyric for s in slots)


def test_beat_unit_groups_beats():
    slots = timing.build(20.0, BEATS, [], Rhythm("beats", beats_per_shot=8, min_shot_s=3.0, max_shot_s=5.0))
    timing.validate(slots, 20.0)
    assert all(abs(s.dur - 4.0) < 0.01 for s in slots)


def test_boundaries_within_0_1s_of_beats_or_lines():
    """Spec 001 US1 independent test: boundaries within 0.1 s of measured beats or line starts."""
    ls = lines(0.0, 3.3, 7.1, 11.6, 15.2)
    slots = timing.build(20.0, BEATS, ls, Rhythm("line"))
    anchors = BEATS + [ln["start"] for ln in ls]
    for s in slots[1:]:
        assert min(abs(a - s.start) for a in anchors) <= 0.1


@pytest.mark.parametrize("seconds,expected", [(2.0, 49), (2.531, 65), (4.0, 97), (0.3, 9)])
def test_frames_cover_the_shot_under_the_ltx_rule(seconds, expected):
    n = frames_for(seconds, round_8k1)
    assert n == expected
    assert n >= seconds * 24 - 1e-6
    assert (n - 1) % 8 == 0


def test_validate_rejects_gaps():
    with pytest.raises(ValueError):
        timing.validate([{"start": 0, "end": 2}, {"start": 2.5, "end": 4}], 4.0)
