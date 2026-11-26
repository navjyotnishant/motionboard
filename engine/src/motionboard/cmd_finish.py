"""Finish and deliver commands: theme, finish, deliver."""

import json
import subprocess
from pathlib import Path

import typer

from motionboard import assets, projects
from motionboard.cli import JsonOpt, app, run
from motionboard.config import ACTOR
from motionboard.db import repo
from motionboard.finish import assemble, metadata
from motionboard.finish import deliver as deliver_mod
from motionboard.finish import overlay as packs
from motionboard.guard import presets
from motionboard.report import MbError
from motionboard.storyboard import board, templates

ProjectOpt = typer.Option(..., "--project", "-p", help="Project id (or its last characters)")
LIST_KEYS = {"highlight_words", "tags", "hashtags", "platforms", "chorus"}
NUM_KEYS = {"snap_at", "end_hold", "lyrics_y"}



def _tail_audio(p: dict, workdir: Path, tail: float) -> Path:
    """For a long end hold the song plays on under the end card and fades out, instead of cutting to silence."""
    seg = projects.segment_audio(p)
    song, start, end = p.get("song_path"), p.get("segment_start"), p.get("segment_end")
    if not song or start is None or end is None or not Path(song).exists():
        return seg
    workdir.mkdir(parents=True, exist_ok=True)
    out = workdir / "audio_tail.wav"
    music = float(end) - float(start)
    res = subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{float(start):.3f}", "-t", f"{music + tail:.3f}",
                          "-i", str(song), "-af", f"afade=t=out:st={music:.3f}:d={tail:.3f}", str(out)],
                         capture_output=True, text=True)
    return out if res.returncode == 0 and out.exists() else seg

@app.command()
def theme(
    project: str = ProjectOpt,
    set_: list[str] = typer.Option(None, "--set", help="key=value; lists as comma separated, e.g. "
                                   "highlight_words=almost,love"),
    unset: list[str] = typer.Option(None, "--unset"),
    as_json: bool = JsonOpt,
) -> None:
    """Show or edit the finishing theme: artist, song, album_line, release_note, highlight_words, snap_at, ..."""

    def go(conn, r):
        p = projects.get(conn, project)
        r.project = p["id"]
        th = json.loads(p.get("theme") or "{}")
        for item in set_ or []:
            if "=" not in item:
                raise MbError("INVALID_INPUT", f"--set needs key=value, got '{item}'")
            k, v = item.split("=", 1)
            k = k.strip()
            if k in LIST_KEYS:
                val = [x.strip() for x in v.split(",") if x.strip()]
                th[k] = [float(x) for x in val] if k == "chorus" else val
            elif k in NUM_KEYS:
                th[k] = float(v)
            else:
                th[k] = v
        for k in unset or []:
            th.pop(k, None)
        if set_ or unset:
            projects.touch(conn, p["id"], ACTOR(), theme=th)
        mode = templates.get_mode(p["mode"], conn) if p.get("mode") else None
        keys = packs.load_pack(mode.animation)["theme_keys"] if mode else {}
        r.data = {"theme": th, "pack": mode.animation if mode else None, "pack_keys": keys}

    run("mb theme", as_json, go)


def _active_clips(conn, shots: list[dict]) -> list[Path]:
    out = []
    for s in shots:
        a = assets.active(conn, s["id"], "clip")
        if not a or not a["path"] or not Path(a["path"]).exists():
            raise MbError("INVALID_INPUT", f"shot {s['ord']} has no clip file", hint="mb clips, then mb worker")
        out.append(Path(a["path"]))
    return out


def _frame(video: Path, at: float, out: Path) -> Path:
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{at:.2f}", "-i", str(video), "-frames:v", "1",
                        "-q:v", "2", str(out)], capture_output=True, text=True)
    if r.returncode != 0:
        raise MbError("INTERNAL", f"frame grab failed: {r.stderr.strip()}")
    return out


@app.command()
def finish(
    project: str = ProjectOpt,
    no_animation: bool = typer.Option(False, "--no-animation", help="Skip the mode's animation pack"),
    cover_at: float = typer.Option(None, "--cover-at", help="Second of the cut to use for the cover"),
    as_json: bool = JsonOpt,
) -> None:
    """Assemble the final video: cuts on shot times, grade, the mode's animation pack, end card, cover, metadata."""

    def go(conn, r):
        p = projects.get(conn, project)
        r.project = p["id"]
        board.require_gates(conn, p["id"], "storyboard", "plates", "clips")
        shots = [dict(x) for x in conn.execute("SELECT * FROM shot WHERE project_id = ? ORDER BY ord", (p["id"],))]
        clips = _active_clips(conn, shots)
        a = repo.get(conn, "song_analysis", p["id"], key="project_id")
        analysis = {"beats": json.loads(a["beats"]), "lines": json.loads(a["lines"])}
        folder = Path(p["folder"])
        outdir = folder / "out"
        profile = presets.active(conn)
        slug = projects.slugify(p["title"])
        w, h = assemble.DELIVERY[p["aspect"]]
        final = outdir / f"{slug}_{w}x{h}.mp4"
        overlay_mp4 = matte_mp4 = None
        pack_name, tail = None, 1.5
        mode = templates.get_mode(p["mode"], conn) if p.get("mode") else None
        if mode and not no_animation:
            pack = packs.load_pack(mode.animation)
            pack_name, tail = pack["name"], float(pack.get("tail_seconds", 1.5))
            theme_now = json.loads(p.get("theme") or "{}")
            if theme_now.get("end_hold") is not None:  # creator asked the end card to stay longer (or shorter)
                tail = min(12.0, max(1.5, float(theme_now["end_hold"])))
            if p["aspect"] not in pack["aspects"]:
                raise MbError("INVALID_INPUT", f"pack '{pack_name}' does not support {p['aspect']}")
            cfg = packs.make_config(p, analysis, shots, tail)
            work = packs.prepare(pack_name, cfg, outdir / "finish" / pack_name)
            layers = pack["layers"]
            if "matte" in layers:
                matte_mp4 = packs.render_layer(work, layers["matte"]["file"], outdir / "finish" / "matte.mp4", 24,
                                               profile)
            if "overlay" in layers:
                overlay_mp4 = packs.render_layer(work, layers["overlay"]["file"], outdir / "finish" / "overlay.mp4",
                                                 24, profile)
            r.verified.append(f"animation pack '{pack_name}' rendered ({cfg['duration']} s)")
        else:
            r.not_verified.append("no animation pack used")
        audio = _tail_audio(p, outdir / "finish", tail) if tail > 1.5 else projects.segment_audio(p)
        plan = assemble.build(shots, clips, audio, final, p["aspect"], 24, overlay_mp4, matte_mp4,
                              tail)
        res = subprocess.run(plan.cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise MbError("INTERNAL", f"ffmpeg assemble failed: {res.stderr.strip()[-800:]}")
        info = assets.probe(final)
        checks = []
        if abs(info["frames"] - plan.total_frames) > 1:
            checks.append(f"expected {plan.total_frames} frames, got {info['frames']}")
        if (info["width"], info["height"]) != (w, h):
            checks.append(f"expected {w}x{h}, got {info['width']}x{info['height']}")
        if abs(info["duration"] - plan.duration) > 0.1:
            checks.append(f"expected {plan.duration} s, got {info['duration']:.2f} s")
        if checks:
            r.not_verified += checks
        else:
            r.verified.append(f"final is {w}x{h}, {info['frames']} frames, {info['duration']:.2f} s "
                              "(segment plus tail)")
        r.verified.append("cuts placed on shot frames by construction (each shot trimmed to its exact frames)")
        r.not_verified.append("lyric timing on screen matches the line timing in the analysis, not checked by ear")
        cover = outdir / f"{slug}_cover_{w}x{h}.jpg"
        at = cover_at if cover_at is not None else (shots[-1]["end"]) * 0.4
        shot_at = next((s for s, c in zip(shots, clips, strict=True) if s["start"] <= at < s["end"]), shots[0])
        clip_at = clips[shots.index(shot_at)]
        bg = _frame(clip_at, max(0.0, at - shot_at["start"]), outdir / "cover-bg.jpg")  # clean picture, no lyrics
        try:
            if pack_name:
                packs.render_cover(outdir / "finish" / pack_name, bg, cover, profile)
                r.verified.append("cover rendered with the pack's title block")
            else:
                cover.write_bytes(bg.read_bytes())
        except MbError as e:
            cover.write_bytes(bg.read_bytes())
            r.not_verified.append(f"cover title block failed ({e.message}); plain frame used")
        meta = metadata.write(p, outdir / f"{slug}_metadata.md", final, cover)
        conn.execute(
            "INSERT INTO delivery(project_id, video_path, cover_path, metadata_path, verified) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(project_id) DO UPDATE SET video_path = excluded.video_path, cover_path = excluded.cover_path,"
            " metadata_path = excluded.metadata_path, verified = excluded.verified",
            (p["id"], str(final), str(cover), str(meta), json.dumps({"verified": r.verified, "probe": info})))
        r.data = {"video": str(final), "cover": str(cover), "metadata": str(meta), "probe": info,
                  "pack": pack_name, "synthetic_people": bool(p.get("synthetic_people"))}
        r.next = f"review the video, then mb approve --project {p['id']} --stage final and mb deliver"

    run("mb finish", as_json, go)


@app.command()
def deliver(
    project: str = ProjectOpt,
    to: Path = typer.Option(..., "--to", help="Folder to copy the video, cover and metadata into"),
    post_time: str = typer.Option(None, "--post-time", help="When it should go out, written into the metadata"),
    platforms: str = typer.Option(None, "--platforms", help="Comma separated, e.g. YouTube Shorts,Instagram Reels"),
    as_json: bool = JsonOpt,
) -> None:
    """Copy the approved final video, cover and metadata to a folder (Dropbox, a drive, anywhere)."""

    def go(conn, r):
        p = projects.get(conn, project)
        r.project = p["id"]
        board.require_gates(conn, p["id"], "final")
        d = repo.get(conn, "delivery", p["id"], key="project_id")
        meta = Path(d["metadata_path"])
        plats = [x.strip() for x in platforms.split(",")] if platforms else None
        metadata.write(p, meta, Path(d["video_path"]), Path(d["cover_path"]), post_time, plats)
        res = deliver_mod.deliver(Path(d["video_path"]), Path(d["cover_path"]), meta, to)
        conn.execute("UPDATE delivery SET target_folder = ?, post_time = ? WHERE project_id = ?",
                     (str(to), post_time, p["id"]))
        r.data = res
        r.verified.append("files copied and sizes match; video re-probed at the destination")
        r.not_verified.append("posting is not done by Motionboard")

    run("mb deliver", as_json, go)
