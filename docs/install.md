# Install

One defined way to install Motionboard: clone the repo and run `./install.sh`. It checks your Mac, installs the
engine, the `mb` command, the Studio and the Claude Code plugin, and asks before anything large. Run it again any
time; it skips what is already done.

## 1. Before you start

| You need | Version | Install it with |
|---|---|---|
| Apple Silicon Mac | macOS 14+, 32 GB memory or more | (Linux works for everything except local LTX clips) |
| Homebrew | any | https://brew.sh |
| uv | any recent | `brew install uv` |
| ffmpeg | 7 or later | `brew install ffmpeg` |
| Node | 20 or later | `brew install node` |
| git | any | `xcode-select --install` |
| Claude Code | current | https://docs.claude.com/en/docs/claude-code |
| Free disk | about 45 GB | model weights (29 + 7.5 + 1.6 GB) plus projects. Add about 44 GB if you also install LTX-2.5 |

The installer checks all of these and prints the exact command for anything missing. It does not install system
tools for you.

## 2. Install

```bash
git clone https://github.com/navjyotnishant/motionboard ~/motionboard
cd ~/motionboard
./install.sh --check     # optional: see what it would do, changes nothing
./install.sh
```

What it does, in order:

| Step | What happens | Asks first? |
|---|---|---|
| 1. Machine | Checks chip and memory | no |
| 2. Tools | Checks uv, ffmpeg, git, Node; stops with the install command if one is missing | no |
| 3. Engine | `uv sync` into `engine/.venv`, with demucs (vocal isolation) and mlx-whisper (line timing); creates the database at `~/.motionboard/motionboard.db` | no |
| 4. `mb` command | Writes `~/.local/bin/mb`, a launcher for the engine; tells you if that folder is not on your PATH | no |
| 5. ltx-2-mlx | The video model runtime. Uses yours if found, else clones it into `~/.motionboard/ltx-2-mlx` (about 1 GB of packages) | yes |
| 6. Model weights | LTX-2.3 q8 (29 GB), Gemma 3 12B 4-bit text encoder (7.5 GB), Whisper turbo (1.6 GB, optional), LTX-2.5 q8 (43 GB, optional) and its detail add-on (0.3 GB, optional, gated). Shows each size and licence | yes, one by one |
| 7. Studio | `npm ci` and `next build` in `studio/` | no |
| 8. Plugin | `claude plugin marketplace add <repo>` and `claude plugin install motionboard@motionboard` | no |
| 9. Check | Runs `mb setup` and prints the result | no |

Options: `--yes` (answer yes to every question), `--no-models`, `--no-studio`, `--no-plugin`, `--no-extras`.

Model licences: LTX-2.3 is free to use under its licence for organisations under USD 10M annual revenue
(https://huggingface.co/Lightricks/LTX-2.3/blob/main/LICENSE). Gemma follows the Gemma Terms of Use
(https://ai.google.dev/gemma/terms). If Hugging Face asks you to log in or accept a licence, do it yourself with
`hf auth login`; Motionboard never handles your token.

## 3. Check it worked

```bash
mb setup                 # ready_for_clips: True means clips can render
```

Restart Claude Code, then say "make a music video for <song>". Or open the Studio with `mb studio start`.

## 4. Update

```bash
cd ~/motionboard && git pull && ./install.sh
claude plugin marketplace update motionboard
```

## 5. Uninstall

```bash
cd ~/motionboard && ./uninstall.sh              # mb command, plugin, Studio build, engine environment
./uninstall.sh --all-data                       # also ~/.motionboard (asks first)
```

Your projects in `~/Motionboard/projects` and model weights in `~/.cache/huggingface` are never deleted by these
scripts.

## Where things live

| Path | What | Override |
|---|---|---|
| `~/.motionboard/motionboard.db` | database (shared by chat and Studio) | `MB_HOME`, `MB_DB` |
| `~/Motionboard/projects/<slug>` | project folders: audio, plates, clips, out | `MB_PROJECTS` |
| `~/.motionboard/ltx-2-mlx` | video model runtime, if the installer added it | `MB_LTX_BIN` |
| `~/.cache/huggingface/hub` | model weights | `HF_HOME` |
| `~/.local/bin/mb` | the `mb` command | `MB_BIN_DIR` at install time |

Set `MB_BACKEND=stub` to run the whole pipeline without a GPU (solid colour clips); tests and CI use it.

## Troubleshooting

- `mb: command not found`: add `export PATH="$HOME/.local/bin:$PATH"` to `~/.zshrc` and open a new terminal.
- A model download stalls: run it again; the installer already sets `HF_HUB_DISABLE_XET=1`, which resumes reliably.
- `ready_for_clips: False`: run `mb setup --fix-plan` for the exact missing step, or run `./install.sh` again.
- Studio will not start: `mb studio start --rebuild`; the log is in `~/.motionboard/studio.log`.

## LTX-2.5 (optional)

LTX-2.5 is the newer video model. On the first real video it followed the vocal more closely on lip-sync shots than LTX-2.3. It is optional, and LTX-2.3 stays the default.

| Piece | Size | What it does |
|---|---|---|
| `dgrauet/ltx-2.5-mlx-q8` | 43 GB | The model and its own text encoder. The installer skips the 20 GB full-quality transformer and the distilled LoRA |
| `Lightricks/LTX-2.5-22b-IC-LoRA-Pixel-Spatial-Upscaler` | 0.3 GB | The detail add-on. With it, lip-sync shots render in DFR mode, where the second pass runs at full resolution and faces stay sharp. Without it they use the fast path, which is slightly soft |

The detail add-on is gated. Do this once before the installer can download it:

1. Sign in at https://huggingface.co/Lightricks/LTX-2.5-22b-IC-LoRA-Pixel-Spatial-Upscaler and accept the licence.
2. Run `hf auth login` on the Mac.
3. Run `./install.sh` again and say yes to the add-on.

Use it for one run, without changing the project:

```bash
mb clips --project <id> --shots 14,16 --redo --backend ltx25 --json
mb worker --detach --json
```

Each result is a new take. The take in use changes only when you pick one in the Studio or with `mb use`.

Limits measured on a 36 GB M3 Max, 576x1024:

- A 97-frame lip-sync shot peaks at about 17.7 GB and takes about 9 minutes. Close other heavy apps first.
- Only lip-sync shots are measured so far. The fit check refuses other LTX-2.5 shots until they are measured.
- Run one render at a time. A large download or a second render alongside it trips the memory guard.

| Setting | Meaning |
|---|---|
| `MB_LTX25_SNAPSHOT` | folder of the LTX-2.5 weights, if not in the Hugging Face cache |
| `MB_LTX25_DETAIL_LORA` | file or folder of the detail add-on, if not in the Hugging Face cache |

