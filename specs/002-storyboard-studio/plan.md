# Implementation Plan: Storyboard Studio (local web app)

**Branch**: `002-storyboard-studio` | **Date**: 2026-11-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-storyboard-studio/spec.md`

**Depends on**: `001-music-video-pipeline` (engine, DB schema, `mb` CLI).

## Summary

A Next.js app in `studio/`, served on `127.0.0.1` by a plugin command, that reads and writes the shared SQLite file. Plain field edits go straight to the DB; anything with rules (draft, approve, plates, clips, queue control, export) calls the `mb` CLI with `--json`, so business rules live only in the engine. Live updates stream from the `change_event` table over Server Sent Events. The look is a dark, imagery first media tool: large frames, film strip and waveform timeline, hover scrub, inline playback, keyboard first.

## Technical Context

**Language/Version**: TypeScript 5, Node 20+ (24 on the reference Mac).

**Primary Dependencies**: Next.js 16 (App Router, route handlers), React 19, Tailwind CSS 4, better-sqlite3 13 (sync driver, WAL), Drizzle ORM 0.45 (typed read model mirroring the engine schema, no migrations of its own), wavesurfer.js 8 (waveform, regions), zod (input validation), Radix primitives (dialogs, panels), lucide icons.

**Storage**: Shared SQLite file from 001 (`~/.motionboard/motionboard.db`). Media read from project folders via a path guarded route.

**Testing**: Vitest (lib and route handlers against a temp DB), Playwright (board, keyboard, review, animatic flows) using the stub backend.

**Target Platform**: Any modern Chromium, Safari or Firefox on the same Mac; served only on 127.0.0.1.

**Project Type**: Local web application bundled in the plugin.

**Performance Goals**: 23 shot board interactive under 2 s, 80 shots under 5 s (lazy thumbnails, virtualised strip); change to screen under 3 s (SSE, 500 ms DB poll on `change_event.seq`); hover scrub at 30 fps using low res proxy clips.

**Constraints**: No outbound network from the app; no keys in browser or DB; bind to loopback only; random per start session token required on mutating routes to block other local sites (CSRF).

**Scale/Scope**: One creator; about 10 screens worth of views folded into one page plus panels.

## Constitution Check

| Principle | How this plan complies | Status |
|---|---|---|
| I. Storyboard First | Clips actions disabled until storyboard and plates gates are approved (engine enforces, UI mirrors). | Pass |
| II. Local First | Loopback only, no account, no outbound calls; paid plate requests need a confirm click showing cost. | Pass |
| III. Never Crash | Queue panel shows live memory vs guard; settings edit presets through `mb guard`. | Pass |
| IV. No Weights | Studio has no model handling; setup page links to `mb setup` output. | Pass |
| V. Review Gates | Gate bar with approve buttons that call `mb approve`. | Pass |
| VI. Honest Verification | Each action toast shows the `verified` and `not_verified` lists from `mb`. | Pass |
| VII. Simple and Portable | Same DB and JSON export; no Studio only tables. | Pass |
| VIII. One Source, media tool look | Same DB, SSE sync, dark imagery first UI. | Pass |

Post design re-check: Pass.

## Project Structure

### Documentation (this feature)

```text
specs/002-storyboard-studio/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── http-api.md
│   └── ui.md
└── tasks.md
```

### Source Code

```text
studio/
├── package.json
├── next.config.ts
├── tailwind.css
├── src/
│   ├── app/
│   │   ├── layout.tsx                 # dark shell, fonts, session token
│   │   ├── page.tsx                   # project bin (grid of projects)
│   │   ├── new/page.tsx               # start: brainstorm or template
│   │   ├── p/[id]/page.tsx            # the board
│   │   ├── settings/page.tsx          # guard presets, adapters, paths
│   │   └── api/
│   │       ├── events/route.ts        # SSE from change_event
│   │       ├── media/route.ts         # path guarded file stream with Range
│   │       ├── shots/[id]/route.ts    # PATCH plain fields
│   │       ├── mb/route.ts            # POST action -> mb CLI bridge
│   │       └── brainstorm/route.ts    # POST -> claude -p headless
│   ├── components/
│   │   ├── board/ (Board, ShotCard, FilmStrip, Timeline, SidePanel, GateBar)
│   │   ├── review/ (VersionStrip, NoteBox, ApproveBar)
│   │   ├── queue/ (QueuePanel, MemoryMeter)
│   │   ├── animatic/ (Animatic)
│   │   ├── start/ (BrainstormForm, ConceptCards, TemplatePicker)
│   │   └── ui/ (Button, Panel, Toast, Kbd)
│   ├── lib/
│   │   ├── db.ts                      # better-sqlite3 + drizzle, WAL, busy timeout
│   │   ├── schema.ts                  # drizzle mirror of engine schema
│   │   ├── mb.ts                      # spawn `mb --json`, parse report
│   │   ├── events.ts                  # client SSE hook
│   │   ├── shortcuts.ts
│   │   ├── media.ts                   # allowlist check
│   │   └── token.ts
│   └── styles/tokens.css              # colours, spacing, type scale
└── tests/
    ├── unit/
    └── e2e/
engine/src/motionboard/studio_cmd.py   # `mb studio start|stop|status` (build once, start on 127.0.0.1:4317)
engine/src/motionboard/finish/proxy.py # low res proxy clips for hover scrub
engine/src/motionboard/storyboard/export_pdf.py, export_html.py
skills/mb-studio/SKILL.md
```

**Structure Decision**: Studio is a thin UI over the engine. Reads via Drizzle; plain writes via one PATCH route that also writes `change_event`; ruled actions via `mb`. Exports and proxies are engine features so chat and Studio share them.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Next.js instead of a static page | Creator chose a media grade UI with routing, streaming and server routes | Static HTML would need its own server anyway for SQLite and file streaming |
