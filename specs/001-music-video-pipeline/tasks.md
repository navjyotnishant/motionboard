---
description: "Task list for Music Video Pipeline (Motionboard v1)"
---

# Tasks: Music Video Pipeline (Motionboard v1)

**Input**: Design documents from `/specs/001-music-video-pipeline/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included for the rules the constitution depends on (timing, gates, cost, guard, secrets) and one end to end smoke run with the stub backend.

**Reuse**: Port logic from the Almost Yours project at `~/Movies/NAVAAN-reels/almost-yours/museum/` (`ltx/run_batch.py`, `ltx/assemble.py`, `overlay/`, `matte/`, `cover/`, `compare/run_*.sh` guard loops).

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup

- [x] T001 [MOT-17] Initialise git repo, `.gitignore` (weights, `*.safetensors`, `.venv`, `node_modules`, `*.db`, project media), MIT `LICENSE`, `README.md` in repo root
- [x] T002 [MOT-18] Create plugin manifest `.claude-plugin/plugin.json` (name `motionboard`, version 0.1.0, repo navjyotnishant/motionboard)
- [x] T003 [MOT-19] Create Python package with uv: `engine/pyproject.toml` (Python 3.12, typer, pydantic, PyYAML, librosa, soundfile, psutil, Pillow, mlx-whisper, demucs as optional extra, pytest, ruff), entry point `mb = motionboard.cli:app`
- [x] T004 [MOT-20] [P] Configure ruff and pytest in `engine/pyproject.toml`; add `engine/tests/conftest.py` with temp DB and temp project folder fixtures
- [x] T005 [MOT-21] [P] Add test fixtures: 10 s song `engine/tests/fixtures/song10s.wav`, `lyrics.txt`, 4 plates `plates/shot-01..04.png`, 80 shot export `export80.json`

## Phase 2: Foundational (blocks all stories)

- [x] T006 [MOT-22] Implement config and paths (`~/.motionboard/`, projects root, `MB_DB` override) in `engine/src/motionboard/config.py`
- [x] T007 [MOT-23] Write initial schema with every table in data-model.md, indexes, `schema_version` in `engine/src/motionboard/db/migrations/0001_init.sql`
- [x] T008 [MOT-24] Implement connection (WAL, foreign keys, busy_timeout 5000) and migration runner in `engine/src/motionboard/db/connection.py`
- [x] T009 [MOT-25] Implement change events writer used by every write in `engine/src/motionboard/db/events.py`
- [x] T010 [MOT-26] Implement typed repository (projects, shots, assets, jobs, approvals, adapters, guard profiles) with secret pattern rejection in `engine/src/motionboard/db/repo.py`
- [x] T011 [MOT-27] Implement report object (`ok`, `data`, `verified`, `not_verified`, `next`, error codes) and redactor in `engine/src/motionboard/report.py`
- [x] T012 [MOT-28] Create typer app with `--json` handling and `mb db migrate` in `engine/src/motionboard/cli.py`
- [x] T013 [MOT-29] [P] Implement memory monitor (memory_pressure free percent, `sysctl vm.swapusage`, psutil fallback, process group RSS) in `engine/src/motionboard/guard/monitor.py`
- [x] T014 [MOT-30] [P] Seed builtin guard presets safe, balanced, max in `engine/src/motionboard/guard/presets.py`
- [x] T015 [MOT-31] Implement `run_guarded` (wait for start floor, process group, 2 s samples to `memory_sample`, SIGTERM then SIGKILL, stop reason and suggestion, `fit_sample` on success) in `engine/src/motionboard/guard/run.py`
- [x] T016 [MOT-32] Implement fit check from backend profile plus local `fit_sample` rows in `engine/src/motionboard/guard/fitcheck.py`
- [x] T017 [MOT-33] [P] Define `VideoBackend` protocol and registry in `engine/src/motionboard/backends/base.py` and `registry.py`
- [x] T018 [MOT-34] [P] Implement stub backend (ffmpeg colour clip of exact frames) in `engine/src/motionboard/backends/stub.py`
- [x] T019 [MOT-35] Add `mb guard` and `mb fit` commands in `engine/src/motionboard/cli.py`
- [x] T020 [MOT-36] [P] Tests: guard stops a memory hog subprocess under a tight preset and records reason in `engine/tests/integration/test_guard.py`
- [x] T021 [MOT-37] [P] Tests: repo rejects key like strings and reports redact secrets in `engine/tests/unit/test_secrets.py`

**Checkpoint**: DB, reports, guard and fit check work; stories can start.

## Phase 3: User Story 1 - Storyboard from a song (P1) 🎯 MVP

**Goal**: Song, lyrics and idea become a timed, editable storyboard with a contact sheet.

**Independent Test**: 60 s song gives a storyboard whose shot boundaries are within 0.1 s of measured beats or line starts.

- [x] T022 [MOT-38] [P] [US1] Implement `mb project new` (folder layout `audio/ plates/ clips/ out/ logs/`) in `engine/src/motionboard/cli.py` and `engine/src/motionboard/db/repo.py`
- [x] T023 [MOT-39] [P] [US1] Implement tempo, beats, RMS, onsets, waveform peaks in `engine/src/motionboard/audio/analyze.py`
- [x] T024 [MOT-40] [P] [US1] Implement segment picker (first chorus heuristic, manual override) and cut with atrim and short fades in `engine/src/motionboard/audio/segment.py`
- [x] T025 [MOT-41] [US1] Implement lyric line alignment with mlx-whisper word timestamps, beat grid fallback and `verified_vocal_alignment` flag in `engine/src/motionboard/audio/align.py`
- [x] T026 [MOT-42] [US1] Add `mb analyze` writing `song_analysis` in `engine/src/motionboard/cli.py`
- [x] T027 [MOT-43] [US1] Implement timing grid (one shot per line or beat group, min frames merge, frame rule rounding, tiling validation) in `engine/src/motionboard/storyboard/timing.py`
- [x] T028 [MOT-44] [P] [US1] Write five modes (Studio Session, Travel, Two Lovers, Lyric Story, Mood Loop) as `modes/<mode>/mode.yaml` (rhythm rules, camera language, figure rules, animation pack name) and five looks (Origami, Exotic, Vintage Film, Neon Night, Cosmic) as `looks/*.yaml` (style lines, no figure lines, plate prompt language)
- [x] T029 [MOT-45] [US1] Implement mode and look loader, validation and combination in `engine/src/motionboard/storyboard/templates.py`
- [x] T030 [MOT-46] [US1] Implement draft from chosen concept or mode plus look (fills visual, action, camera, has_figure, plate and motion prompts; one clear action per shot) in `engine/src/motionboard/storyboard/draft.py`
- [x] T031 [MOT-47] [US1] Add `mb concepts add`, `mb draft`, `mb shot set` (dirty and state rules) in `engine/src/motionboard/cli.py`
- [x] T032 [MOT-48] [P] [US1] Implement contact sheet (aspect aware tiles, shot number, timecode, lyric) in `engine/src/motionboard/storyboard/contact_sheet.py` and `mb sheet`
- [x] T033 [MOT-49] [P] [US1] Implement JSON export and import per `contracts/storyboard.schema.json` in `engine/src/motionboard/storyboard/io_json.py` and `mb export` / `mb import`
- [x] T034 [MOT-50] [US1] Implement gates (`mb approve`, revoke, rule that every shot is in the matching state) in `engine/src/motionboard/cli.py`
- [x] T035 [MOT-51] [US1] Write skill `skills/mb-storyboard/SKILL.md`: gather song, lyrics, idea, aspect, look; offer Brainstorm (Claude writes three concepts as JSON, `mb concepts add`) or template; run analyze and draft; show contact sheet; stop for approval
- [x] T036 [MOT-52] [P] [US1] Tests: golden timing for fixture song, tiling and frame rule in `engine/tests/unit/test_timing.py`
- [x] T037 [MOT-53] [P] [US1] Tests: export then import round trip identical in `engine/tests/unit/test_io_json.py`

**Checkpoint**: Storyboard stage usable on its own.

## Phase 4: User Story 2 - Plates and clips on the local machine (P1)

**Goal**: Approved storyboard becomes plates (any source) and clips rendered locally under the guard, resumable.

**Independent Test**: Approved 5 shot storyboard renders 5 clips of exact length and size with no out of memory; rerun does no work.

- [x] T038 [MOT-54] [P] [US2] Define `PlateAdapter` protocol and registry in `engine/src/motionboard/plates/adapter.py`
- [x] T039 [MOT-55] [P] [US2] Implement manual adapter (watch folder naming `shot-NN.png`, upload) in `engine/src/motionboard/plates/manual.py`
- [x] T040 [MOT-56] [P] [US2] Implement command adapter with placeholders run under the guard in `engine/src/motionboard/plates/command.py`
- [x] T041 [MOT-57] [P] [US2] Implement http adapter (templated body, key from file or env at call time, image extraction, declared cost) in `engine/src/motionboard/plates/http_api.py`
- [x] T042 [MOT-58] [P] [US2] Implement handoff adapter (pending `plate_request` rows, `mb plate fulfil`) in `engine/src/motionboard/plates/handoff.py`
- [x] T043 [MOT-59] [US2] Add `mb adapter` and `mb plates` with cost estimate and `COST_NOT_CONFIRMED` in `engine/src/motionboard/cli.py`
- [x] T044 [MOT-60] [US2] Implement LTX-2.3 backend (i2v and a2v command build, snapshot path, style or no figure line, progress parse) in `engine/src/motionboard/backends/ltx23.py`
- [x] T045 [MOT-61] [P] [US2] Add measured profile points from the Almost Yours runs in `engine/src/motionboard/backends/profiles/ltx23.json`
- [x] T046 [MOT-62] [US2] Implement job queue ops (enqueue, priority, pause, resume, stop, move) in `engine/src/motionboard/jobs/queue.py`
- [x] T047 [MOT-63] [US2] Implement worker (one job at a time, fit check, `run_guarded`, progress and sec per frame, skip shots with valid active clip unless redo, detach mode, logs) in `engine/src/motionboard/jobs/worker.py`
- [x] T048 [MOT-64] [US2] Add `mb clips` (gate check, fit per setting, enqueue), `mb worker`, `mb queue` in `engine/src/motionboard/cli.py`
- [x] T049 [MOT-65] [P] [US2] Implement vocal stem per lip-sync shot with demucs under the guard in `engine/src/motionboard/audio/vocals.py`
- [x] T050 [MOT-66] [US2] Write skill `skills/mb-clips/SKILL.md`: pick adapter, confirm cost, fulfil handoff requests with the creator's MCP image tool, show plate sheet, stop for approval, queue clips, start worker, report progress and guard stops
- [x] T051 [MOT-67] [P] [US2] Tests: clips refused before gates; paid adapter refused without confirm in `engine/tests/unit/test_gates_cost.py`
- [x] T052 [MOT-68] [P] [US2] Tests: stub backend run, stop mid queue, resume renders no finished shot in `engine/tests/integration/test_resume.py`

**Checkpoint**: P1 complete: song to approved clips.

## Phase 5: User Story 3 - Finish and deliver (P2)

**Goal**: Clips become a postable video with lyrics, grade, end card, cover and metadata.

**Independent Test**: One MP4 matching segment duration, frame count, size and audio, plus cover and metadata.

- [ ] T053 [MOT-69] [US3] Port assemble (trim to cut points, optional piecewise retime, lanczos upscale to 1080x1920 or 1920x1080, mux original audio, tail) in `engine/src/motionboard/finish/assemble.py`
- [ ] T054 [MOT-70] [P] [US3] Port the Almost Yours dust overlay and matte as the Two Lovers animation pack (lyric rows from `song_analysis.lines`, ruby thread, motes, dusting end card from theme, no follow ask by default) in `modes/two-lovers/animation/`
- [ ] T055 [MOT-71] [US3] Implement animation pack contract (pack.json: inputs, theme keys, fonts, duration rules), overlay config writer and foreground HyperFrames render in `engine/src/motionboard/finish/overlay.py`
- [ ] T056 [MOT-72] [US3] Add grade, multiply matte, screen overlay, noise alls=3, CRF 19, faststart to assemble in `engine/src/motionboard/finish/assemble.py`
- [ ] T057 [MOT-73] [P] [US3] Implement cover from a chosen frame with title block in `engine/src/motionboard/finish/cover.py`
- [ ] T058 [MOT-74] [P] [US3] Implement metadata file (title, description, tags, hashtags, post time, platforms, synthetic content flag) in `engine/src/motionboard/finish/metadata.py`
- [ ] T059 [MOT-75] [US3] Implement deliver (copy to folder, verify sizes and durations with ffprobe) in `engine/src/motionboard/finish/deliver.py`
- [ ] T060 [MOT-76] [US3] Add `mb finish` and `mb deliver` with verification report (duration, frame count, cut points within one frame) in `engine/src/motionboard/cli.py`
- [ ] T061 [MOT-77] [US3] Write skill `skills/mb-finish/SKILL.md`: theme check, finish, contact sheet of final, stop for approval, deliver
- [ ] T062 [MOT-78] [P] [US3] Tests: ffmpeg command builder golden output in `engine/tests/unit/test_assemble.py`

## Phase 6: User Story 4 - Setup check and fit check (P2)

**Goal**: New creator sees what is missing and how to fix it; renders never start if they will not fit.

**Independent Test**: Without weights, `mb setup` lists the model with license link and size and downloads nothing.

- [x] T063 [MOT-79] [P] [US4] Write model catalog (LTX-2.3 q8, Gemma 3 12B 4bit, demucs, whisper; license URLs, sizes, `hf download` with include and exclude and `HF_HUB_DISABLE_XET=1`) in `engine/src/motionboard/setup/models.py`
- [x] T064 [MOT-80] [US4] Implement doctor (chip, memory, free disk, uv, ffmpeg, node, npx hyperframes, ltx bin, partial downloads) in `engine/src/motionboard/setup/doctor.py`
- [x] T065 [MOT-81] [US4] Add `mb setup` and `--fix-plan` in `engine/src/motionboard/cli.py`
- [x] T066 [MOT-82] [US4] Write skill `skills/mb-setup/SKILL.md`: run setup, explain gaps, never download without the creator, show guard presets and let the creator pick
- [x] T067 [MOT-83] [P] [US4] Tests: fit refuses oversize request with suggestions in `engine/tests/unit/test_fitcheck.py`

## Phase 7: User Story 5 - Realistic characters and lip-sync performance (P3)

**Goal**: Consistent realistic characters and singing shots, flagged as synthetic.

**Independent Test**: 3 shot board with one sung line gives a lip-synced clip and metadata with synthetic content Yes.

- [ ] T068 [MOT-84] [US5] Add character commands (`mb character add|set`, reference image, style line, link to shots) in `engine/src/motionboard/cli.py`
- [ ] T069 [MOT-85] [US5] Pass character reference images to adapters that support them and append style lines in `engine/src/motionboard/plates/adapter.py`
- [ ] T070 [MOT-86] [US5] Route `lip_sync` shots to a2v with the vocal stem in `engine/src/motionboard/jobs/worker.py`
- [ ] T071 [MOT-87] [US5] Set `synthetic_people` for realistic look with figures and write it to metadata in `engine/src/motionboard/finish/metadata.py`
- [ ] T072 [MOT-88] [P] [US5] Add Studio Session lip-sync defaults in `modes/studio-session/mode.yaml`

## Phase 8: Polish

- [ ] T073 [MOT-89] [P] Write docs: install, first video, adapters, guard presets, licenses in `docs/`
- [ ] T074 [MOT-90] [P] Add GitHub Actions CI (ruff, pytest with stub backend, no GPU) in `.github/workflows/ci.yml`
- [ ] T075 [MOT-91] Run quickstart.md steps 1 to 6 on the reference Mac and record results in `specs/001-music-video-pipeline/checklists/quickstart-run.md`

## Phase 9: Mode animation packs (Motionboard IP)

**Goal**: every v1 mode has its own signature animation, licensed PolyForm Noncommercial 1.0.0.

**Independent Test**: each pack renders over the fixture song with stub clips; lyrics follow `song_analysis.lines`; end card shows theme texts; no follow or subscribe ask.

- [ ] T076 [MOT-143] Add `modes/LICENSE` (full PolyForm Noncommercial 1.0.0 text, required notice), dual licence section in `README.md`, and a licence check in `engine/tests/unit/test_licences.py` that every `modes/*/animation/` folder carries the notice
- [ ] T077 [MOT-144] [P] Build the Studio Session pack (VU meter and waveform pulses on beats, lyrics on a lyric sheet, REC light, tape counter, cassette label end card) in `modes/studio-session/animation/`
- [ ] T078 [MOT-145] [P] Build the Travel pack (route line drawn between cuts, lyric words as ink stamps without place names, boarding pass end card) in `modes/travel/animation/`
- [ ] T079 [MOT-146] [P] Port the A Letter Never Sent kinetic typography as the Lyric Story pack (one big word per beat, hard cuts, handwriting contrast) in `modes/lyric-story/animation/`
- [ ] T080 [MOT-147] [P] Build the Mood Loop pack (light leaks, drifting particles, breathing lyric fades) in `modes/mood-loop/animation/`
- [ ] T081 [MOT-148] Render a contact sheet and 10 s preview per pack with the fixture song and record results in `specs/001-music-video-pipeline/checklists/packs-run.md`

## Dependencies

- Setup, then Foundational, then stories. Phase 9 packs need T055 (pack contract); T079 reuses the promo film project at `~/Movies/NAVAAN-reels/letter-never-sent/film`.
- US1 before US2 (clips need approved storyboard). US3 needs US2 output. US4 can run in parallel with US1. US5 after US2.
- Within stories: protocols and models before services, services before CLI, CLI before skills.

## Parallel examples

- Foundational: T013, T014, T017, T018 together; T020, T021 together.
- US1: T022, T023, T024, T028 together; then T032, T033, T036, T037.
- US2: T038 to T042 together; T045, T049 alongside T044.

## Implementation strategy

MVP is US1 (storyboard) then US2 (clips): the full local path from song to approved clips. Then US4 (setup) and US3 (finish). US5 last. Feature 002 Studio starts after the Foundational phase here, since it needs the DB schema and `mb`.
