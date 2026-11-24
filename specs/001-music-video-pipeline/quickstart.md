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
uv run mb project new --title smoke --song tests/fixtures/song10s.wav --lyrics-file tests/fixtures/lyrics.txt --idea "paper boats" --aspect 9:16
uv run mb analyze --project <id>
uv run mb draft --project <id> --template "Mood Loop"
uv run mb approve --project <id> --stage storyboard
uv run mb adapter --add --kind manual --config '{"watch_folder":"plates/inbox"}'
# copy tests/fixtures/plates/shot-*.png into the project's plates/inbox
uv run mb plates --project <id> --adapter manual
uv run mb approve --project <id> --stage plates
MB_BACKEND=stub uv run mb clips --project <id> && uv run mb worker
uv run mb approve --project <id> --stage clips
uv run mb finish --project <id>
```
Expect: final MP4 duration equals the segment, cuts within one frame of shot times (`verified` list says so), cover and metadata written.

## 3. Real run (LTX-2.3)
Same as step 2 with a 3 shot template and `mb clips --preset balanced`. Expect fit check printed, guard preset printed, 3 clips, no out of memory.

## 4. Resume
Stop the worker during shot 2 (`mb queue --stop`), run `mb worker` again. Expect shot 1 not re-rendered.

## 5. Guard
`mb guard --create tight --start 90 --kill 85 --swap 0` then `mb clips --preset tight`. Expect the job to wait or stop with a `GUARD_STOPPED` reason and a suggestion.

## 6. Paid adapter
Add an `http` adapter with `cost_per_image_usd: 0.01`, run `mb plates` without `--confirm-cost`. Expect `COST_NOT_CONFIRMED` with the estimate and no request sent.
