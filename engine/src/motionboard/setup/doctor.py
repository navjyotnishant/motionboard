"""Setup check (T064): machine, tools, models. Reports and prints steps; never installs or downloads."""

import importlib.util
import platform
import shutil
import subprocess
from pathlib import Path

import psutil

from motionboard.backends.ltx23 import LTX23Backend, find_snapshot
from motionboard.guard import monitor
from motionboard.setup.models import CATALOG

MIN_MEMORY_GB = 32
HYPERFRAMES = "hyperframes@0.9.84"


def _version(cmd: list[str]) -> str | None:
    if not shutil.which(cmd[0]):
        return None
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    text = (out.stdout or out.stderr).strip().splitlines()
    return text[0] if out.returncode == 0 and text else None


def _partial(repo: str) -> bool:
    blobs = Path.home() / ".cache" / "huggingface" / "hub" / f"models--{repo.replace('/', '--')}" / "blobs"
    return blobs.is_dir() and any(p.suffix == ".incomplete" for p in blobs.iterdir())


def check(probe_hyperframes: bool = True) -> dict:
    vm = psutil.virtual_memory()
    disk = psutil.disk_usage(str(Path.home()))
    s = monitor.sample()
    machine = {
        "chip": monitor.machine_label(),
        "os": f"{platform.system()} {platform.mac_ver()[0] or platform.release()}",
        "apple_silicon": platform.system() == "Darwin" and platform.machine() == "arm64",
        "memory_gb": round(vm.total / 1024**3, 1),
        "free_memory_pct": s.free_pct,
        "swap_used_mb": s.swap_used_mb,
        "free_disk_gb": round(disk.free / 1024**3, 1),
    }
    ltx = LTX23Backend()
    tools = {
        "uv": _version(["uv", "--version"]),
        "ffmpeg": _version(["ffmpeg", "-version"]),
        "ffprobe": _version(["ffprobe", "-version"]),
        "node": _version(["node", "-v"]),
        "hyperframes": _version(["npx", "--yes", HYPERFRAMES, "--version"]) if probe_hyperframes else "not probed",
        "ltx-2-mlx": ltx.bin if Path(ltx.bin).exists() else None,
        "hf": _version(["hf", "version"]) or _version([str(Path(ltx.bin).with_name("hf")), "version"]),
        "mlx_whisper (align extra)": "installed" if importlib.util.find_spec("mlx_whisper") else None,
        "demucs (vocals extra)": "installed" if importlib.util.find_spec("demucs") else None,
    }
    models = []
    for m in CATALOG:
        snap = m.present() if not m.repo.startswith("(") else None
        status = "present" if snap else ("partial download" if not m.repo.startswith("(") and _partial(m.repo)
                                         else "missing")
        if m.key == "demucs":
            status = "present" if tools["demucs (vocals extra)"] else "missing"
        if m.key == "whisper":
            status = "present" if find_snapshot(m.repo) else "missing"
        models.append({"key": m.key, "repo": m.repo, "role": m.role, "status": status, "approx_gb": m.approx_gb,
                       "licence": m.licence, "licence_url": m.licence_url, "optional": m.optional,
                       "backlog": m.backlog, "path": str(snap) if snap else None})
    gaps = []
    if not machine["apple_silicon"]:
        gaps.append("Not an Apple Silicon Mac: the LTX MLX backend will not run; the rest of Motionboard will.")
    if machine["memory_gb"] < MIN_MEMORY_GB:
        gaps.append(f"{machine['memory_gb']} GB memory: use the safe guard preset and smaller shots.")
    for t in ("uv", "ffmpeg", "ffprobe", "node"):
        if not tools[t]:
            gaps.append(f"{t} is missing")
    if not tools["ltx-2-mlx"]:
        gaps.append("ltx-2-mlx is missing")
    need_disk = sum(m["approx_gb"] for m in models if m["status"] != "present" and not m["optional"]
                    and not m["backlog"])
    if need_disk and machine["free_disk_gb"] < need_disk + 10:
        gaps.append(f"needs about {need_disk:.0f} GB for models; {machine['free_disk_gb']} GB free")
    gaps += [f"model {m['key']} is {m['status']}" for m in models
             if m["status"] != "present" and not m["optional"] and not m["backlog"]]
    return {"machine": machine, "tools": tools, "models": models, "gaps": gaps,
            "ready_for_clips": not any(g.startswith(("ltx-2-mlx", "model ltx23", "model gemma")) for g in gaps)}


def fix_plan(report: dict) -> list[str]:
    steps = []
    t = report["tools"]
    if not t["uv"]:
        steps.append("brew install uv")
    if not t["ffmpeg"] or not t["ffprobe"]:
        steps.append("brew install ffmpeg")
    if not t["node"]:
        steps.append("brew install node")
    if not t["ltx-2-mlx"]:
        steps += ["git clone https://github.com/dgrauet/ltx-2-mlx ~/dev/ltx-2-mlx",
                  "cd ~/dev/ltx-2-mlx && uv venv --python 3.12 && uv pip install -e .",
                  "export MB_LTX_BIN=~/dev/ltx-2-mlx/.venv/bin/ltx-2-mlx"]
    for m in CATALOG:
        row = next(r for r in report["models"] if r["key"] == m.key)
        if row["status"] == "present" or m.backlog:
            continue
        if m.repo.startswith("("):
            steps += [f"# {m.role}: {n}" for n in m.notes]
            continue
        steps.append(f"# {m.role} ({m.approx_gb:.0f} GB). Licence: {m.licence} {m.licence_url}")
        steps += [f"# {n}" for n in m.notes]
        steps.append(m.download_command())
    return steps
