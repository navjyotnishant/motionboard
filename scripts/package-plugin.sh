#!/usr/bin/env bash
# Build dist/motionboard.plugin for the Claude app: the plugin manifest and skills only (the engine stays on the Mac).
# Run it after changing skills/ or .claude-plugin/plugin.json, and commit dist/motionboard.plugin.
set -euo pipefail
cd "$(dirname "$0")/.."
claude plugin validate . >/dev/null 2>&1 || echo "note: claude plugin validate failed or is not installed; check manually"
STAGE=$(mktemp -d)
mkdir -p "$STAGE/.claude-plugin" dist
cp .claude-plugin/plugin.json "$STAGE/.claude-plugin/"
cp -R skills "$STAGE/"
cp packaging/app-plugin-README.md "$STAGE/README.md"
rm -f dist/motionboard.plugin
(cd "$STAGE" && zip -qr - . -x "*.DS_Store") > dist/motionboard.plugin
rm -rf "$STAGE"
V=$(python3 -c "import json;print(json.load(open('.claude-plugin/plugin.json'))['version'])")
echo "dist/motionboard.plugin (version $V, $(du -h dist/motionboard.plugin | cut -f1))"
