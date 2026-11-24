---
name: mb-setup
description: Check that this Mac is ready for Motionboard and explain what is missing. Use when the creator says "set up Motionboard", "is my machine ready", "what do I need to install", "check setup", or before the first render. Reports machine, tools, model weights and memory guard presets; never downloads or installs anything on its own.
---

# Motionboard: Setup check

**Where `mb` runs.** On the creator's Mac, never in a cloud workspace.
- Claude Code: the terminal.
- Claude app (desktop or mobile, with the Mac linked): the Mac's shell tool (device bash or Desktop Commander). If `mb` is not on that shell's PATH, use `~/.local/bin/mb`. If no Mac tool is available, say the Mac must be linked through the Claude desktop app, and stop.
- Long jobs (clips, finish) run detached (`mb worker --detach`); check them with `mb queue --json` instead of waiting on one call.
- Images and videos it makes live on the Mac; stage or open them to show the creator.

First check that the `mb` command exists (`command -v mb`).

- If it does not, Motionboard is not installed yet. Tell the creator the one defined way to install it, which they run themselves:

  ```bash
  git clone https://github.com/navjyotnishant/motionboard ~/motionboard
  cd ~/motionboard && ./install.sh
  ```

  `./install.sh --check` reports what is missing without changing anything. Full guide: `docs/install.md`.
- If it does, run:

  ```bash
  mb setup --json
  ```

Summarise for the creator in plain words:

- Machine: chip, memory, free disk, free memory now.
- Tools: uv, ffmpeg, Node, HyperFrames, ltx-2-mlx. Optional: voice alignment (align extra), vocal isolation (vocals extra).
- Models: present, partial or missing, each with its size and licence.
- `ready_for_clips`: whether clips can render now.

## When something is missing

Run `mb setup --fix-plan --json` and show the steps. Running `./install.sh` again from the repo fixes most gaps; it asks before anything large. Then:

- Never run a download or install without the creator's go ahead. Model weights are large (LTX-2.3 about 29 GB, its text encoder about 7.5 GB).
- The creator accepts each model's licence on Hugging Face and logs in (`hf auth login`) themselves. Never ask for or handle their token.
- If a download stalls on resume, `HF_HUB_DISABLE_XET=1` is already in the commands.

## Memory guard

Show the presets with `mb guard --json` and explain in one line each:

- safe: waits for 45% free memory, stops below 12% or after 2 GB of new swap.
- balanced (default): 35%, 8%, 4 GB.
- max: 25%, 6%, 8 GB; only if the creator accepts more risk.

Let the creator pick (`mb guard --set <name>`) or create their own (`mb guard --create <name> --start --kill --swap`). Never change it on your own.

Wan 2.2 and LTX-2.5 are in the backlog: both ran out of memory on a 36 GB Mac in tests.
