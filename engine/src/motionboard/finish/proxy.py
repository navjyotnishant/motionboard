"""Small previews for the Studio (002 T035): a 240 px wide proxy clip and a poster frame next to each clip.

clip clips/shot-03-v2.mp4 -> clips/.previews/shot-03-v2.proxy.mp4 and .poster.jpg, so the clips folder holds only clips. Failure never fails the render."""

import subprocess
from pathlib import Path


def paths(clip: Path) -> tuple[Path, Path]:
    d = clip.parent / ".previews"
    d.mkdir(exist_ok=True)
    return d / f"{clip.stem}.proxy.mp4", d / f"{clip.stem}.poster.jpg"


def make(clip: Path, width: int = 240) -> dict:
    proxy, poster = paths(clip)
    out = {}
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(clip), "-vf",
                        f"scale={width}:-2", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
                        "-movflags", "+faststart", str(proxy)], capture_output=True, text=True)
    if r.returncode == 0:
        out["proxy"] = str(proxy)
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", "0.6", "-i", str(clip),
                        "-frames:v", "1", "-q:v", "3", str(poster)], capture_output=True, text=True)
    if r.returncode == 0 and poster.exists():
        out["poster"] = str(poster)
    return out
