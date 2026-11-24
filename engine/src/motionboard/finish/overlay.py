"""Animation packs (Motionboard IP): load the pack, write its config, render its layers with HyperFrames.

Pack contract (modes/<mode>/animation/pack.json):
  layers: {"matte": {"file", "blend": "multiply"}, "overlay": {"file", "blend": "screen"}}
  cover: html file for the cover, tail_seconds, aspects, theme_keys, fonts
HTML files may use __DURATION__, __W__ and __H__; the engine writes js/config.js as window.MB.
HyperFrames renders in the foreground (a detached render was cancelled in the Almost Yours build).
"""

import json
import shutil
import subprocess
from pathlib import Path

from motionboard import config
from motionboard.finish.assemble import DELIVERY
from motionboard.guard.presets import GuardProfile
from motionboard.guard.run import run_guarded
from motionboard.report import MbError

HYPERFRAMES = "hyperframes@0.9.84"


def pack_dir(name: str) -> Path:
    d = config.repo_root() / "modes" / name / "animation"
    if not (d / "pack.json").exists():
        raise MbError("NOT_FOUND", f"no animation pack '{name}'", hint="packs live in modes/<mode>/animation/")
    return d


def load_pack(name: str) -> dict:
    p = json.loads((pack_dir(name) / "pack.json").read_text())
    for key in ("name", "layers", "aspects"):
        if key not in p:
            raise MbError("INVALID_INPUT", f"pack '{name}' is missing '{key}'")
    return p


def downbeats(beats: list[float], every: int = 4) -> list[float]:
    return [round(b, 3) for b in beats[::every]]


def make_config(project: dict, analysis: dict, shots: list[dict], tail: float) -> dict:
    w, h = DELIVERY[project["aspect"]]
    music = round(shots[-1]["end"], 3)
    theme = json.loads(project.get("theme") or "{}")
    return {
        "width": w, "height": h, "fps": 24,
        "music_end": music, "duration": round(music + tail, 3),
        "lines": [{"start": ln["start"], "end": ln["end"], "text": ln["text"]} for ln in analysis.get("lines", [])],
        "cuts": [round(s["start"], 3) for s in shots[1:]],
        "downbeats": downbeats(analysis.get("beats", [])),
        "chorus": theme.get("chorus"),
        "theme": theme,
    }


def prepare(pack_name: str, cfg: dict, workdir: Path) -> Path:
    src = pack_dir(pack_name)
    if workdir.exists():
        shutil.rmtree(workdir)
    shutil.copytree(src, workdir)
    for html in workdir.glob("*.html"):
        text = html.read_text()
        text = (text.replace("__DURATION__", f"{cfg['duration']:.3f}").replace("__W__", str(cfg["width"]))
                .replace("__H__", str(cfg["height"])))
        html.write_text(text)
    (workdir / "js").mkdir(exist_ok=True)
    (workdir / "js" / "config.js").write_text("window.MB = " + json.dumps(cfg, indent=1) + ";\n")
    (workdir / "package.json").write_text(json.dumps({"name": f"mb-{pack_name}", "private": True,
                                                      "type": "module"}, indent=2))
    return workdir


def render_layer(workdir: Path, html: str, out: Path, fps: int, profile: GuardProfile, fmt: str = "mp4") -> Path:
    cmd = ["npx", "--yes", HYPERFRAMES, "render", str(workdir), "-c", html, "-o", str(out), "-f", str(fps),
           "--quiet"]
    if fmt != "mp4":
        cmd += ["--format", fmt]
    res = run_guarded(cmd, profile, cwd=workdir, log_path=out.with_suffix(".log") if fmt == "mp4" else
                      workdir / f"{Path(html).stem}.log")
    if res.stopped:
        raise MbError("GUARD_STOPPED", res.stop_reason or "render stopped")
    if res.exit_code != 0 or not out.exists():
        raise MbError("MISSING_TOOL" if res.exit_code == 127 else "INTERNAL",
                      f"HyperFrames render of {html} failed (exit {res.exit_code}); see the log in {workdir}")
    return out


def render_cover(workdir: Path, background: Path, out: Path, profile: GuardProfile) -> Path:
    shutil.copy2(background, workdir / "cover-bg.jpg")
    seq = workdir / "cover-frames"
    render_layer(workdir, "cover.html", seq, 1, profile, fmt="png-sequence")
    frames = sorted(seq.glob("*.png"))
    if not frames:
        raise MbError("INTERNAL", "cover render produced no frame")
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(frames[0]), "-q:v", "2", str(out)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise MbError("INTERNAL", f"cover conversion failed: {r.stderr.strip()}")
    return out
