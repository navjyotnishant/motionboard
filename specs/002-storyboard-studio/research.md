# Research: Storyboard Studio

Versions checked on the reference Mac via npm on 2026-11-24: next 16.4.6, better-sqlite3 13.2.0, drizzle-orm 0.45.4, wavesurfer.js 8.1.0. Node 24.7.0.

## S1. Framework
- **Decision**: Next.js 16 App Router, run with `next start -H 127.0.0.1 -p 4317` after a one time `next build` during setup.
- **Rationale**: Creator approved Next.js locally; route handlers give SSE, Range streaming and a CLI bridge in one process.
- **Alternatives**: Vite SPA plus a small Node server (two pieces to ship); Python served page (weaker UI tooling).

## S2. Database access
- **Decision**: better-sqlite3 with WAL and `busy_timeout=5000`; Drizzle schema mirrors engine tables for types only. Studio refuses to start if `schema_version` differs from what it was built for and tells the creator to run `mb db migrate`.
- **Rationale**: Engine owns migrations (Principle VIII); sync driver is simple and fast for one user.
- **Alternatives**: node:sqlite (still maturing), Prisma (own migrations, heavier).

## S3. Live sync
- **Decision**: `/api/events` SSE; server polls `SELECT max(seq)` every 500 ms and pushes new `change_event` rows; client refetches affected entities.
- **Rationale**: Meets the 3 s goal, no file watchers, works for engine and chat writes.
- **Alternatives**: WebSockets (not needed), fs watch on the DB (unreliable with WAL).

## S4. Ruled actions
- **Decision**: `/api/mb` maps a whitelist of actions to `mb` arguments, spawns `uv run mb ... --json` in `engine/`, returns the report. Long jobs only enqueue; the worker runs them.
- **Rationale**: One rule implementation; Studio cannot bypass gates or cost confirmation.

## S5. Brainstorm
- **Decision**: `/api/brainstorm` runs `claude -p` (Claude Code headless) with a fixed prompt template and the song analysis, asking for JSON matching the concept schema, then `mb concepts add`. If the `claude` CLI is missing, the form says Brainstorm needs Claude and offers templates. The same flow is available in chat through the `mb-storyboard` skill.
- **Rationale**: Uses the creator's own Claude; no API keys in the app.

## S6. Waveform and timeline
- **Decision**: wavesurfer.js 8 with the Regions plugin; peaks come precomputed from `song_analysis.waveform_peaks` so large files load instantly; beat and line markers drawn as a thin overlay; region drag snaps to nearest beat or line within 120 ms.

## S7. Media streaming and hover scrub
- **Decision**: `/api/media?path=` serves files only under registered project folders (realpath check), supports HTTP Range for video. Engine makes 240 px proxy clips (`finish/proxy.py`) after each clip render; cards scrub the proxy by mapping pointer x to `currentTime`.

## S8. Look and feel
- **Decision**: Dark neutral surface (#0E0F11 base, #16181B panels, #24272C lines), text #E7E7E9 and #8B8F97, one accent (warm amber #F2A33A, configurable), status colours muted (green approved, red redo, blue rendering). Inter for UI, tabular numbers for timecodes. Frames dominate: cards are the plate at full card width with a thin info bar; chrome uses 1 px lines, no shadows. Detail in a right side panel; queue in a bottom drawer.
- **Shortcuts**: Space play/pause, J/K/L shuttle, Left/Right previous/next shot, A approve, R reject, E edit focused field, V versions, Q queue drawer, ? help.

## S9. Security on localhost
- **Decision**: Bind 127.0.0.1 only; random token generated at start, printed in the URL once, stored in an httpOnly cookie; mutating routes require it and check `Origin`.
- **Rationale**: Stops other websites in the browser from calling the local API.

## S10. Exports
- **Decision**: JSON via `mb export`; PDF contact sheet via Pillow multi page in `export_pdf.py`; self contained HTML (inline thumbnails as data URIs, no scripts beyond a tiny viewer) via `export_html.py`.
