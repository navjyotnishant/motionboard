#!/usr/bin/env bash
# Preview one animation pack: stub smoke run, then a contact sheet of the final video, the overlay layer
# and the cover, plus a 10 s preview MP4. Usage: scripts/pack_preview.sh <mode> <look> <outdir>
set -euo pipefail
cd "$(dirname "$0")/.."
MODE=$1 LOOK=$2 OUT=$3
mkdir -p "$OUT"
F=$(bash scripts/smoke.sh "$MODE" "$LOOK" 2>"$OUT/$MODE-smoke.log" | tail -1)
V=$(ls "$F"/out/*_1080x1920.mp4 | head -1)
O="$F/out/finish/overlay.mp4"
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$V")
SEL=""
for frac in 0.08 0.25 0.45 0.65 0.82 0.95; do
  n=$(python3 -c "print(int($DUR*24*$frac))")
  SEL="${SEL:+$SEL+}eq(n\\,$n)"
done
ffmpeg -v error -y -i "$V" -vf "select='$SEL',scale=240:-1,tile=6x1" -frames:v 1 "$OUT/$MODE-final.png"
ffmpeg -v error -y -i "$O" -vf "select='$SEL',scale=240:-1,tile=6x1" -frames:v 1 "$OUT/$MODE-overlay.png"
cp "$F"/out/*_cover_*.jpg "$OUT/$MODE-cover.jpg"
ffmpeg -v error -y -i "$V" -t 10 -c copy "$OUT/$MODE-preview.mp4"
FR=$(ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of csv=p=0 "$V")
echo "$MODE duration=$DUR frames=$FR folder=$F"
