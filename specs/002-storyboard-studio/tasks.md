---
description: "Task list for Storyboard Studio"
---

# Tasks: Storyboard Studio (local web app)

**Input**: Design documents from `/specs/002-storyboard-studio/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md; feature 001 Phase 2 complete (schema, `mb`).

**Tests**: Vitest for lib and routes; Playwright for the main flows with the stub backend.

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup

- [ ] T001 [MOT-92] Scaffold Next.js 16 app with TypeScript, App Router, Tailwind 4 in `studio/` (`package.json`, `next.config.ts`, `tsconfig.json`)
- [ ] T002 [MOT-93] [P] Add dependencies better-sqlite3, drizzle-orm, wavesurfer.js, zod, Radix primitives, lucide-react; dev: vitest, playwright in `studio/package.json`
- [ ] T003 [MOT-94] [P] Define design tokens (dark surfaces, text, one accent, status colours, spacing, type scale, tabular numbers) in `studio/src/styles/tokens.css` and `studio/tailwind.css`
- [ ] T004 [MOT-95] [P] Add `mb studio start|stop|status` (one time `npm ci` and `next build`, start on 127.0.0.1:4317, print URL with token, pid file) in `engine/src/motionboard/studio_cmd.py`

## Phase 2: Foundational

- [ ] T005 [MOT-96] Implement DB access (WAL, busy timeout, schema_version check) in `studio/src/lib/db.ts`
- [ ] T006 [MOT-97] Write Drizzle mirror of every table in data-model in `studio/src/lib/schema.ts`
- [ ] T007 [MOT-98] [P] Implement session token and origin check middleware in `studio/src/lib/token.ts` and `studio/src/middleware.ts`
- [ ] T008 [MOT-99] [P] Implement `mb` bridge (action whitelist, spawn `uv run mb ... --json`, parse report) in `studio/src/lib/mb.ts` and `studio/src/app/api/mb/route.ts`
- [ ] T009 [MOT-100] [P] Implement SSE events route polling `change_event.seq` every 500 ms in `studio/src/app/api/events/route.ts` and client hook `studio/src/lib/events.ts`
- [ ] T010 [MOT-101] [P] Implement media route (realpath allowlist of project folders, HTTP Range) in `studio/src/app/api/media/route.ts` and `studio/src/lib/media.ts`
- [ ] T011 [MOT-102] Build app shell (dark layout, top bar, toast with verified and not verified lists, Kbd help overlay) in `studio/src/app/layout.tsx` and `studio/src/components/ui/`
- [ ] T012 [MOT-103] [P] Implement keyboard shortcut registry (Space, J/K/L, arrows, A, R, E, V, Q, ?) in `studio/src/lib/shortcuts.ts`
- [ ] T013 [MOT-104] Build project bin (grid of tiles with hero frame, aspect, stage) in `studio/src/app/page.tsx`
- [ ] T014 [MOT-105] [P] Tests: token and origin rejection, media path escape rejected in `studio/tests/unit/security.test.ts`

## Phase 3: User Story 1 - Board view tied to the song (P1) 🎯 MVP

**Goal**: Cards over a waveform, editable, playable from any shot.

**Independent Test**: 23 shot board loads, play from card starts at shot time, timing edit survives reload.

- [ ] T015 [MOT-106] [US1] Implement shot PATCH with zod, optimistic `updated_at` check (409), neighbour boundary transaction, dirty and state rules, change_event in `studio/src/app/api/shots/[id]/route.ts`
- [ ] T016 [MOT-107] [P] [US1] Build ShotCard (aspect correct frame, info bar, state dot, selection) in `studio/src/components/board/ShotCard.tsx`
- [ ] T017 [MOT-108] [US1] Build Board grid with virtualisation and lazy thumbnails in `studio/src/components/board/Board.tsx` and `studio/src/app/p/[id]/page.tsx`
- [ ] T018 [MOT-109] [US1] Build Timeline (wavesurfer from stored peaks, beat and line markers, shot regions, snap within 120 ms, playhead) in `studio/src/components/board/Timeline.tsx`
- [ ] T019 [MOT-110] [P] [US1] Build FilmStrip under the waveform in `studio/src/components/board/FilmStrip.tsx`
- [ ] T020 [MOT-111] [US1] Build SidePanel editing all shot fields and characters in `studio/src/components/board/SidePanel.tsx`
- [ ] T021 [MOT-112] [US1] Wire live updates from SSE to board state in `studio/src/app/p/[id]/page.tsx`
- [ ] T022 [MOT-113] [P] [US1] E2E: load board, edit field, drag boundary, reload, chat edit appears within 3 s in `studio/tests/e2e/board.spec.ts`

## Phase 4: User Story 2 - Start from a brainstorm or a template (P1)

**Goal**: No blank page.

**Independent Test**: From only a song and lyrics, either path gives a drafted board.

- [ ] T023 [MOT-114] [US2] Build start page (song file path or upload into project folder, lyrics, idea, aspect, look) calling `mb project new` and `mb analyze` in `studio/src/app/new/page.tsx`
- [ ] T024 [MOT-115] [P] [US2] Build TemplatePicker tiles with sample frame strips in `studio/src/components/start/TemplatePicker.tsx`
- [ ] T025 [MOT-116] [US2] Implement brainstorm route (`claude -p` with prompt template and analysis, JSON concept schema, `CLAUDE_MISSING`) in `studio/src/app/api/brainstorm/route.ts` and `studio/src/lib/prompts/brainstorm.md`
- [ ] T026 [MOT-117] [P] [US2] Build BrainstormForm and ConceptCards (three side by side, pick or mix, then `mb draft`) in `studio/src/components/start/`
- [ ] T027 [MOT-118] [US2] Add save as template (`mb` action `template_save`, strips song specific parts) in `engine/src/motionboard/storyboard/templates.py` and SidePanel menu
- [ ] T028 [MOT-119] [P] [US2] E2E: template path drafts a board; brainstorm without `claude` shows the needs Claude message in `studio/tests/e2e/start.spec.ts`

## Phase 5: User Story 3 - Review and approve, card by card (P1)

**Goal**: Gates and per card review in the board.

**Independent Test**: Reject plate with note, regenerate, approve; history keeps both and the note.

- [ ] T029 [MOT-120] [US3] Build VersionStrip (plates, clips, prompts, set active) in `studio/src/components/review/VersionStrip.tsx`
- [ ] T030 [MOT-121] [P] [US3] Build ApproveBar and NoteBox (A and R shortcuts, note required on reject) in `studio/src/components/review/`
- [ ] T031 [MOT-122] [US3] Add `mb review` (approve or reject a version, move states, note) in `engine/src/motionboard/cli.py`
- [ ] T032 [MOT-123] [US3] Build GateBar (Storyboard, Plates, Clips, Final; disabled with reason until rules pass) in `studio/src/components/board/GateBar.tsx`
- [ ] T033 [MOT-124] [US3] Build plate request flow (adapter picker, cost confirm modal, upload) in `studio/src/components/review/PlateRequest.tsx`
- [ ] T034 [MOT-125] [P] [US3] E2E: reject, upload, approve, gate approve in `studio/tests/e2e/review.spec.ts`

## Phase 6: User Story 4 - Watch renders live, safely (P2)

**Goal**: Queue and memory visible and controllable.

**Independent Test**: 3 shot render, pause after shot 1, resume, no shot renders twice.

- [ ] T035 [MOT-126] [P] [US4] Add proxy clip generation (240 px, after each clip) in `engine/src/motionboard/finish/proxy.py` and worker hook
- [ ] T036 [MOT-127] [US4] Build QueuePanel drawer (progress, time left, sec per frame, drag reorder, pause, resume, stop) in `studio/src/components/queue/QueuePanel.tsx`
- [ ] T037 [MOT-128] [P] [US4] Build MemoryMeter (free percent vs kill floor, swap vs ceiling, warning band) in `studio/src/components/queue/MemoryMeter.tsx`
- [ ] T038 [MOT-129] [US4] Show guard stop reason and suggestion on the card in `studio/src/components/board/ShotCard.tsx`
- [ ] T039 [MOT-130] [US4] Inline clip playback and hover scrub on proxies in `studio/src/components/board/ShotCard.tsx`
- [ ] T040 [MOT-131] [US4] Build settings page (guard presets via `mb guard`, adapters with test, paths, accent) in `studio/src/app/settings/page.tsx`
- [ ] T041 [MOT-132] [P] [US4] E2E: queue pause, resume, stop with stub backend in `studio/tests/e2e/queue.spec.ts`

## Phase 7: User Story 5 - Animatic and export (P2)

**Goal**: Pacing check and files out.

**Independent Test**: Animatic cuts match card times; JSON round trip identical.

- [ ] T042 [MOT-133] [US5] Build Animatic full screen player (plates or clips per shot over song, lyric line, J/K/L) in `studio/src/components/animatic/Animatic.tsx`
- [ ] T043 [MOT-134] [P] [US5] Implement PDF contact sheet export in `engine/src/motionboard/storyboard/export_pdf.py`
- [ ] T044 [MOT-135] [P] [US5] Implement self contained HTML export in `engine/src/motionboard/storyboard/export_html.py`
- [ ] T045 [MOT-136] [US5] Add export and import menu (JSON, PDF, HTML) in `studio/src/components/board/ExportMenu.tsx`
- [ ] T046 [MOT-137] [P] [US5] E2E: animatic timing and JSON round trip in `studio/tests/e2e/animatic-export.spec.ts`

## Phase 8: Polish

- [ ] T047 [MOT-138] [P] Write skill `skills/mb-studio/SKILL.md` (start, open URL, stop; mention chat and Studio share state)
- [ ] T048 [MOT-139] [P] Light theme toggle in `studio/src/styles/tokens.css`
- [ ] T049 [MOT-140] Performance pass with the 80 shot fixture (under 5 s) in `studio/tests/e2e/perf.spec.ts`
- [ ] T050 [MOT-141] Run quickstart.md steps 1 to 8 and record results in `specs/002-storyboard-studio/checklists/quickstart-run.md`

## Dependencies

- Needs 001 Foundational (schema, `mb`, events). US3 needs 001 US2 plate adapters for the plate request flow; US4 needs 001 worker.
- US1 first; US2 and US3 after US1; US4 and US5 after US3.

## Parallel examples

- Foundational: T007, T008, T009, T010, T012 together.
- US1: T016 and T019 alongside T018.
- US4: T035 and T037 alongside T036.

## Implementation strategy

MVP is US1 (board) with US3 (review and gates): the Boords replacement. Then US2 (brainstorm and templates). Then US4 (queue) and US5 (animatic, exports).
