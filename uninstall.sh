#!/usr/bin/env bash
# Remove what install.sh added. Your projects, database and downloaded model weights stay unless you ask.
#   ./uninstall.sh                 remove the mb command, the plugin, the Studio build and engine/.venv
#   ./uninstall.sh --all-data      also delete ~/.motionboard (database, settings, ltx-2-mlx it installed)
set -uo pipefail
REPO="$(cd "$(dirname "$0")" && pwd)"
MB_HOME="${MB_HOME:-$HOME/.motionboard}"
BIN_DIR="${MB_BIN_DIR:-$HOME/.local/bin}"

if command -v uv >/dev/null 2>&1 && [ -f "$MB_HOME/studio.pid" ]; then
  uv run --quiet --project "$REPO/engine" mb studio stop --json >/dev/null 2>&1 || true
fi
if command -v claude >/dev/null 2>&1; then
  claude plugin uninstall motionboard@motionboard >/dev/null 2>&1 && echo "removed the Claude Code plugin"
  claude plugin marketplace remove motionboard >/dev/null 2>&1 || true
fi
if [ -f "$BIN_DIR/mb" ] && grep -q "Motionboard engine launcher" "$BIN_DIR/mb"; then rm "$BIN_DIR/mb" && echo "removed $BIN_DIR/mb"; fi
rm -rf "$REPO/studio/.next" "$REPO/studio/node_modules" "$REPO/engine/.venv" && echo "removed the Studio build and engine environment"

if [ "${1:-}" = "--all-data" ]; then
  read -r -p "Delete $MB_HOME (database, settings) for good? Projects in ~/Motionboard/projects stay. [y/N] " r
  [[ "$r" =~ ^[Yy] ]] && rm -rf "$MB_HOME" && echo "deleted $MB_HOME"
fi
echo "Model weights stay in ~/.cache/huggingface. Delete them there if you no longer need them."
