#!/usr/bin/env bash
# End to end smoke run with the stub video backend (no GPU, no weights; HyperFrames comes from the npx cache).
# Usage: scripts/smoke.sh [mode] [look]     Prints the project folder on the last line.
set -euo pipefail
cd "$(dirname "$0")/.."
MODE=${1:-two-lovers}
LOOK=${2:-origami}
export MB_HOME=${MB_HOME:-$(mktemp -d)} MB_PROJECTS=${MB_PROJECTS:-$(mktemp -d)} MB_BACKEND=stub
mb() { uv run mb "$@" --json; }
ok() { python3 -c "import json,sys;d=json.load(sys.stdin);print(('ok   ' if d['ok'] else 'FAIL ')+d['command'], '' if d['ok'] else d['error'], file=sys.stderr);sys.exit(0 if d['ok'] else 1)"; }
OUT=$(mb project new --title "Smoke $MODE" --song tests/fixtures/song10s.wav --lyrics-file tests/fixtures/lyrics.txt)
P=$(echo "$OUT" | python3 -c "import json,sys;print(json.load(sys.stdin)['project'])")
F=$(echo "$OUT" | python3 -c "import json,sys;print(json.load(sys.stdin)['data']['folder'])")
mb analyze -p "$P" | ok
DRAFT=$(mb draft -p "$P" --mode "$MODE" --look "$LOOK")
echo "$DRAFT" | ok
N=$(echo "$DRAFT" | python3 -c "import json,sys;print(json.load(sys.stdin)['data']['shots'])")
mb approve -p "$P" --stage storyboard | ok
mkdir -p "$F/plates/inbox"
for i in $(seq 1 "$N"); do cp "tests/fixtures/plates/shot-0$(( (i - 1) % 4 + 1 )).png" "$F/plates/inbox/shot-$(printf %02d "$i").png"; done
mb plates -p "$P" | ok
mb review -p "$P" --shot 0 --decision approve --all | ok
mb approve -p "$P" --stage plates | ok
mb clips -p "$P" | ok
mb worker | ok
mb review -p "$P" --shot 0 --kind clip --decision approve --all | ok
mb approve -p "$P" --stage clips | ok
mb theme -p "$P" --set artist=NAVAAN --set "song=Paper Boats" --set "album_line=FROM THE ALBUM  AFTER DARK" \
  --set "release_note=COMING SOON" --set highlight_words=almost,thread | ok
mb finish -p "$P" | ok
echo "$F"
