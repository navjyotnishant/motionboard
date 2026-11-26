# Implementation Plan: Music Video Pipeline (Motionboard v1)

**Branch**: `001-music-video-pipeline` | **Date**: 2026-11-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-music-video-pipeline/spec.md`

## Summary

Build the Motionboard engine and the Claude plugin around it. The engine is a Python package with a `mb` command line that analyses the song, drafts and stores the storyboard, drives plate adapters, renders clips through a video backend (LTX-2.3 via `ltx-2-mlx`) under a memory guard, and finishes the video with ffmpeg plus a HyperFrames overlay. All state lives in one SQLite file shared with the Storyboard Studio (feature 002). The plugin exposes four commands (setup check, storyboard, plates and clips, finish and deliver) as skills that call `mb` and keep the review gates. The proven Almost Yours scripts (`run_batch.py`, `assemble.py`, overlay, matte, cover, guard scripts) are the starting point, refactored into modules.

## Technical Context

**Language/Version**: Python 3.12 (engine; matches the `ltx-2-mlx` MLX stack), Bash for thin wrappers, HTML/JS for the HyperFrames finishing template.

**Primary Dependencies**: librosa and soundfile (tempo, beats, loudness), mlx-whisper (lyric line alignment), demucs (vocal isolation for lip-sync shots), psutil (memory and swap readings), Pillow (contact sheets, cover), pydantic v2 (schemas), typer (CLI), PyYAML (templates, config), ffmpeg 7+ (system), HyperFrames 0.9.x via `npx` (overlay render), `ltx-2-mlx` in its own venv, called as a subprocess.

**Storage**: SQLite 3 single file, WAL mode, at `~/.motionboard/motionboard.db` (overridable). Media on disk under each project folder. JSON export and import for every project.

**Testing**: pytest (unit and integration), golden file tests for storyboard timing and ffmpeg command building, a short end to end smoke run with a stub video backend so CI needs no GPU.

**Target Platform**: macOS 14+ on Apple Silicon, 32 GB memory or more for default presets. Linux supported for everything except the MLX backend.

**Project Type**: Claude Code plugin (skills plus bundled scripts) wrapping a Python CLI engine; shares a database with a local Next.js app (feature 002).

**Performance Goals**: Storyboard draft for a 65 s song under 60 s of compute. Guard poll every 2 s with under 1 percent CPU. LTX-2.3 at 576x1024, about 3.6 s per frame on M3 Max (reference). Finish pass for 65 s under 10 min.

**Constraints**: Never exceed guard limits; never print or store secrets; no model weights in the repo; no network calls except model downloads the creator runs and plate adapters the creator configures; resumable at shot level.

**Scale/Scope**: One creator, projects up to 5 min and 120 shots, single render at a time.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How this plan complies | Status |
|---|---|---|
| I. Storyboard First | `mb clips` refuses to run unless the project's storyboard and plates gates are approved in the DB. | Pass |
| II. Local First, Free by Default | Default backend LTX-2.3 local; plate adapters include `manual` and `local`; paid adapters must declare a cost estimate and need `--confirm-cost` or a Studio click. | Pass |
| III. Never Crash the Machine | Every render and heavy step runs through `guard.run_guarded()`; `mb fit` dry run before each job; presets safe, balanced, max; limits stored in DB and printed at job start. | Pass |
| IV. No Bundled Weights | `mb setup` only reports and prints download steps and license links; `.gitignore` blocks weights; backend registry carries license text. | Pass |
| V. Review Gates | Gate table in DB (`stage_approval`); each skill ends with an artifact to review and stops. | Pass |
| VI. Honest Verification | Every command returns a JSON report with `verified` and `not_verified` lists; skills relay them. | Pass |
| VII. Simple and Portable | One DB file, media as files, `mb export` and `mb import` JSON; backends and plate sources behind small interfaces. | Pass |
| VIII. One Source of Truth | Engine owns migrations; Studio reads and writes the same DB; change events table for live updates. | Pass |

Post design re-check: Pass (no violations; see Complexity Tracking).

## Project Structure

### Documentation (this feature)

```text
specs/001-music-video-pipeline/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md
│   ├── storyboard.schema.json
│   ├── plate-adapter.md
│   ├── video-backend.md
│   └── guard.md
└── tasks.md
```

### Source Code (repository root)

```text
.claude-plugin/
└── plugin.json                  # plugin manifest
skills/
├── mb-setup/SKILL.md            # setup check
├── mb-storyboard/SKILL.md       # storyboard (brainstorm, template, draft, review)
├── mb-clips/SKILL.md            # plates and clips
├── mb-finish/SKILL.md           # finish and deliver
└── mb-studio/SKILL.md           # start/stop Studio (feature 002)
engine/
├── pyproject.toml
├── src/motionboard/
│   ├── cli.py                   # typer app, `mb`
│   ├── config.py                # paths, workspace settings
│   ├── report.py                # verified / not_verified report object
│   ├── db/
│   │   ├── connection.py        # WAL, busy timeout, migrations runner
│   │   ├── migrations/0001_init.sql
│   │   ├── repo.py              # typed queries
│   │   └── events.py            # change events
│   ├── audio/
│   │   ├── analyze.py           # tempo, beats, loudness, onsets
│   │   ├── segment.py           # pick and cut song segment
│   │   ├── align.py             # lyric line timing (mlx-whisper)
│   │   └── vocals.py            # demucs vocal stem per segment
│   ├── storyboard/
│   │   ├── timing.py            # line and beat grid, frame rule rounding
│   │   ├── draft.py             # build shots from concept or template
│   │   ├── templates.py         # load template YAML
│   │   ├── contact_sheet.py
│   │   └── io_json.py           # export / import
│   ├── plates/
│   │   ├── adapter.py           # PlateAdapter protocol, registry
│   │   ├── manual.py            # creator supplied files
│   │   ├── http_api.py          # generic HTTP adapter (key from file/env)
│   │   ├── command.py           # local command adapter (any local model)
│   │   └── handoff.py           # MCP handoff: Claude fulfils request rows
│   ├── backends/
│   │   ├── base.py              # VideoBackend protocol
│   │   ├── ltx23.py             # ltx-2-mlx generate / a2v
│   │   ├── stub.py              # test backend
│   │   ├── registry.py
│   │   └── profiles/ltx23.json  # measured memory and speed points
│   ├── guard/
│   │   ├── monitor.py           # psutil + memory_pressure + swap
│   │   ├── presets.py
│   │   ├── fitcheck.py
│   │   └── run.py               # run_guarded(subprocess)
│   ├── jobs/
│   │   ├── queue.py             # render_job table ops
│   │   └── worker.py            # `mb worker`, one job at a time
│   ├── finish/
│   │   ├── assemble.py          # trims, retime, upscale, grade, mux
│   │   ├── overlay.py           # writes overlay config, runs hyperframes
│   │   ├── cover.py
│   │   ├── metadata.py
│   │   └── deliver.py
│   └── setup/
│       ├── doctor.py            # machine, tools, weights report
│       └── models.py            # model catalog, license links, sizes
└── tests/
    ├── unit/
    ├── integration/
    └── fixtures/                # 10 s test song, lyrics, tiny plates
modes/                           # story modes; animation packs are Motionboard IP
├── LICENSE                      # PolyForm Noncommercial 1.0.0 (packs only)
├── studio-session/ (mode.yaml, animation/)
├── travel/ (mode.yaml, animation/)
├── two-lovers/ (mode.yaml, animation/)   # Almost Yours dust + ruby thread
├── lyric-story/ (mode.yaml, animation/)  # A Letter Never Sent kinetic type
└── mood-loop/ (mode.yaml, animation/)
looks/
└── *.yaml                       # origami, exotic, vintage-film, neon-night, cosmic (Apache-2.0)
studio/                          # feature 002
docs/
```

**Structure Decision**: Single repo that is itself the Claude plugin. Python engine under `engine/` is the only writer of schema migrations and the only process that runs heavy jobs. Skills stay thin and call `mb` with `--json`. The Studio (002) lives in `studio/` and talks to the same DB.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Two languages (Python engine, TypeScript Studio) | MLX, librosa, demucs are Python; Studio is a media web app in Next.js | One language would mean either a weak web UI or reimplementing audio and MLX tooling in Node |
| Job worker process | Renders take hours and must survive Studio and chat closing | Running renders inside the skill call blocks chat and dies with the session |
