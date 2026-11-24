# Install

Motionboard runs on your own machine. Nothing is hosted and nothing is downloaded without you running the command.

## What you need

| Item | Version | Why |
|---|---|---|
| Apple Silicon Mac | macOS 14 or later, 32 GB memory or more | LTX-2.3 on MLX (Linux works for everything except the MLX backend) |
| uv | any recent | runs the Python engine |
| ffmpeg | 7 or later | cuts, grade, assembly |
| Node | 20 or later | HyperFrames renders the animation packs |
| Claude Code | current | the plugin skills drive the engine |

## Steps

1. Clone the repo and install the engine:

   ```bash
   git clone https://github.com/navjyotnishant/motionboard ~/dev/motionboard
   cd ~/dev/motionboard/engine
   uv sync
   uv run mb db migrate
   ```

2. Check the machine. Nothing is installed by this command:

   ```bash
   uv run mb setup
   uv run mb setup --fix-plan   # exact install and download steps for anything missing
   ```

3. Download the video model yourself. `mb setup --fix-plan` prints the command and the licence link.
   LTX-2.3 is free to use under its licence for organisations under USD 10M annual revenue:
   https://huggingface.co/Lightricks/LTX-2.3/blob/main/LICENSE. Motionboard never bundles weights.

4. Optional extras:

   ```bash
   uv sync --extra align    # mlx-whisper, better sung line timing
   uv sync --extra vocals   # demucs, vocal stem for lip-sync shots
   ```

5. Install the plugin in Claude Code from the repo folder, then ask Claude to "make a music video".

## Where things live

| Path | What | Override |
|---|---|---|
| `~/.motionboard/motionboard.db` | SQLite database (WAL mode) | `MB_HOME`, `MB_DB` |
| `~/Motionboard/projects/<slug>` | project folders: audio, plates, clips, out | `MB_PROJECTS` |

Set `MB_BACKEND=stub` to run the whole pipeline without a GPU (solid colour clips). Tests and CI use it.
