# Studio quickstart run (T050)

Date: 2026-11-24, about 02:00 CT. Reference Mac (M3 Max, 36 GB). Studio built with Next.js 16.4.6.
Automated by the Playwright suite in `studio/tests/e2e` (7 tests, installed Chrome, stub backend, throwaway
`/tmp/mb-e2e`), plus a manual pass on the real LTX project from the 001 quickstart.

| Step | Result | How |
|---|---|---|
| 1. Start | pass | `mb studio start` built once and served 127.0.0.1:4317. Loopback answers (403 without the token); the LAN address 10.0.0.186:4317 refuses the connection |
| 2. Board and sync | pass | e2e `a-board`: panel edit persists across reload; a chat `mb shot set` shows in the open board within 3 s |
| 3. Timeline | pass | e2e `a-board`: dragging the first cut on the waveform moves it (snapped to a beat by the engine); reload keeps it |
| 4. Start flows | partly | e2e `e-start`: `/new` with the fixture song, template Mood Loop plus Cosmic drafts a board; with `claude` missing the "needs Claude Code" message shows. A live brainstorm with Claude was not run |
| 5. Review | pass | e2e `b-review`: reject with a note, upload a plate, approve all four with the A key, approve the plates gate |
| 6. Queue | pass | e2e `c-queue`: pause, queue, resume, worker renders 4 stub clips, stop. Found and fixed: `mb worker --detach` could not start (see below) |
| 7. Animatic and exports | pass | e2e `d-animatic-export`: animatic opens, L steps to shot 2; JSON export imports as a new project with the same shots. PDF and HTML exports checked by eye on the real project |
| 8. Performance | pass | e2e `f-perf`: the 80 shot fixture board renders all 80 cards in about 0.1 s after navigation (limit 5 s) |

Security checks (e2e `a-board` and `tests/unit/security.test.ts`): no token gives 403 on pages and APIs; a write
from another origin gives 403; `/api/media?path=/etc/passwd` gives 403; `..` escapes and symlinks out of a project
folder are refused; the mb bridge refuses unknown actions and bad arguments and never builds a shell string.

## Fixed during the run

- `mb worker --detach` started `python -m motionboard.cli`, which loads the CLI without its commands
  ("No such command 'worker'"). Added `motionboard/__main__.py` and a test that the module entry sees every command.
- Studio queue drawer read the pause state from job rows; it now reads the queue's pause setting.

## Not verified

- Live brainstorm with `claude -p` (it runs on the creator's own Claude account; left for the creator to try).
- Light theme and accent colours were not reviewed by eye.
- Wavesurfer is not used: the waveform, beats, lines and cut dragging are drawn on a canvas from the stored peaks.
