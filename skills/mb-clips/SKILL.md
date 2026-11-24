---
name: mb-clips
description: Make image plates and local video clips for an approved Motionboard storyboard. Use when the creator says "make the plates", "generate images for the shots", "animate the shots", "render the clips", "how is the render going", "pause the render" or "redo shot 7". Works with any image source (own files, a local model, an HTTP API, or an MCP image tool such as Muse) and renders locally with LTX-2.3 under the memory guard.
---

# Motionboard: Plates and clips

Run engine commands from the plugin's `engine/` folder as `uv run mb <command> --json`. Relay each report's `verified` and `not_verified` lists honestly.

## Rules

- The storyboard gate must be approved before plates; the plates gate before clips. Never approve on the creator's behalf.
- Never spend money without a clear yes to a stated amount. Paid adapters refuse with `COST_NOT_CONFIRMED` and the estimate; show it, wait for yes, then re-run with `--confirm-cost`.
- Never print or paste API keys. Adapters reference keys by `key_file` or `key_env` only.
- Never loosen guard presets on your own. Show the active preset; change it only when the creator asks.

## 1. Pick the image source

```bash
uv run mb adapter --list --json
```

Ask which source to use if it is not obvious:

- **Own images**: `uv run mb plate upload --project <id> --shot 3 --file <img> --json`, or drop `shot-03.png` style files into `<project>/plates/inbox/` and run `mb plates --adapter manual`.
- **MCP image tool (handoff)**: add once with `mb adapter --add muse --kind handoff --cost 0.01 --config '{"hint":"Muse"}'`. Then `mb plates --adapter muse --confirm-cost` (after the yes) creates pending requests; for each, `mb plate requests` gives the prompt, size and any character reference image. Generate the image with the creator's MCP tool (pass the reference image for character shots so faces stay consistent), save it, then `mb plate fulfil --request <id> --file <img>`.
- **Local model**: `--kind command` with a `cmd` list using `{prompt} {out} {w} {h} {ref} {seed}`.
- **HTTP API**: `--kind http` with `url`, `body`, `image_field`, and `key_file` or `key_env`.

## 2. Review plates

```bash
uv run mb sheet --project <id> --kind plates --json
```

Show the sheet. For each shot the creator dislikes: `mb review --shot N --kind plate --decision reject --note "<why>"`, edit the shot if needed (`mb shot set`), and request again with `--shots N`. Approve the rest with `mb review --decision approve --all --shot 0` once the creator says so, then `mb approve --stage plates`.

## 3. Render clips

```bash
uv run mb guard --json                     # show the active guard preset
uv run mb clips --project <id> --json      # fit check, then queue; refuses with suggestions if it will not fit
uv run mb worker --detach --json           # renders in the background, one shot at a time
```

Tell the creator the estimated time from the report. LTX-2.3 takes about 4 to 5 seconds per frame at 576x1024 on an M3 Max.

## 4. Watch, pause, stop, redo

```bash
uv run mb queue --json                     # progress, memory, guard
uv run mb queue --pause --json             # pause after the current shot
uv run mb queue --resume --json && uv run mb worker --detach --json
uv run mb queue --stop --json              # stop now
uv run mb clips --project <id> --shots 7 --redo --json
```

If the guard or fit check stopped a shot, read its `stop_reason` and `suggestion` and offer them; do not retry the same settings blindly.

## 5. Review clips

`mb sheet --kind clips`, then per shot `mb review --kind clip --decision approve|reject --note`. Finished shots are never re-rendered unless `--redo`. When every clip is approved and the creator says yes: `mb approve --stage clips`, then hand over to `mb-finish`.
