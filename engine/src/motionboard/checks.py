"""Checks that catch a bad take or a bad board before the creator has to spot it by eye.

Two failures came out of the first full length video and neither needs a person to find:

- a clip that leaves its plate part way through (the model cuts to another place or another person);
- a sung line that the board only partly gives to the singer, so the voice goes on while the picture
  has moved to something else, or the singer appears mid line.
"""

import re
import subprocess
from pathlib import Path

W, H = 96, 54
CUT_FLOOR = 8.0      # mean absolute grey level change (0 to 255) that a plain move never reaches
CUT_RATIO = 6.0      # ... and how far above the clip's own typical frame change a cut must be
LINE_SLACK = 0.25    # seconds a cut may sit inside a sung line before it counts as splitting it
MIN_SUNG = 0.6       # a singing shot must hold at least this much of a line to count as showing it


def frame_changes(path: Path) -> list[float]:
    """Mean absolute change between neighbouring frames, on a small grey copy of the clip."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"scale={W}:{H},format=gray",
                        "-f", "rawvideo", "-"], capture_output=True)
    size = W * H
    if r.returncode != 0 or len(r.stdout) < 2 * size:
        return []
    import numpy as np  # comes with librosa

    f = np.frombuffer(r.stdout[: len(r.stdout) // size * size], dtype=np.uint8).reshape(-1, size).astype(np.int16)
    return [float(x) for x in np.abs(f[1:] - f[:-1]).mean(axis=1)]


def find_cuts(changes: list[float]) -> list[int]:
    """Frame numbers (the first frame after the jump) where the picture changes like an edit, not a move."""
    if len(changes) < 4:
        return []
    typical = sorted(changes)[len(changes) // 2]
    limit = max(CUT_FLOOR, CUT_RATIO * typical)
    return [i + 1 for i, d in enumerate(changes) if d > limit]


def scene_cuts(path: Path) -> list[int]:
    """Hard scene jumps inside one clip. A clip is one continuous shot, so any jump is a failed take."""
    return find_cuts(frame_changes(path))


def clip_problem(path: Path) -> str | None:
    cuts = scene_cuts(path)
    if not cuts:
        return None
    more = f" and {len(cuts) - 1} more" if len(cuts) > 1 else ""
    return f"scene jumps at frame {cuts[0]}{more}: the clip leaves its plate, render another take"


def split_lines(shots: list[dict], lines: list[dict]) -> list[str]:
    """Sung lines that singing shots show only in part.

    Every clip is rendered on its own, so a line that starts in a singing shot and ends in a shot of
    something else is seen cut off, and a singer who arrives mid line is seen starting mid word.
    A line shared by two or more singing shots is fine as long as together they hold all of it.
    """
    out: list[str] = []
    singing = [s for s in shots if s.get("lip_sync")]
    for ln in lines:
        a, b = float(ln["start"]), float(ln["end"])
        if b - a <= 0:
            continue
        hits = [(s, min(b, s["end"]) - max(a, s["start"])) for s in singing]
        hits = [(s, o) for s, o in hits if o >= MIN_SUNG]
        if not hits:
            continue
        spans = sorted((max(a, s["start"]), min(b, s["end"])) for s, _ in hits)
        gaps, at = [], a
        for x, y in spans:
            if x - at > LINE_SLACK:
                gaps.append((at, x))
            at = max(at, y)
        if b - at > LINE_SLACK:
            gaps.append((at, b))
        if not gaps:
            continue
        ords = ", ".join(str(s["ord"]) for s, _ in hits)
        missing = ", ".join(f"{x:.1f} to {y:.1f} s" for x, y in gaps)
        other = sorted({s["ord"] for s in shots if not s.get("lip_sync")
                        and any(min(y, s["end"]) - max(x, s["start"]) > LINE_SLACK for x, y in gaps)})
        fix = (f"make shot {', '.join(map(str, other))} a singing shot too, or move the cut to the line's edge"
               if other else "move the cut to the line's edge")
        out.append(f"shot {ords} sings only part of \"{ln.get('text', '').strip()}\" ({a:.1f} to {b:.1f} s); "
                   f"{missing} is not on the singer: {fix}")
    return out


# Words that carry no picture: sharing them with the lyric says nothing about how literal a shot is.
_PLAIN = {
    "about", "after", "again", "always", "around", "because", "before", "being", "could", "every", "from",
    "have", "into", "just", "know", "like", "love", "made", "make", "more", "much", "never", "only", "over",
    "said", "some", "still", "than", "that", "them", "then", "there", "they", "this", "those", "through",
    "time", "what", "when", "where", "which", "while", "with", "would", "your", "yours", "youre", "dont",
    "cant", "wont", "mine", "myself", "yourself", "heart", "feel", "want", "need", "come", "came", "back",
    "away", "down", "here",
}


def _picture_words(text: str) -> set[str]:
    words = {w[:-1] if w.endswith("s") and len(w) > 4 else w for w in re.findall(r"[a-z]{4,}", text.lower())}
    return words - _PLAIN


def literal_shots(shots: list[dict]) -> list[str]:
    """Shots that show their lyric word for word.

    A lyric is already heard. A picture that repeats it (the line says a jacket on the door, the shot is
    a jacket on a door) adds nothing, and a whole video of such shots reads as a slideshow of the words.
    The director's job is the meaning under the line, so these are listed for a second look. Singing
    shots are left out: there the singer is the picture.
    """
    out = []
    for s in shots:
        if s.get("lip_sync") or not (s.get("lyric") or "").strip():
            continue
        said = _picture_words(s["lyric"])
        shown = _picture_words(f"{s.get('visual', '')} {s.get('action', '')}")
        same = sorted(said & shown)
        if len(same) >= 2:
            out.append(f"shot {s['ord']} shows its lyric word for word ({', '.join(same)}): "
                       "show what the line means, not what it names")
    return out
