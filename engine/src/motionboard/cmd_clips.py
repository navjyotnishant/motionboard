"""Plates and clips stage commands: adapter, plates, plate, review, clips, worker, queue."""

import json
from dataclasses import replace
from pathlib import Path

import typer

from motionboard import assets, projects
from motionboard.backends import registry
from motionboard.cli import JsonOpt, app, run
from motionboard.config import ACTOR
from motionboard.db import repo
from motionboard.guard import fitcheck, monitor, presets
from motionboard.jobs import queue, worker
from motionboard.plates import adapter as adapters
from motionboard.plates import service as plates
from motionboard.report import MbError
from motionboard.storyboard import board, templates

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
            adapters.add(conn, add, kind, cfg, cost, ACTOR())
            r.verified.append(f"adapter '{add}' added")
        out = []
        for a in repo.find(conn, "plate_adapter", order="name"):
            cfg = json.loads(a["config"])
            # manual adapters wait for files the creator drops in; they show every reference and need no build
            n = None if a["kind"] == "manual" else adapters.build(a, {}).reference_capacity()
            out.append({"name": a["name"], "kind": a["kind"], "cost_per_image_usd": a["cost_per_image_usd"],
                        "config": cfg, "reference_capacity": "unlimited" if n is None else n,
                        "reference_strategy": cfg.get("reference_strategy", "strict")})
        r.data = {"adapters": out}

    run("mb adapter", as_json, go)


@app.command("plates")
def plates_cmd(
    project: str = ProjectOpt,
    adapter_name: str = typer.Option("manual", "--adapter"),
    shots: str = typer.Option(None, "--shots", help="Only these shot numbers, e.g. 3,7"),
    confirm_cost: bool = typer.Option(False, "--confirm-cost", help="The creator approved the stated cost"),
    reference_strategy: str = typer.Option(None, "--reference-strategy",
                                           help="When a shot has more references than the adapter takes: strict "
                                                "(stop), primary, first or none"),
    accept_conflicts: bool = typer.Option(False, "--accept-conflicts",
                                          help="The creator saw the conflicts with the direction and said go ahead"),
    as_json: bool = JsonOpt,
) -> None:
    """Request plates for shots that need them. Paid adapters refuse until the cost is confirmed."""

    def go(conn, r):
        p = projects.get(conn, project)
        r.project = p["id"]
        res = plates.request_plates(conn, p, adapter_name, _ords(shots), confirm_cost, ACTOR(), reference_strategy,
                                    accept_conflicts)
        r.data = res
        r.not_verified += [c["message"] + (" (kept by the creator)" if c["kept"] else " (accepted for this run)")
                           for c in res["conflicts"]]
        sent = sum(len(x.get("references", [])) for x in res["done"] + res["pending"])
        dropped = [(x["shot"], d) for x in res["done"] + res["pending"] for d in x.get("references_dropped", [])]
        if sent:
            r.verified.append(f"{sent} character reference images attached to the requests")
        r.not_verified += [f"shot {s}: {d['character']} {d['purpose']} reference not sent ({d['reason']})"
                           for s, d in dropped]
        r.not_verified += [f"shot {f['shot']}: {f['error']}; {f['hint']}" for f in res["failed"] if f.get("hint")]
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
        a = plates.fulfil(conn, p, request, file, ACTOR())
        r.data = {"plate": a["path"]}

    run("mb plate fulfil", as_json, go)


@plate_app.command("upload")
def plate_upload(project: str = ProjectOpt, shot: int = typer.Option(..., "--shot"),
                 file: Path = typer.Option(..., "--file"), as_json: bool = JsonOpt) -> None:
    """Use your own image as a shot's plate."""

    def go(conn, r):
        p = projects.get(conn, project)
        r.project = p["id"]
        a = plates.upload(conn, p, shot, file, ACTOR())
        r.data = {"plate": a["path"]}

    run("mb plate upload", as_json, go)


@app.command("use")
def use_version(project: str = ProjectOpt, asset: str = typer.Option(..., "--asset", help="Asset version id"),
                as_json: bool = JsonOpt) -> None:
    """Make an earlier plate or clip version (a take) the one the shot uses."""

    def go(conn, r):
        p = projects.get(conn, project)
        r.project = p["id"]
        row = conn.execute("SELECT a.id, a.kind, s.ord FROM asset_version a JOIN shot s ON s.id = a.shot_id "
                           "WHERE a.id = ? AND s.project_id = ?", (asset, p["id"])).fetchone()
        if not row:
            raise MbError("NOT_FOUND", f"no version '{asset}' in this project")
        a = assets.set_active(conn, asset, ACTOR())
        r.data = {"shot": row["ord"], "kind": row["kind"], "path": a["path"]}
        r.verified.append(f"shot {row['ord']} now uses this {row['kind']} version")

    run("mb use", as_json, go)


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
                    assets.review(conn, dict(s), kind, "approve", note, ACTOR())
                    done.append(s["ord"])
            r.data = {"approved": done}
            return
        s = board.shot_by_ord(conn, p["id"], shot)
        s = assets.review(conn, s, kind, decision, note, ACTOR())
        r.data = {"shot": shot, "state": s["state"]}

    run("mb review", as_json, go)


@app.command()
def clips(
    project: str = ProjectOpt,
    shots: str = typer.Option(None, "--shots"),
    redo: bool = typer.Option(False, "--redo", help="Render again even if a finished clip exists"),
    preset: str = typer.Option(None, "--preset", help="Guard preset to make active for this run"),
    seeds: str = typer.Option(None, "--seeds", help="One take per seed, e.g. 7,101,2024 (each a new version)"),
    backend: str = typer.Option(None, "--backend",
                                help="Video model for this run, e.g. ltx25 (default: the project's)"),
    sing_until: float = typer.Option(None, "--sing-until",
                                     help="Lip-sync shots of this run: seconds into the shot after which the singer "
                                          "hears silence (stops a backing echo being mouthed as a repeated word)"),
    as_json: bool = JsonOpt,
) -> None:
    """Queue clip renders for approved plates (fit check first). Start them with mb worker."""

    def go(conn, r):
        p = projects.get(conn, project)
        r.project = p["id"]
        board.require_gates(conn, p["id"], "storyboard", "plates")
        if preset:
            presets.set_active(conn, preset, ACTOR())
        profile = presets.active(conn)
        b = registry.get(backend or p["video_backend"])
        inst = b.check_installed()
        if not inst.installed:
            raise MbError("MISSING_MODEL", f"{b.name} is not ready: {'; '.join(inst.missing)}", hint="mb setup")
        w, h = b.sizes[p["aspect"]]
        now = monitor.sample()
        eff = replace(now, free_pct=max(now.free_pct, profile.start_free_pct))
        want = _ords(shots)
        rows = [x for x in conn.execute("SELECT frames, lip_sync, ord FROM shot WHERE project_id = ?",
                                        (p["id"],)).fetchall() if not want or x[2] in want]
        if not rows:
            raise MbError("INVALID_INPUT", "no such shots in this project")
        worst = max(rows, key=lambda x: x[0])  # the fit check sizes the longest shot of this run
        fit = fitcheck.fit(b, "a2v" if worst[1] else "i2v", w, h, b.frame_rule(worst[0]), profile, conn, eff)
        if not fit.fits:
            raise MbError("FIT_REFUSED", fit.summary(), hint="; ".join(fit.suggestions))
        seed_list = _ords(seeds) if seeds else None
        res = queue.enqueue_clips(conn, p, b, _ords(shots), redo, ACTOR(), seed_list, sing_until)
        r.data = {**res, "guard": profile.describe(), "backend": b.name, "fit_longest_shot": fit.summary(),
                  "est_minutes": round(sum((fit.est_seconds or 0) / max(1, worst[0]) * q["frames"]
                                           for q in res["queued"]) / 60, 1)}
        r.verified.append(f"fit check passed for the longest shot ({worst[0]} frames)")
        r.not_verified.append("render time is an estimate")
        # Motion prompts that contradict the direction are named again where they are about to be rendered.
        look = templates.get_look(p["visual_look"], conn) if p.get("visual_look") else None
        r.not_verified += board.grammar_warnings(conn, p, look)
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
        bad = [x for x in ok if x.get("problems")]
        if bad:
            r.not_verified.append("takes with problems: " + "; ".join(
                f"shot {x['shot']} {', '.join(x['problems'])}" for x in bad))
        r.not_verified.append("a clip can pass these checks and still be wrong (a changed face, lips that do not "
                              "move, the wrong action): watch every take before it is used")

    run("mb worker", as_json, go)


@queue_app.callback(invoke_without_command=True)
def queue_cmd(
    ctx: typer.Context,
    project: str = typer.Option(None, "--project", "-p"),
    pause: bool = typer.Option(False, "--pause", help="Pause after the current shot"),
    resume: bool = typer.Option(False, "--resume"),
    stop: bool = typer.Option(False, "--stop", help="Stop the running job now and clear the queue"),
    move: str = typer.Option(None, "--move", help="JOB:POSITION"),
    cancel: str = typer.Option(None, "--cancel", help="Shots to take out of the queue, e.g. 1,2,5 (needs --project)"),
    as_json: bool = JsonOpt,
) -> None:
    """Show the render queue, or pause, resume, stop, cancel, reorder."""

    def go(conn, r):
        pid = projects.get(conn, project)["id"] if project else None
        if pause:
            queue.pause(conn, ACTOR())
        if resume:
            queue.resume(conn, ACTOR())
        if stop:
            r.data["stopped"] = queue.stop(conn, pid, ACTOR())
        if cancel:
            if not pid:
                raise MbError("INVALID_INPUT", "--cancel needs --project")
            r.data["cancelled"] = queue.cancel(conn, pid, _ords(cancel), ACTOR())
            r.verified.append(f"cancelled queued shots {r.data['cancelled']}; shots with a clip keep it")
        if move:
            jid, pos = move.rsplit(":", 1)
            queue.move(conn, jid, int(pos), ACTOR())
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
                      "memory": last.get(j["id"]), "problems": j.get("stop_reason") or None} for j in js],
        })

    run("mb queue", as_json, go)
