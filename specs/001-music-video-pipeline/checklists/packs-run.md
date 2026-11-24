# Animation packs run (T081)

Date: 2026-11-24. Machine: reference Mac (M3 Max). Tool: `engine/scripts/pack_preview.sh <mode> <look> <outdir>`.
Input: fixture song (`tests/fixtures/song10s.wav`), fixture lyrics, stub video backend, theme artist NAVAAN,
song Paper Boats, album line, release note COMING SOON.

| Pack | Look used | Result | Duration | Frames | Notes |
|------|-----------|--------|----------|--------|-------|
| two-lovers | origami | pass | 11.5 s | 275 | Checked in US3 (T060 to T067) |
| studio-session | neon-night | pass | 11.5 s | 275 | REC light, counter, typed lines, meters on beats, cassette card. Lip-sync shots routed to a2v (stub) |
| travel | origami | pass | 11.5 s | 275 | Route grows one stop per cut, stamps alternate red and blue, boarding pass card, no place names |
| lyric-story | vintage-film | pass | 11.5 s | 275 | One word per beat, handwriting reveal, title card. First render failed: render ran before init; fixed with lazy prepare |
| mood-loop | cosmic | pass | 11.5 s | 275 | Leaks and motes drift, breathing lyric fades, glow title card |

Every pack: lyrics come from `song_analysis.lines`, clear before the end card, end card shows theme texts,
no follow or subscribe ask.

Outputs per pack (on the Mac, not in git): `<mode>-final.png`, `<mode>-overlay.png`, `<mode>-cover.jpg`,
`<mode>-preview.mp4` in `~/Movies/NAVAAN-reels/almost-yours/_motionboard_checks/packs/`.

Not verified:
- Packs over real LTX clips; stub clips are flat colour, so contrast against busy footage is untested.
- Mood Loop lyrics wash out over very bright plates; the matte vignette helps but a darker grade may be needed.
- 16:9 layouts were not rendered in this run.
- Lyric timing was not checked by ear.
