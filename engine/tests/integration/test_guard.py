"""Guard stops a running job when memory gets tight, records why, and never leaves it running."""

import sys
import time

import psutil

from motionboard.guard.monitor import Sample
from motionboard.guard.presets import GuardProfile
from motionboard.guard.run import run_guarded

TIGHT = GuardProfile("tight", start_free_pct=40, kill_free_pct=20, swap_ceiling_mb=500, poll_seconds=0.1)

# A child that allocates memory in steps and would run for a minute if not stopped.
HOG = [
    sys.executable, "-c",
    "import time\nblocks=[]\nfor _ in range(600):\n    blocks.append(bytearray(1024*1024))\n    time.sleep(0.1)",
]


class FakeMemory:
    """Free memory falls by 5 points per sample; swap optionally grows."""

    def __init__(self, free=60, step=5, swap_step=0):
        self.free, self.step, self.swap, self.swap_step = free, step, 1000, swap_step
        self.pids = []

    def __call__(self, pid):
        if pid:
            self.pids.append(pid)
            self.free -= self.step
            self.swap += self.swap_step
        return Sample(free_pct=self.free, swap_used_mb=self.swap, total_gb=36.0, rss_mb=100)


def test_guard_stops_on_low_free_memory(tmp_path):
    mem = FakeMemory()
    log = tmp_path / "job.log"
    t0 = time.monotonic()
    out = run_guarded(HOG, TIGHT, sampler=mem, log_path=log)
    assert out.stopped
    assert out.stop_reason.startswith("guard: free memory")
    assert "< 20%" in out.stop_reason
    assert time.monotonic() - t0 < 10
    assert not psutil.pid_exists(mem.pids[0]) or psutil.Process(mem.pids[0]).status() == psutil.STATUS_ZOMBIE
    assert "[motionboard] guard: free memory" in log.read_text()


def test_guard_stops_on_swap_growth():
    mem = FakeMemory(free=90, step=0, swap_step=200)
    out = run_guarded(HOG, TIGHT, sampler=mem)
    assert out.stopped
    assert out.stop_reason.startswith("guard: swap grew")


def test_guard_waits_for_start_floor_then_gives_up():
    mem = FakeMemory(free=30, step=0)
    out = run_guarded(HOG, TIGHT, sampler=mem, start_timeout=0.3)
    assert out.stopped and out.exit_code is None
    assert "never reached start floor 40%" in out.stop_reason
    assert mem.pids == []  # job never started


def test_guard_lets_a_normal_job_finish():
    mem = FakeMemory(free=90, step=0)
    out = run_guarded([sys.executable, "-c", "print('done')"], TIGHT, sampler=mem)
    assert out.ok and out.exit_code == 0 and not out.stopped


def test_stop_request_stops_job():
    mem = FakeMemory(free=90, step=0)
    calls = {"n": 0}

    def should_stop():
        calls["n"] += 1
        return calls["n"] > 3

    out = run_guarded(HOG, TIGHT, sampler=mem, should_stop=should_stop)
    assert out.stopped and out.stop_reason == "stopped by request"
