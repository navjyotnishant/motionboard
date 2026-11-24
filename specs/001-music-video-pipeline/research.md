# Research: Music Video Pipeline

All Technical Context unknowns resolved. Sources: the Almost Yours build (Nov 2026) on an M3 Max 36 GB, and package registries checked 2026-11-24.

## R1. Engine language and packaging
- **Decision**: Python 3.12 package `motionboard` managed with uv, entry point `mb`.
- **Rationale**: MLX, librosa, demucs and mlx-whisper are Python. 3.12 matches the working `ltx-2-mlx` venv; 3.14 on the Mac is too new for some wheels.
- **Alternatives**: Node engine (no MLX or audio stack); Go (same gap).

## R2. Calling LTX-2.3
- **Decision**: Run `ltx-2-mlx` as a subprocess from its own venv; path set in workspace settings. Proven flags: `generate --distilled --low-ram --no-audio -W 576 -H 1024 -f <8k+1> --frame-rate 24 --seed 42 --image <plate>`; lip-sync via `a2v --audio <wav>`.
- **Rationale**: Isolates heavy deps, lets the guard kill the whole process group, and matches what already works (about 3.6 s per frame, 97 frames in about 6 min, a2v 81 frames in about 228 s).
- **Alternatives**: Import as a library (guard cannot reclaim memory reliably); ComfyUI (extra server, heavier).

## R3. Memory guard
- **Decision**: Poll every 2 s: `memory_pressure` free percent (macOS), `sysctl vm.swapusage`, psutil fallback on Linux. Start only when free is at or above the preset start floor; stop the process group (SIGTERM, then SIGKILL after 5 s) when free drops below the kill floor or swap exceeds the ceiling. Presets: safe (start 45%, kill 12%, swap 2 GB), balanced (start 35%, kill 8%, swap 4 GB), max (start 25%, kill 6%, swap 8 GB). Custom allowed.
- **Rationale**: The Wan test caused a kernel watchdog restart; the 2 s guard with free percent thresholds stopped later runs cleanly. Values come from those runs.
- **Alternatives**: cgroups (not on macOS); RSS only (misses compressed memory and swap).

## R4. Fit check
- **Decision**: Each backend ships a profile of measured points (model, width, height, frames, mode, peak GB, seconds per frame). `mb fit` interpolates on pixel x frames, adds a 15 percent margin, compares with total memory times (1 minus kill floor). Every real run appends its measured peak to the `fit_sample` table so estimates improve locally.
- **Rationale**: Cheap, explainable, gets better with use.
- **Alternatives**: Trial run of one frame (slow, still risky).

## R5. Song analysis and timing
- **Decision**: librosa for tempo, beat times, RMS loudness, onset strength; mlx-whisper word timestamps to place sung lines; when lyrics are given, align given lines to transcribed words. Segment picker prefers first chorus (highest sustained loudness plus repeated lyric lines). Shot frames rounded to the backend frame rule (LTX: 8k+1).
- **Rationale**: Same approach as the promo films; site timestamps led the voice by up to 1 s, so alignment must come from audio.
- **Alternatives**: Beat grid only (fallback when no vocals).

## R6. Vocal isolation for lip-sync
- **Decision**: demucs htdemucs two stem (vocals, no vocals) on the shot's segment only, under the guard.
- **Rationale**: a2v follows the cleanest vocal; full mix made mouth motion mushy.
- **Alternatives**: None needed v1.

## R7. Plate adapters
- **Decision**: One protocol, four kinds: `manual` (files), `command` (any local CLI that takes prompt and outputs an image), `http` (generic JSON API, key read from file or env, cost per image declared), `handoff` (writes a plate request row; the Claude skill fulfils it with whatever MCP tool the creator has, for example Muse, then marks it done).
- **Rationale**: Creator asked for loose coupling: local, MCP or API. MCP tools exist only inside Claude, so a handoff row keeps the engine free of MCP while still supporting it.
- **Alternatives**: Hard code providers (rejected by creator).

## R8. Finishing
- **Decision**: ffmpeg assemble (trim to cut points, optional piecewise retime, lanczos upscale, gbrp blend, grade eq and curves, unsharp, noise alls=3, CRF 19, faststart). HyperFrames 0.9.x renders the overlay and matte from the `themes/dust` template, run in the foreground. Theme values (fonts, colors, texts, end card) come from the project.
- **Rationale**: Exactly the approved Almost Yours look; one style for v1.
- **Alternatives**: Remotion (heavier setup), pure ffmpeg drawtext (cannot do dust and thread).

## R9. Database
- **Decision**: SQLite, WAL, `busy_timeout=5000`, foreign keys on. Schema owned by the engine (`db/migrations/*.sql`, `schema_version` table). Every write also inserts into `change_event` (table, row id, kind, at) so the Studio can stream changes.
- **Rationale**: Single file, no server, safe concurrent readers, Studio and engine both have mature drivers.
- **Alternatives**: DuckDB (analytics, weaker concurrent writes); JSON files only (no reliable concurrent edits).

## R10. Jobs
- **Decision**: `render_job` table as the queue; `mb worker` runs one job at a time, writes progress and memory samples every 2 s, honours pause and stop flags, survives chat and Studio closing (launched with `nohup` style detach, logs to project folder). HyperFrames step runs in the foreground of the worker (nohup cancelled it before).
- **Alternatives**: Celery or Redis (servers, overkill).

## R11. Secrets
- **Decision**: Adapter config stores only a reference (`key_file: ~/.navaan-assets/meta_api_key` or `key_env: NAME`). Reports and logs pass through a redactor.

## R12. Model catalog
- **Decision**: `setup/models.py` lists LTX-2.3 q8 MLX (`dgrauet/ltx-2.3-mlx-q8`, about 87.5 GB full repo, use include and exclude rules), Gemma 3 12B 4bit text encoder, demucs htdemucs, mlx-whisper model; each with license URL, size, and the exact `hf download` command with `HF_HUB_DISABLE_XET=1` for resume. Wan 2.2 and LTX-2.5 listed as backlog, not installable in v1.
