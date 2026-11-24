# Quickstart run (T075)

Date: 2026-11-24, about 01:00 to 01:30 CT. Machine: reference Mac, M3 Max, 36 GB, macOS. Throwaway `MB_HOME` and
`MB_PROJECTS` folders, so the creator's own database was not touched.

| Step | Result | Notes |
|---|---|---|
| 1. Setup check | pass | `mb setup`: ok, `ready_for_clips: true` (LTX-2.3 q8 and Gemma present; whisper and demucs not installed) |
| 2. Stub smoke run | pass | `scripts/smoke.sh mood-loop cosmic`: all 12 steps ok, final MP4 11.5 s (10 s segment plus 1.5 s tail) |
| 3. Real run (LTX-2.3) | pass after a fix | Studio Session, 4 shots of 65 frames at 576x1024, guard balanced. 3 image to video clips: 2.9 to 4.0 s per frame. The lip-sync shot failed first, see below; after the fix it rendered in 209 s (3.2 s per frame). Finish with the Studio Session pack over the real clips: 27 s, 1080x1920, 275 frames |
| 4. Resume | pass | After rejecting shot 2's clip, `mb clips` queued only shot 2; shots 1, 3 and 4 were skipped as finished |
| 5. Guard | pass | `mb guard --create tight --start 95 --kill 40 --swap 1`; a 1080x1920 241 frame shot is refused by the fit check (51 GB estimate vs 12.6 GB headroom) with the suggestions. Kill floor above 50 is refused by design |
| 6. Paid adapter | pass | `COST_NOT_CONFIRMED`, estimate $0.01, no request sent |

## Fixed during the run

- **Lip-sync audio too short.** Frames are rounded up to the LTX 8k+1 rule (65 frames for a 2.5 s shot), but the
  vocal slice covered only the shot. The a2v encoder needs audio for every frame plus a little more. The slice now
  covers `frames / fps + 0.3 s` and pads with silence past the segment end (`audio/vocals.py`, test added).
- **Fit check for a2v.** A backend profile without a2v points now borrows its i2v points plus 25% and says so in
  the basis, instead of refusing every lip-sync shot.

## Measured (fit_sample)

| Mode | Frames | Peak used (GB) | Seconds per frame |
|---|---|---|---|
| i2v | 65 | 4.6 to 7.6 | 2.9 to 4.0 |
| a2v | 65 | 7.5 | 3.2 |

Peak used is the guard's system wide reading, lower than the shipped profile's Metal peak (about 16 GB), so the fit
check stays conservative.

## Not verified

- Lip-sync quality: demucs is not installed, so the a2v shot used the full mix, not an isolated vocal.
- Lyric timing on screen against the vocal, by ear.
- Full length (60 s) real run; this run used the 10 s fixture song.
