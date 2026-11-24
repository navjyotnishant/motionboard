"""Plates and clips stage commands: adapter, plates, plate, review, clips, worker, queue."""

import json
from dataclasses import replace
from pathlib import Path

import typer

from motionboard import projects
from motionboard.backends import registry
from motionboard.cli import JsonOpt, app, run
from motionboard.db import repo
from motionboard.guard import fitcheck, monitor, presets
from motionboard.jobs import queue, worker
from motionboard.plates import adapter as adapters
from motionboard.plates import service as plates
from motionboard.report import MbError
from motionboard.storyboard import board

plate_app = typer.Typer(no_args_is_help=True, help="Plate requests and uploads")
queue_app = typer.Typer(help="Render queue")
app.add_typer(plate_app, name="plate")
app.add_typer(queue_app, name="queue")

ProjectOpt = typer.Option(..., "--project", "-p", help="Project id (or its last characters)")


def _ords(shots: str | None) -> list[int] | None:
    if not shots:
        return None
    try:
        return [int(x) for x in shots.replace(" ", "").split(",") if x]
    except ValueError as e:
        raise MbError("INVALID_INPUT", "--shots takes numbers like 3,7,12") from e


@app.command()
def adapter(
    list_: bool = typer.Option(False, "--list"),
    add: str = typer.Option(None, "--add", help="Name of a new adapter"),
    kind: str = typer.Option(None, "--kind", help="manual, command, http or handoff"),
    config_json: str = typer.Option("{}", "--config", help="JSON config; keys as key_file or key_env only"),
    cost: float = typer.Option(0.0, "--cost", help="Cost per image in USD"),
    as_json: bool = JsonOpt,
) -> None:
    """List or add plate adapters (any image source: local model, MCP tool, API, your own files)."""

    def go(conn, r):
        adapters.ensure_default_manual(conn)
        if add:
            try:
                cfg = json.loads(config_json)
            except json.JSONDecodeError as e:
                raise MbError("INVALID_INPUT", f"--config is not valid JSON: {e}") from e
            if not kind:
                raise MbError("INVALID_INPUT", "--add needs --kind")
            adapters.add(conn, add, kind, cfg, cost, "chat")
            r.verified.append(f"adapter '{add}' added")
        r.data = {"adapters": [{"name": a["name"], "kind": a["kind"], "cost_per_image_usd": a["cost_per_image_usd"],
                                "config": json.loads(a["config"])} for a in repo.find(conn, "plate_adapter",
                                                                                       order="name")]}

    run("mb adapter", as_json, go)


@app.command("plates")
def plates_cmd(
    project: str = ProjectOpt,
    adapter_name: str = typer.Option("manual", "--adapter"),
    shots: str = typer.Option(None, "--shots", help="Only these shot numbers, e.g. 3,7"),
    confirm_cost: bool = typer.Option(False, "--confirm-cost", help="The creator approved the stated cost"),
    as_json: bool = JsonOpt,
) -> None:
    """Request plates for shots that need them. Paid adapters refuse until the cost is confirmed."""

    def go(conn, r):
        p = projects.get(conn, project)
        r.project = p["id"]
        res = plates.request_plates(conn, p, adapter_name, _ords(shots), confirm_cost, "chat")
        r.data = res
        if res["done"]:
            r.verified.append(f"{len(res['done'])} plates stored and set active")
        if res["pending"]:
            r.not_verified.append(f"{len(res['pending'])} plates pending: fulfil with mb plate fulfil "
                                  "or drop files into plates/inbox")
        if res["failed"]:
            r.not_verified.append(f"{len(res['failed'])} plates failed")
        r.next = f"mb sheet --project {p['id']} --kind plates"

    run("mb plates", as_json, go)


@plate_app.command("requests")
def plate_requests(project: str = ProjectOpt, as_json: bool = JsonOpt) -> None:
    """List pending plate requests (for handoff to an MCP image tool)."""

    def go(conn, r):
        p = projects.get(conn, project)
        r.project = p["id"]
        r.data = {"pending": plates.pending_requests(conn, p["id"]), "size": "x".join(
            map(str, plates.PLATE_SIZES[p["aspect"]]))}

    run("mb plate requests", as_json, go)


@plate_app.command("fulfil")
def plate_fulfil(project: str = ProjectOpt, request: str = typer.Option(..., "--request"),
                 file: Path = typer.Option(..., "--file"), as_json: bool = JsonOpt) -> None:
    """Attach an image to a pending request."""

    def go(conn, r):
        p = projects.get(conn, project)
        r.project = p["id"]
        a = plates.fulfil(conn, p, request, file, "chat")
        r.data = {"plate": a["path"]}

    run("mb plate fulfil", as_json, go)


@plate_app.command("upload")
def plate_upload(project: str = ProjectOpt, shot: int = typer.Option(..., "--shot"),
                 file: Path = typer.Option(..., "--file"), as_json: bool = JsonOpt) -> None:
    """Use your own image as a shot's plate."""

    def go(conn, r):
        p = projects.get(conn, project)
        r.project = p["id"]
        a = plates.upload(conn, p, shot, file, "chat")
        r.data = {"plate": a["path"]}

    run("mb plate upload", as_json, go)


@app.command()
def review(
    project: str = ProjectOpt,
    shot: int = typer.Option(..., "--shot"),
    kind: str = typer.Option("plate", "--kind", help="plate or clip"),
    decision: str = typer.Option(..., "--decision", help="approve, reject or comment"),
    note: str = typer.Option("", "--note"),
    all_shots: bool = typer.Option(False, "--all", help="Apply to every shot that has one (approve only)"),
    as_json: bool = JsonOpt,
) -> None:
    """Approve or reject a shot's active plate or clip, with a note."""
    from motionboard import assets

    def go(conn, r):
        p = projects.get(conn, project)
        r.project = p["id"]
        if all_shots:
            if decision != "approve":
                raise MbError("INVALID_INPUT", "--all only works with approve")
            done = []
            for s in conn.execute("SELECT * FROM shot WHERE project_id = ? ORDER BY ord", (p["id"],)).fetchall():
                ready = "plate_ready" if kind == "plate" else "clip_ready"
                if s["state"] == ready:
                    assets.review(conn, dict(s), kind, "approve", note, "chat")
                    done.append(s["ord"])
            r.data = {"approved": done}
            return
        s = board.shot_by_ord(conn, p["id"], shot)
        s = assets.review(conn, s, kind, decision, note, "chat")
        r.data = {"shot": shot, "state": s["state"]}

    run("mb review", as_json, go)


@app.command()
def clips(
    project: str = ProjectOpt,
    shots: str = typer.Option(None, "--shots"),
    redo: bool = typer.Option(False, "--redo", help="Render again even if a finished clip exists"),
    preset: str = typer.Option(None, "--preset", help="Guard preset to make active for this run"),
    as_json: bool = JsonOpt,
) -> None:
    """Queue clip renders for approved plates (fit check first). Start them with mb worker."""

    def go(conn, r):
        p = projects.get(conn, project)
        r.project = p["id"]
        board.require_gates(conn, p["id"], "storyboard", "plates")
        if preset:
            presets.set_active(conn, preset, "chat")
        profile = presets.active(conn)
        b = registry.get(p["video_backend"])
        inst = b.check_installed()
        if not inst.installed:
            raise MbError("MISSING_MODEL", f"{b.name} is not ready: {'; '.join(inst.missing)}", hint="mb setup")
        w, h = b.sizes[p["aspect"]]
        now = monitor.sample()
        eff = replace(now, free_pct=max(now.free_pct, profile.start_free_pct))
        rows = conn.execute("SELECT DISTINCT frames, lip_sync FROM shot WHERE project_id = ?", (p["id"],)).fetchall()
        worst = max(rows, key=lambda x: x[0])
        fit = fitcheck.fit(b, "a2v" if worst[1] else "i2v", w, h, b.frame_rule(worst[0]), profile, conn, eff)
        if not fit.fits:
            raise MbError("FIT_REFUSED", fit.summary(), hint="; ".join(fit.suggestions))
        res = queue.enqueue_clips(conn, p, b, _ords(shots), redo, "chat")
        r.data = {**res, "guard": profile.describe(), "fit_longest_shot": fit.summary(),
                  "est_minutes": round(sum((fit.est_seconds or 0) / max(1, worst[0]) * q["frames"]
                                           for q in res["queued"]) / 60, 1)}
        r.verified.append(f"fit check passed for the longest shot ({worst[0]} frames)")
        r.not_verified.append("render time is an estimate")
        r.next = "mb worker --detach"

    run("mb clips", as_json, go)


@app.command("worker")
def worker_cmd(
    detach: bool = typer.Option(False, "--detach", help="Run in the background and return"),
    watch: bool = typer.Option(False, "--watch", help="Keep waiting for new jobs"),
    as_json: bool = JsonOpt,
) -> None:
    """Render queued jobs one at a time under the memory guard."""

    def go(conn, r):
        if detach:
            pid = worker.detach(watch)
            r.data = {"pid": pid, "log": str(worker.pid_file().with_name("worker.log"))}
            r.verified.append("worker running in the background")
            return
        if worker.running_pid():
            raise MbError("INVALID_INPUT", "a worker is already running", hint="mb queue to watch it")
        res = worker.run(watch=watch)
        r.data = {"jobs": res}
        ok = [x for x in res if x["ok"]]
        r.verified.append(f"{len(ok)} of {len(res)} jobs finished; frame count and size checked with ffprobe")
        if any(x.get("vocal_isolated") is False for x in res):
            r.not_verified.append("lip-sync used the full mix; install the vocals extra to isolate the voice")
        if len(ok) < len(res):
            r.not_verified.append("some jobs failed or were stopped; see each job's reason")

    run("mb worker", as_json, go)


@queue_app.callback(invoke_without_command=True)
def queue_cmd(
    ctx: typer.Context,
    project: str = typer.Option(None, "--project", "-p"),
    pause: bool = typer.Option(False, "--pause", help="Pause after the current shot"),
    resume: bool = typer.Option(False, "--resume"),
    stop: bool = typer.Option(False, "--stop", help="Stop the running job now and clear the queue"),
    move: str = typer.Option(None, "--move", help="JOB:POSITION"),
    as_json: bool = JsonOpt,
) -> None:
    """Show the render queue, or pause, resume, stop, reorder."""

    def go(conn, r):
        pid = projects.get(conn, project)["id"] if project else None
        if pause:
            queue.pause(conn, "chat")
        if resume:
            queue.resume(conn, "chat")
        if stop:
            r.data["stopped"] = queue.stop(conn, pid, "chat")
        if move:
            jid, pos = move.rsplit(":", 1)
            queue.move(conn, jid, int(pos), "chat")
        js = queue.jobs(conn, pid)
        last = {}
        for j in js:
            row = conn.execute("SELECT free_pct, swap_mb, rss_mb, at FROM memory_sample WHERE job_id = ? "
                               "ORDER BY at DESC LIMIT 1", (j["id"],)).fetchone()
            if row:
                last[j["id"]] = dict(row)
        r.data.update({
            "paused": queue.paused(conn), "worker_pid": worker.running_pid(),
            "guard": presets.active(conn).describe(),
            "jobs": [{"id": j["id"], "shot": j["shot_ord"], "kind": j["kind"], "state": j["state"],
                      "progress": j["progress"], "frames": j["settings"].get("frames"),
                      "memory": last.get(j["id"])} for j in js],
        })

    run("mb queue", as_json, go)
