"""Run a heavy command under the memory guard (contracts/guard.md).

1. Wait until free memory reaches the preset start floor.
2. Start the command in its own process group.
3. Sample every poll interval; stop the whole group if free memory falls below
   the kill floor or swap grows past the ceiling. SIGTERM, then SIGKILL after 5 s.
"""

import os
import signal
import sqlite3
import subprocess
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from motionboard.db import repo
from motionboard.guard import monitor
from motionboard.guard.presets import GuardProfile

Sampler = Callable[[int | None], monitor.Sample]
OnSample = Callable[[monitor.Sample], None]

KILL_GRACE_SECONDS = 5.0


@dataclass
class GuardOutcome:
    exit_code: int | None
    stopped: bool
    stop_reason: str | None = None
    peak_rss_mb: int = 0
    min_free_pct: int = 100
    peak_swap_growth_mb: int = 0
    seconds: float = 0.0
    samples: list[monitor.Sample] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.stopped and self.exit_code == 0

    def peak_used_gb(self, total_gb: float) -> float:
        """Memory used by the job at its worst moment, as seen by the system."""
        return round(self.peak_rss_mb / 1024, 2) if self.peak_rss_mb else round(
            total_gb * (100 - self.min_free_pct) / 100, 2
        )


def _stop_group(proc: subprocess.Popen) -> None:
    try:
        pgid = os.getpgid(proc.pid)
    except ProcessLookupError:
        return
    for sig, wait in ((signal.SIGTERM, KILL_GRACE_SECONDS), (signal.SIGKILL, 2.0)):
        try:
            os.killpg(pgid, sig)
        except ProcessLookupError:
            return
        try:
            proc.wait(timeout=wait)
            return
        except subprocess.TimeoutExpired:
            continue


def wait_for_start(
    profile: GuardProfile, sampler: Sampler, timeout: float, on_wait: Callable[[int], None] | None = None
) -> tuple[bool, monitor.Sample]:
    deadline = time.monotonic() + timeout
    s = sampler(None)
    while s.free_pct < profile.start_free_pct:
        if time.monotonic() >= deadline:
            return False, s
        if on_wait:
            on_wait(s.free_pct)
        time.sleep(profile.poll_seconds)
        s = sampler(None)
    return True, s


def run_guarded(
    cmd: Sequence[str],
    profile: GuardProfile,
    *,
    sampler: Sampler = monitor.sample,
    on_sample: OnSample | None = None,
    on_line: Callable[[str], None] | None = None,
    log_path: Path | None = None,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    start_timeout: float = 600.0,
    should_stop: Callable[[], bool] | None = None,
) -> GuardOutcome:
    started, base = wait_for_start(profile, sampler, start_timeout)
    if not started:
        return GuardOutcome(
            exit_code=None,
            stopped=True,
            stop_reason=f"guard: free memory {base.free_pct}% never reached start floor "
            f"{profile.start_free_pct}% within {int(start_timeout)}s",
            min_free_pct=base.free_pct,
        )

    log = open(log_path, "a", buffering=1) if log_path else None  # noqa: SIM115
    t0 = time.monotonic()
    proc = subprocess.Popen(
        list(cmd),
        cwd=cwd,
        env={**os.environ, **(env or {})},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        start_new_session=True,
    )
    os.set_blocking(proc.stdout.fileno(), False)
    out = GuardOutcome(exit_code=None, stopped=False, min_free_pct=base.free_pct)

    def drain() -> None:
        while True:
            try:
                line = proc.stdout.readline()
            except (BlockingIOError, ValueError):
                return
            if not line:
                return
            if log:
                log.write(line)
            if on_line:
                on_line(line.rstrip("\n"))

    try:
        while True:
            drain()
            if proc.poll() is not None:
                break
            s = sampler(proc.pid)
            out.samples.append(s)
            out.peak_rss_mb = max(out.peak_rss_mb, s.rss_mb)
            out.min_free_pct = min(out.min_free_pct, s.free_pct)
            growth = max(0, s.swap_used_mb - base.swap_used_mb)
            out.peak_swap_growth_mb = max(out.peak_swap_growth_mb, growth)
            if on_sample:
                on_sample(s)
            reason = None
            if s.free_pct < profile.kill_free_pct:
                reason = f"guard: free memory {s.free_pct}% < {profile.kill_free_pct}%"
            elif growth > profile.swap_ceiling_mb:
                reason = f"guard: swap grew {growth} MB > {profile.swap_ceiling_mb} MB"
            elif should_stop and should_stop():
                reason = "stopped by request"
            if reason:
                _stop_group(proc)
                out.stopped, out.stop_reason = True, reason
                break
            time.sleep(profile.poll_seconds)
        drain()
        out.exit_code = proc.wait()
    finally:
        if proc.poll() is None:
            _stop_group(proc)
        if log:
            if out.stop_reason:
                log.write(f"\n[motionboard] {out.stop_reason}\n")
            log.close()
    out.seconds = time.monotonic() - t0
    return out


def db_sampler(conn: sqlite3.Connection, job_id: str) -> OnSample:
    """on_sample callback that records memory samples for a render job."""

    def record(s: monitor.Sample) -> None:
        conn.execute(
            "INSERT INTO memory_sample(job_id, at, free_pct, swap_mb, rss_mb) VALUES (?, ?, ?, ?, ?)",
            (job_id, repo.now(), s.free_pct, s.swap_used_mb, s.rss_mb),
        )

    return record


def record_fit_sample(
    conn: sqlite3.Connection, backend: str, mode: str, width: int, height: int, frames: int,
    outcome: GuardOutcome, total_gb: float,
) -> None:
    """After a successful run, store the measured peak so fit estimates improve locally."""
    if not outcome.ok:
        return
    spf = outcome.seconds / frames if frames else None
    conn.execute(
        "INSERT INTO fit_sample(backend, mode, width, height, frames, peak_used_gb, sec_per_frame, machine, at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (backend, mode, width, height, frames, outcome.peak_used_gb(total_gb), spf,
         monitor.machine_label(), repo.now()),
    )
