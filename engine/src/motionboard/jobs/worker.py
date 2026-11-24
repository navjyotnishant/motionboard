"""The render worker: one job at a time, fit check first, memory guard always (research R10).

Runs until the queue is empty (or forever with --watch). Survives chat and Studio
closing when started with --detach. Pause takes effect after the current shot.
"""

import json
import os
import sqlite3
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path

import psutil

from motionboard import assets, config
from motionboard.audio import vocals
from motionboard.backends import registry
from motionboard.backends.base import ClipJob
from motionboard.db import repo
from motionboard.db.connection import open_db
from motionboard.guard import fitcheck, monitor, presets
from motionboard.guard.run import db_sampler, record_fit_sample, run_guarded
from motionboard.jobs import queue
from motionboard.report import MbError

ACTOR = "worker"


def pid_file() -> Path:
    return config.home() / "worker.pid"


def running_pid() -> int | None:
    p = pid_file()
    if not p.exists():
        return None
    try:
        pid = int(p.read_text().strip())
    except ValueError:
        return None
    if psutil.pid_exists(pid):
        try:
            if "motionboard" in " ".join(psutil.Process(pid).cmdline()):
                return pid
        except psutil.Error:
            return None
    return None


def detach(watch: bool = False) -> int:
    if (pid := running_pid()) is not None:
        return pid
    log = config.home() / "worker.log"
    cmd = [sys.executable, "-m", "motionboard.cli", "worker"] + (["--watch"] if watch else [])
    with open(log, "a") as f:
        proc = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                start_new_session=True, env=os.environ.copy())
    return proc.pid


def _fail(conn, job, shot, reason: str, suggestion: str | None = None, state: str = "failed") -> None:
    repo.update(conn, "render_job", job["id"], {"state": state, "stop_reason": reason, "suggestion": suggestion,
                                                "ended_at": repo.now()}, ACTOR)
    if shot:
        repo.update(conn, "shot", shot["id"], {"state": "clip_failed" if state != "stopped" else "plate_approved",
                                               "updated_at": repo.now()}, ACTOR)


def run_job(conn: sqlite3.Connection, job: dict, sampler=monitor.sample, start_timeout: float = 600.0) -> dict:
    s = json.loads(job["settings"]) if isinstance(job["settings"], str) else job["settings"]
    shot = repo.get(conn, "shot", job["shot_id"]) if job["shot_id"] else None
    project = queue.project_of(conn, job)
    backend = registry.get(job["backend"])
    profile = presets.active(conn)
    repo.update(conn, "render_job", job["id"], {"state": "running", "started_at": repo.now(), "progress": 0}, ACTOR)
    if shot:
        repo.update(conn, "shot", shot["id"], {"state": "clip_rendering", "updated_at": repo.now()}, ACTOR)

    now = sampler(None)
    eff = replace(now, free_pct=max(now.free_pct, profile.start_free_pct))
    fit = fitcheck.fit(backend, s["mode"], s["width"], s["height"], s["frames"], profile, conn, eff)
    if not fit.fits:
        _fail(conn, job, shot, f"fit check: {fit.summary()}", "; ".join(fit.suggestions))
        return {"job": job["id"], "ok": False, "reason": fit.summary()}

    audio, isolated = None, None
    if s["mode"] == "a2v" and shot:
        try:
            audio, isolated = vocals.shot_vocal(Path(project["folder"]), shot, profile)
        except MbError as e:
            _fail(conn, job, shot, e.message)
            return {"job": job["id"], "ok": False, "reason": e.message}

    out = Path(s["out"])
    out.parent.mkdir(parents=True, exist_ok=True)
    clip = ClipJob(s["mode"], Path(s["plate"]), s["prompt"], s["width"], s["height"], s["frames"], out,
                   s.get("fps", 24), s.get("seed", 42), audio)
    try:
        cmd = backend.build_command(clip)
    except (FileNotFoundError, ValueError) as e:
        _fail(conn, job, shot, str(e), "run mb setup")
        return {"job": job["id"], "ok": False, "reason": str(e)}

    watcher = open_db()
    last = {"t": 0.0}

    def on_line(line: str) -> None:
        p = backend.parse_progress(line)
        if p is None:
            return
        frac = p / s["frames"] if p > 1 else p
        if time.monotonic() - last["t"] > 2 or frac >= 1:
            last["t"] = time.monotonic()
            watcher.execute("UPDATE render_job SET progress = ? WHERE id = ?", (round(min(frac, 1.0), 3), job["id"]))

    def should_stop() -> bool:
        r = watcher.execute("SELECT state FROM render_job WHERE id = ?", (job["id"],)).fetchone()
        return bool(r and r[0] == "stopped")

    sample_rec = db_sampler(watcher, job["id"])
    outcome = run_guarded(cmd, profile, sampler=sampler, on_sample=sample_rec, on_line=on_line,
                          log_path=Path(job["log_path"]) if job["log_path"] else None,
                          start_timeout=start_timeout, should_stop=should_stop)
    watcher.close()
    spf = round(outcome.seconds / s["frames"], 2) if s["frames"] and outcome.seconds else None
    if outcome.stopped:
        requested = outcome.stop_reason == "stopped by request"
        _fail(conn, job, shot, outcome.stop_reason or "stopped",
              None if requested else "; ".join(fit.suggestions) or "try fewer frames or a smaller size",
              state="stopped" if requested else "failed")
        return {"job": job["id"], "ok": False, "reason": outcome.stop_reason}
    if outcome.exit_code != 0 or not out.exists():
        _fail(conn, job, shot, f"backend exited with code {outcome.exit_code}; see {job['log_path']}")
        return {"job": job["id"], "ok": False, "reason": f"exit {outcome.exit_code}"}
    info = assets.probe(out)
    problems = []
    if abs(info["frames"] - s["frames"]) > 1:
        problems.append(f"expected {s['frames']} frames, got {info['frames']}")
    if (info["width"], info["height"]) != (s["width"], s["height"]):
        problems.append(f"expected {s['width']}x{s['height']}, got {info['width']}x{info['height']}")
    record_fit_sample(conn, backend.name, s["mode"], s["width"], s["height"], s["frames"], outcome,
                      monitor.total_gb())
    if shot:
        assets.add(conn, shot["id"], "clip", out, backend.name, ACTOR)
        repo.update(conn, "shot", shot["id"], {"state": "clip_ready", "dirty": False, "updated_at": repo.now()},
                    ACTOR)
    repo.update(conn, "render_job", job["id"], {
        "state": "done", "progress": 1.0, "sec_per_frame": spf, "ended_at": repo.now(),
        "stop_reason": "; ".join(problems) or None}, ACTOR)
    return {"job": job["id"], "ok": True, "shot": shot["ord"] if shot else None, "out": str(out),
            "seconds": round(outcome.seconds, 1), "sec_per_frame": spf, "probe": info, "problems": problems,
            "vocal_isolated": isolated}


def run(watch: bool = False, sampler=monitor.sample, idle_poll: float = 3.0, max_jobs: int | None = None) -> list[dict]:
    conn = open_db()
    results: list[dict] = []
    pid_file().write_text(str(os.getpid()))
    try:
        while max_jobs is None or len(results) < max_jobs:
            if queue.paused(conn):
                if not watch:
                    break
                time.sleep(idle_poll)
                continue
            job = queue.next_job(conn)
            if job is None:
                if not watch:
                    break
                time.sleep(idle_poll)
                continue
            results.append(run_job(conn, job, sampler))
    finally:
        try:
            if pid_file().read_text().strip() == str(os.getpid()):
                pid_file().unlink()
        except OSError:
            pass
        conn.close()
    return results
