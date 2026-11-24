"""Final cut with ffmpeg (research R8), ported from the Almost Yours assemble.py.

picture: each clip trimmed to its shot's frames, upscaled with lanczos, joined
   -> grade (eq, curves, unsharp) -> x matte (multiply) -> + overlay (screen) -> fine grain
audio: the analysed segment, padded for the tail. Last frame held for the tail.
"""

from dataclasses import dataclass
from pathlib import Path

DELIVERY = {"9:16": (1080, 1920), "16:9": (1920, 1080)}
GRADE = ("eq=contrast=1.07:saturation=1.10:gamma=0.97,"
         "curves=m='0/0 0.10/0.065 0.5/0.5 1/1':r='0/0 0.5/0.52 1/1':b='0/0.012 0.5/0.49 1/0.97',"
         "unsharp=5:5:0.55:3:3:0")


@dataclass
class Plan:
    cmd: list[str]
    cut_frames: list[int]       # frame index where each shot starts, plus the end
    total_frames: int
    duration: float


def cut_frames(shots: list[dict], fps: int) -> list[int]:
    return [round(s["start"] * fps) for s in shots] + [round(shots[-1]["end"] * fps)]


def build(shots: list[dict], clips: list[Path], audio: Path, out: Path, aspect: str, fps: int = 24,
          overlay: Path | None = None, matte: Path | None = None, tail: float = 1.5, grain: int = 3,
          crf: int = 19) -> Plan:
    if len(shots) != len(clips):
        raise ValueError("one clip per shot is required")
    w, h = DELIVERY[aspect]
    frames = cut_frames(shots, fps)
    inputs: list[str] = []
    parts = []
    for i, clip in enumerate(clips):
        n = frames[i + 1] - frames[i]
        inputs += ["-i", str(clip)]
        parts.append(f"[{i}:v]fps={fps},tpad=stop_mode=clone:stop_duration=1,trim=end_frame={n},"
                     f"setpts=PTS-STARTPTS,scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,"
                     f"crop={w}:{h},setsar=1[v{i}]")
    k = len(clips)
    graph = ";".join(parts) + ";" + "".join(f"[v{i}]" for i in range(k)) + f"concat=n={k}:v=1:a=0[cut]"
    inputs += ["-i", str(audio)]
    a_idx = k
    chain = f";[cut]tpad=stop_mode=clone:stop_duration={tail},{GRADE},format=gbrp[bg]"
    last = "bg"
    nxt = k + 1
    if matte:
        inputs += ["-i", str(matte)]
        chain += (f";[{nxt}:v]fps={fps},scale={w}:{h},format=gbrp[mt]"
                  f";[{last}][mt]blend=all_mode=multiply:shortest=1[dim]")
        last, nxt = "dim", nxt + 1
    if overlay:
        inputs += ["-i", str(overlay)]
        chain += f";[{nxt}:v]fps={fps},scale={w}:{h},format=gbrp[ov];[{last}][ov]blend=all_mode=screen:shortest=1[lit]"
        last = "lit"
    chain += f";[{last}]format=yuv420p,noise=alls={grain}:allf=t[v];[{a_idx}:a]apad=pad_dur={tail}[a]"
    graph += chain
    duration = frames[-1] / fps + tail
    cmd = ["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", graph, "-map", "[v]", "-map", "[a]",
           "-t", f"{duration:.3f}", "-c:v", "libx264", "-crf", str(crf), "-preset", "medium", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", str(out)]
    return Plan(cmd, frames, round(duration * fps), round(duration, 3))
