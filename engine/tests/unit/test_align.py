"""Line alignment on a segment of a song whose chorus repeats (real bug: the whole sheet was required to match)."""

from motionboard.audio.align import match_lines

LYRICS = [
    "your name lights up my wall", "two am you start to call",
    "you only miss me in the dark", "only love me when you're lost",
    "maybe i was just the place", "you ran to when you couldn't face",
    "you only miss me in the dark", "only love me when you're lost",
    "you don't call me when the sun is up",
]


def words_for(lines, start=1.0, step=0.4):
    out, t = [], start
    for ln in lines:
        for w in ln.split():
            out.append((w, t, t + 0.3))
            t += step
        t += 0.8
    return out


def test_segment_matches_only_the_lines_it_holds():
    heard = words_for(LYRICS[4:8])  # bridge and the last chorus
    lines = match_lines(LYRICS, heard, 30.0)
    assert lines is not None
    assert [ln.text for ln in lines] == LYRICS[4:8]
    assert lines[0].start > 0.5 and all(ln.source == "aligned" for ln in lines)
    assert all(a.end <= b.start + 1e-6 for a, b in zip(lines, lines[1:], strict=False))


def test_no_match_returns_none():
    assert match_lines(LYRICS, [("completely", 0.0, 0.3), ("different", 0.4, 0.7)], 10.0) is None
