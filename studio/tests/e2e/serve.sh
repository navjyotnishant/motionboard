#!/usr/bin/env bash
# E2E server: a throwaway MB_HOME with one stub project drafted and plates in its inbox, then the built Studio
# on port 4399 with a fixed token. Playwright starts this and waits for the port.
set -euo pipefail
cd "$(dirname "$0")/../.."
STUDIO=$PWD
ENGINE=$STUDIO/../engine
E2E=${MB_E2E_DIR:-/tmp/mb-e2e}
rm -rf "$E2E"; mkdir -p "$E2E/home" "$E2E/projects"
export MB_HOME=$E2E/home MB_PROJECTS=$E2E/projects MB_BACKEND=stub
mb() { (cd "$ENGINE" && uv run mb "$@" --json); }
mb db migrate >/dev/null
OUT=$(mb project new --title "E2E Board" --song "$ENGINE/tests/fixtures/song10s.wav" --lyrics-file "$ENGINE/tests/fixtures/lyrics.txt")
P=$(echo "$OUT" | python3 -c "import json,sys;print(json.load(sys.stdin)['project'])")
F=$(echo "$OUT" | python3 -c "import json,sys;print(json.load(sys.stdin)['data']['folder'])")
mb analyze -p "$P" >/dev/null
mb draft -p "$P" --mode two-lovers --look origami >/dev/null
mkdir -p "$F/plates/inbox"
for i in 1 2 3 4; do cp "$ENGINE/tests/fixtures/plates/shot-0$i.png" "$F/plates/inbox/shot-0$i.png"; done
cp "$ENGINE/tests/fixtures/plates/shot-01.png" "$E2E/upload.png"
echo "$P" > "$E2E/project"; echo "$F" > "$E2E/folder"
[ -f .next/BUILD_ID ] || npm run build >/dev/null
export MB_STUDIO_TOKEN=e2e-token MB_CLAUDE_BIN=none PORT=4399 MB_REPO=$STUDIO/..
exec npx next start -H 127.0.0.1 -p 4399
