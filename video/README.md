# Motionboard overview video

Remotion source of the 64 second product overview in `docs/media/`.

- `src/` scenes, cover (`Cover` still) and shared kit; every scene length is a whole number of beats at 120 BPM.
- `scripts/bed.py` writes the music bed (synthesised locally, no samples).
- `public/` holds clips and plates cut from a Motionboard project. It is not tracked; fill it from your own project to render.

```bash
npm install
python3 scripts/bed.py
npm run render
ffmpeg -i out/overview-silent.mp4 -i out/bed.wav -map 0:v -map 1:a -c:v copy -c:a aac -shortest out/motionboard-overview.mp4
npx remotion still src/index.ts Cover out/cover-1920x1080.png
```
