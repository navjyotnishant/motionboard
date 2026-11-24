"""Memory readings. macOS: `memory_pressure` free percent and `sysctl vm.swapusage`
(they count compressed and reclaimable memory the way the kernel does).
Elsewhere: psutil."""

import contextlib
import platform
import re
import subprocess
from dataclasses import dataclass

import psutil

IS_MAC = platform.system() == "Darwin"


@dataclass(frozen=True)
class Sample:
    free_pct: int
    swap_used_mb: int
    total_gb: float
    rss_mb: int = 0  # process group of the guarded job


def total_gb() -> float:
    return psutil.virtual_memory().total / 1024**3


def _mac_free_pct() -> int | None:
    try:
        out = subprocess.run(["memory_pressure"], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    m = re.search(r"free percentage:\s*(\d+)%", out)
    return int(m.group(1)) if m else None


def _mac_swap_used_mb() -> int | None:
    try:
        out = subprocess.run(["sysctl", "vm.swapusage"], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    m = re.search(r"used\s*=\s*([\d.]+)([MG])", out)
    if not m:
        return None
    val = float(m.group(1))
    return int(val * 1024 if m.group(2) == "G" else val)


def group_rss_mb(pid: int | None) -> int:
    """Resident memory of a process and all its children."""
    if not pid:
        return 0
    try:
        root = psutil.Process(pid)
        procs = [root, *root.children(recursive=True)]
    except psutil.Error:
        return 0
    total = 0
    for p in procs:
        with contextlib.suppress(psutil.Error):
            total += p.memory_info().rss
    return int(total / 1024**2)


def sample(pid: int | None = None) -> Sample:
    vm = psutil.virtual_memory()
    free_pct = _mac_free_pct() if IS_MAC else None
    if free_pct is None:
        free_pct = int(round(vm.available / vm.total * 100))
    swap = _mac_swap_used_mb() if IS_MAC else None
    if swap is None:
        swap = int(psutil.swap_memory().used / 1024**2)
    return Sample(free_pct=free_pct, swap_used_mb=swap, total_gb=vm.total / 1024**3, rss_mb=group_rss_mb(pid))


def machine_label() -> str:
    chip = platform.processor() or platform.machine()
    if IS_MAC:
        with contextlib.suppress(OSError, subprocess.TimeoutExpired):
            chip = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True, timeout=5
            ).stdout.strip() or chip
    return f"{chip}, {round(total_gb())} GB"
