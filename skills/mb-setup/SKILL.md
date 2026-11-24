---
name: mb-setup
description: Check that this Mac is ready for Motionboard and explain what is missing. Use when the creator says "set up Motionboard", "is my machine ready", "what do I need to install", "check setup", or before the first render. Reports machine, tools, model weights and memory guard presets; never downloads or installs anything on its own.
---

# Motionboard: Setup check

From the plugin's `engine/` folder:

```bash
uv sync                                   # first time only: installs the engine's Python packages
uv run mb db migrate --json
uv run mb setup --json
```

Summarise for the creator in plain words:

- Machine: chip, memory, free disk, free memory now.
- Tools: uv, ffmpeg, Node, HyperFrames, ltx-2-mlx. Optional: voice alignment (align extra), vocal isolation (vocals extra).
- Models: present, partial or missing, each with its size and licence.
- `ready_for_clips`: whether clips can render now.

## When something is missing

Run `uv run mb setup --fix-plan --json` and show the steps. Then:

- Never run a download or install without the creator's go ahead. Model weights are large (LTX-2.3 about 29 GB, its text encoder about 7.5 GB).
- The creator accepts each model's licence on Hugging Face and logs in (`hf auth login`) themselves. Never ask for or handle their token.
- If a download stalls on resume, `HF_HUB_DISABLE_XET=1` is already in the commands.

## Memory guard

Show the presets with `uv run mb guard --json` and explain in one line each:

- safe: waits for 45% free memory, stops below 12% or after 2 GB of new swap.
- balanced (default): 35%, 8%, 4 GB.
- max: 25%, 6%, 8 GB; only if the creator accepts more risk.

Let the creator pick (`mb guard --set <name>`) or create their own (`mb guard --create <name> --start --kill --swap`). Never change it on your own.

Wan 2.2 and LTX-2.5 are in the backlog: both ran out of memory on a 36 GB Mac in tests.
