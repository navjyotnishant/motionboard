#!/usr/bin/env bash
# Motionboard installer. Run it from the repo you cloned:
#
#   ./install.sh            check, install what is safe to install, ask before anything large
#   ./install.sh --check    report only; change nothing
#   ./install.sh --yes      answer yes to every question (model downloads included)
#   ./install.sh --no-models --no-studio --no-plugin   skip those parts
#
# It never installs system tools (Homebrew, uv, ffmpeg, Node) for you: it prints the exact command.
# It never downloads model weights without showing the size and licence and getting a yes.
set -uo pipefail

REPO="$(cd "$(dirname "$0")" && pwd)"
ENGINE="$REPO/engine"
MB_HOME="${MB_HOME:-$HOME/.motionboard}"
BIN_DIR="${MB_BIN_DIR:-$HOME/.local/bin}"
LTX_DIR="${MB_LTX_DIR:-$MB_HOME/ltx-2-mlx}"
CHECK=0 YES=0 MODELS=1 STUDIO=1 PLUGIN=1 EXTRAS=1
for a in "$@"; do
  case "$a" in
    --check) CHECK=1 ;;
    --yes|-y) YES=1 ;;
    --no-models) MODELS=0 ;;
    --no-studio) STUDIO=0 ;;
    --no-plugin) PLUGIN=0 ;;
    --no-extras) EXTRAS=0 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "unknown option: $a"; exit 2 ;;
  esac
done

ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
miss() { printf '  \033[31m✗\033[0m %s\n' "$1"; }
note() { printf '  · %s\n' "$1"; }
step() { printf '\n\033[1m%s\033[0m\n' "$1"; }
ask()  { [ "$YES" = 1 ] && return 0; [ "$CHECK" = 1 ] && return 1; read -r -p "  $1 [y/N] " r; [[ "$r" =~ ^[Yy] ]]; }
run()  { if [ "$CHECK" = 1 ]; then note "would run: $*"; else "$@"; fi; }
FAIL=0

step "1. Machine"
if [ "$(uname -s)" = "Darwin" ] && [ "$(uname -m)" = "arm64" ]; then
  ok "Apple Silicon Mac ($(sysctl -n machdep.cpu.brand_string 2>/dev/null))"
  MEM=$(( $(sysctl -n hw.memsize) / 1073741824 ))
  if [ "$MEM" -ge 32 ]; then ok "${MEM} GB memory"; else miss "${MEM} GB memory: 32 GB or more is needed for LTX-2.3 clips"; fi
  MAC=1
else
  note "not an Apple Silicon Mac: storyboard, plates, Studio and finishing work; local LTX clips need Apple Silicon"
  MAC=0
fi

step "2. Tools (install these yourself if missing)"
need() { # name, check command, install hint
  if command -v "$2" >/dev/null 2>&1; then ok "$1: $($2 --version 2>&1 | head -1)"; else miss "$1 missing. Install: $3"; FAIL=1; fi
}
need "uv" uv "brew install uv   (or: curl -LsSf https://astral.sh/uv/install.sh | sh)"
need "ffmpeg" ffmpeg "brew install ffmpeg"
need "git" git "xcode-select --install"
if [ "$STUDIO" = 1 ]; then need "Node 20+" node "brew install node"; fi
if command -v node >/dev/null 2>&1; then
  NV=$(node -p 'process.versions.node.split(".")[0]')
  [ "$NV" -ge 20 ] || { miss "Node $NV is too old; 20 or later is needed (brew upgrade node)"; FAIL=1; }
fi
if [ "$FAIL" = 1 ]; then
  echo; echo "Install the missing tools above, then run ./install.sh again."; exit 1
fi

step "3. Engine (Python, in its own environment under engine/.venv)"
EXTRA_ARGS=()
if [ "$EXTRAS" = 1 ]; then
  EXTRA_ARGS=(--extra vocals)
  [ "$MAC" = 1 ] && EXTRA_ARGS+=(--extra align)
  note "with optional extras: demucs (vocal isolation for lip-sync)$([ "$MAC" = 1 ] && echo ', mlx-whisper (sung line timing)')"
fi
run uv sync --project "$ENGINE" "${EXTRA_ARGS[@]}" --quiet && [ "$CHECK" = 0 ] && ok "engine installed"
run env MB_HOME="$MB_HOME" "$ENGINE/.venv/bin/mb" db migrate --json >/dev/null && [ "$CHECK" = 0 ] && ok "database ready at $MB_HOME/motionboard.db"

step "4. The mb command"
SHIM="$BIN_DIR/mb"
if [ "$CHECK" = 1 ]; then
  note "would write $SHIM (runs $ENGINE/.venv/bin/mb)"
else
  mkdir -p "$BIN_DIR"
  cat > "$SHIM" <<EOF
#!/usr/bin/env bash
# Motionboard engine launcher, written by install.sh. Repo: $REPO
# Run the engine's own environment directly: "uv run" would re-sync it and drop the optional extras.
if [ -x "$ENGINE/.venv/bin/mb" ]; then exec "$ENGINE/.venv/bin/mb" "\$@"; fi
exec uv run --quiet --project "$ENGINE" mb "\$@"
EOF
  chmod +x "$SHIM"
  ok "mb installed at $SHIM"
fi
case ":$PATH:" in
  *":$BIN_DIR:"*) ok "$BIN_DIR is on your PATH" ;;
  *) miss "$BIN_DIR is not on your PATH. Add this line to ~/.zshrc, then open a new terminal:"
     echo "      export PATH=\"$BIN_DIR:\$PATH\"" ;;
esac

if [ "$MAC" = 1 ]; then
  step "5. Video model runtime (ltx-2-mlx)"
  LTX_BIN=""
  for c in "${MB_LTX_BIN:-}" "$(command -v ltx-2-mlx 2>/dev/null)" "$LTX_DIR/.venv/bin/ltx-2-mlx" "$HOME/dev/ltx-2-mlx/.venv/bin/ltx-2-mlx"; do
    [ -n "$c" ] && [ -x "$c" ] && { LTX_BIN="$c"; break; }
  done
  if [ -n "$LTX_BIN" ]; then
    ok "ltx-2-mlx found: $LTX_BIN"
  elif ask "ltx-2-mlx is not installed. Clone https://github.com/dgrauet/ltx-2-mlx to $LTX_DIR and install it (about 1 GB of Python packages)?"; then
    git clone --depth 1 https://github.com/dgrauet/ltx-2-mlx "$LTX_DIR" && \
      (cd "$LTX_DIR" && uv venv --python 3.12 --quiet && uv pip install --quiet -e .) && ok "ltx-2-mlx installed in $LTX_DIR"
  else
    miss "ltx-2-mlx not installed; clips cannot render until it is. Run ./install.sh again to install it."
  fi

  if [ "$MODELS" = 1 ]; then
    step "6. Model weights (downloaded by you, under their own licences)"
    HUB="${HF_HOME:-$HOME/.cache/huggingface}/hub"
    model() { # repo, size, licence, url, optional, what it is for, [extra hf args], [gated: 1]
      local dir="$HUB/models--${1//\//--}"
      if [ -d "$dir/snapshots" ] && [ -n "$(ls -A "$dir/snapshots" 2>/dev/null)" ]; then ok "$1 present ($6)"; return; fi
      echo "  $1"
      echo "    What it does: $6"
      echo "    Size: about $2. Licence: $3 ($4)"
      if [ "${8:-0}" = 1 ]; then
        echo "    Gated: sign in at https://huggingface.co/$1 and accept its licence once, and run 'hf auth login' on this Mac, before downloading."
      fi
      if ask "Download $1 now$([ "$5" = 1 ] && echo ' (optional)')?"; then
        # shellcheck disable=SC2086
        if HF_HUB_DISABLE_XET=1 uvx --from "huggingface_hub[cli]" hf download "$1" ${7:-}; then
          ok "$1 downloaded"
        else
          note "could not download $1. If it says access denied, accept the licence at https://huggingface.co/$1 and run: hf auth login"
        fi
      else
        note "skipped $1. Later: HF_HUB_DISABLE_XET=1 hf download $1 ${7:-}"
      fi
    }
    model "dgrauet/ltx-2.3-mlx-q8" "29 GB" "LTX-2 Community License, free under USD 10M annual revenue" "https://huggingface.co/Lightricks/LTX-2.3/blob/main/LICENSE" 0 \
      "the video model. It turns each approved still image (plate) into a moving clip, and makes lip-sync shots from the vocal. Needed for clips."
    model "mlx-community/gemma-3-12b-it-4bit" "7.5 GB" "Gemma Terms of Use" "https://ai.google.dev/gemma/terms" 0 \
      "the text encoder LTX-2.3 uses to read each shot's motion prompt. Needed for clips."
    model "mlx-community/whisper-large-v3-turbo" "1.6 GB" "MIT" "https://huggingface.co/openai/whisper-large-v3-turbo" 1 \
      "listens to the song and finds when each lyric line is sung, so shots cut and lyrics appear on the right words. Without it, line timing is estimated from the beats."
    model "dgrauet/ltx-2.5-mlx-q8" "43 GB" "LTX-2 Community License" "https://github.com/Lightricks/LTX-2/blob/main/LICENSE-2_x" 1 \
      "the newer video model (LTX-2.5), with its own text encoder. More accurate lip-sync and sharper faces than LTX-2.3. Optional: choose it per project with --backend ltx25." \
      "--exclude=transformer-dev.safetensors --exclude=*lora*"
    model "Lightricks/LTX-2.5-22b-IC-LoRA-Pixel-Spatial-Upscaler" "0.3 GB" "LTX-2 Community License" "https://github.com/Lightricks/LTX-2/blob/main/LICENSE-2_x" 1 \
      "the detail add-on for LTX-2.5. It lets the second pass run at full resolution so faces stay sharp. Only useful with LTX-2.5." \
      "" 1
    note "demucs (vocal isolation) downloads its own small model (about 0.3 GB) the first time a lip-sync shot needs it. It pulls the voice out of the mix so lip-sync follows the singer, not the drums."
  fi
fi

if [ "$STUDIO" = 1 ]; then
  step "7. Storyboard Studio (local web app)"
  if [ -d "$REPO/studio/node_modules" ]; then ok "Studio packages installed"; else run npm ci --prefix "$REPO/studio" --no-audit --no-fund --silent && [ "$CHECK" = 0 ] && ok "Studio packages installed"; fi
  if [ "$CHECK" = 1 ]; then note "would build the Studio (npm run build)"; else
    (cd "$REPO/studio" && npm run build >/dev/null 2>&1) && ok "Studio built" || miss "Studio build failed: cd studio && npm run build"
  fi
  note "HyperFrames (animation packs) is fetched by npx the first time you finish a video"
fi

if [ "$PLUGIN" = 1 ]; then
  step "8. Claude Code plugin"
  if ! command -v claude >/dev/null 2>&1; then
    miss "Claude Code not found. Install it (https://docs.claude.com/en/docs/claude-code), then run ./install.sh again"
  elif claude plugin list 2>/dev/null | grep -q "motionboard"; then
    ok "plugin already installed (update: claude plugin marketplace update motionboard)"
  else
    run claude plugin marketplace add "$REPO" && run claude plugin install motionboard@motionboard && [ "$CHECK" = 0 ] && ok "plugin installed; restart Claude Code to load its skills"
  fi
fi

step "9. Check"
if [ "$CHECK" = 1 ]; then
  note "would run: mb setup"
else
  env MB_HOME="$MB_HOME" "$ENGINE/.venv/bin/mb" setup --quick | sed -n '1,12p'
fi
echo
echo "Done. In Claude Code, say: make a music video for <song>. Or open the Studio: mb studio start"
