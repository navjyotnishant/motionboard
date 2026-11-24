"""Regenerate test fixtures. Run: uv run python tests/fixtures/make_fixtures.py

- song10s.wav: 10 s, 44.1 kHz mono, 120 bpm kick on every beat plus a tone that
  changes pitch every 2.5 s (stands in for four sung lines).
- lyrics.txt: four lines matching the tone changes.
- plates/shot-01..04.png: 576x1024 solid colour plates with the shot number.
- export80.json: an 80 shot project export (motionboard.project.v1) for performance tests.
"""

import json
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw

HERE = Path(__file__).parent
SR = 44100


def song() -> None:
    t = np.arange(int(10 * SR)) / SR
    audio = np.zeros_like(t)
    for beat in np.arange(0, 10, 0.5):  # 120 bpm
        idx = int(beat * SR)
        n = int(0.12 * SR)
        env = np.exp(-np.linspace(0, 8, n))
        audio[idx : idx + n] += 0.8 * env * np.sin(2 * np.pi * 60 * np.arange(n) / SR)
    for i, freq in enumerate([220, 262, 294, 247]):
        a, b = int(i * 2.5 * SR), int((i + 1) * 2.5 * SR)
        seg = t[a:b] - t[a]
        fade = np.minimum(1, np.minimum(seg / 0.05, (2.5 - seg) / 0.05))
        audio[a:b] += 0.25 * fade * np.sin(2 * np.pi * freq * t[a:b])
    audio /= np.max(np.abs(audio))
    sf.write(HERE / "song10s.wav", (0.9 * audio).astype(np.float32), SR)


def lyrics() -> None:
    (HERE / "lyrics.txt").write_text(
        "paper boats on a silver river\n"
        "folding wishes into the night\n"
        "every almost drifts a little closer\n"
        "hold the thread and hold it tight\n"
    )


def plates() -> None:
    out = HERE / "plates"
    out.mkdir(exist_ok=True)
    colours = [(40, 52, 70), (70, 40, 52), (40, 70, 52), (70, 62, 40)]
    for i, c in enumerate(colours, start=1):
        img = Image.new("RGB", (576, 1024), c)
        ImageDraw.Draw(img).text((40, 40), f"shot {i:02d}", fill=(230, 230, 230))
        img.save(out / f"shot-{i:02d}.png")


def export80() -> None:
    dur = 80 * 2.0
    shots = [
        {
            "ord": i + 1,
            "start": i * 2.0,
            "end": (i + 1) * 2.0,
            "lyric": f"line {i + 1}",
            "visual": "paper river at night",
            "action": "a paper boat drifts left to right",
            "camera": "slow push in",
            "has_figure": i % 3 == 0,
            "lip_sync": False,
            "plate_prompt": "origami paper river, night, soft light",
            "motion_prompt": "the boat drifts slowly",
            "state": "draft",
            "assets": [],
        }
        for i in range(80)
    ]
    doc = {
        "format": "motionboard.project.v1",
        "project": {
            "title": "perf 80",
            "segment": {"start": 0, "end": dur},
            "aspect": "9:16",
            "look": "stylized",
            "theme": {},
            "template": None,
            "synthetic_people": False,
        },
        "analysis": {
            "tempo_bpm": 120,
            "beats": [round(b * 0.5, 3) for b in range(int(dur * 2))],
            "lines": [
                {"start": s["start"], "end": s["end"], "text": s["lyric"], "source": "beat"} for s in shots
            ],
        },
        "concepts": [],
        "characters": [],
        "shots": shots,
        "approvals": {},
    }
    (HERE / "export80.json").write_text(json.dumps(doc, indent=1))


if __name__ == "__main__":
    song()
    lyrics()
    plates()
    export80()
    print("fixtures written to", HERE)
