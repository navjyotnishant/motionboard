# Quickstart: validate the pipeline

## Prerequisites
- Apple Silicon Mac, macOS 14+, 32 GB+ memory.
- uv, ffmpeg 7+, Node 20+ (for HyperFrames), Claude Code with the plugin installed.
- LTX-2.3 weights downloaded by you after accepting the license (`mb setup --fix-plan` prints the steps).

## 1. Setup check
```bash
cd engine && uv sync && uv run mb db migrate && uv run mb setup --json
```
Expect: `ok: true`, a tools table, models present or missing with license links. No downloads happen.

## 2. Smoke run with the stub backend (no GPU)
```bash
bash scripts/smoke.sh mood-loop cosmic
```
The script runs: project new, analyze, draft, approve storyboard, manual plates from `tests/fixtures/plates`,
review, approve plates, clips, worker, review clips, approve clips, theme, finish. It prints the project folder.
Expect: every step `ok`, a final MP4 in `out/` whose duration is the segment plus the 1.5 s tail, a cover and metadata.

## 3. Real run (LTX-2.3)
Same steps without `MB_BACKEND=stub`, on a 3 shot board, with `mb guard --set balanced`.
Expect: fit check printed, guard preset printed, 3 clips, no out of memory.

## 4. Resume
Stop the worker during shot 2 (`mb queue --stop`), queue again with `mb clips -p <id>`, run `mb worker`.
Expect: shot 1 not re-rendered.

## 5. Guard
`mb guard --create tight --start 90 --kill 85 --swap 0`, `mb guard --set tight`, then `mb clips -p <id>`.
Expect: the clip is refused by the fit check or stopped with `GUARD_STOPPED`, with a suggestion.
Set the guard back with `mb guard --set balanced`.

## 6. Paid adapter
`mb adapter --add paid --kind http --config '{"url": "http://127.0.0.1:9/x", "key_env": "MB_TEST_KEY"}' --cost 0.01`,
then `mb plates -p <id> --adapter paid` without `--confirm-cost`.
Expect: `COST_NOT_CONFIRMED` with the estimate and no request sent.
