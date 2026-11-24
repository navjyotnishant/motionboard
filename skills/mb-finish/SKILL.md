---
name: mb-finish
description: Finish and deliver a Motionboard music video after every clip is approved. Use when the creator says "finish the video", "add the lyrics and end card", "make the final cut", "make the cover", or "deliver it to Dropbox". Applies the mode's signature animation pack (lyrics, transitions, end card), grade and grain, makes the cover and metadata, and copies them to a folder.
---

# Motionboard: Finish and deliver

**Where `mb` runs.** On the creator's Mac, never in a cloud workspace.
- Claude Code: the terminal.
- Claude app (desktop or mobile, with the Mac linked): the Mac's shell tool (device bash or Desktop Commander). If `mb` is not on that shell's PATH, use `~/.local/bin/mb`. If no Mac tool is available, say the Mac must be linked through the Claude desktop app, and stop.
- Long jobs (clips, finish) run detached (`mb worker --detach`); check them with `mb queue --json` instead of waiting on one call.
- Images and videos it makes live on the Mac; stage or open them to show the creator.

Run engine commands as `mb <command> --json` (the `mb` command comes from `./install.sh`). Relay `verified` and `not_verified` honestly.

## 1. Theme

The mode's animation pack needs a few texts. Show what is set and what the pack accepts:

```bash
mb theme --project <id> --json
```

Ask only for what is missing, then set it:

```bash
mb theme --project <id> --set artist=NAVAAN --set "song=Almost Yours" \
  --set "album_line=FROM THE ALBUM  AFTER DARK" --set "release_note=COMING SOON" \
  --set highlight_words=almost,love --json
```

Rules for the end card: artist, song, album and a release note only. No follow or subscribe ask unless the creator adds one. No location or exhibit labels.

Two Lovers also takes `snap_at` (second where the ruby thread snaps) and `chorus` (start,end seconds).

## 2. Finish

```bash
mb finish --project <id> --json
```

This renders the pack's matte and overlay with HyperFrames (in the foreground, under the memory guard), assembles the cut with ffmpeg (shots trimmed to their exact frames, grade, matte, overlay, fine grain, original audio, 1.5 s tail), makes the cover from a clean clip frame with the pack's title block, and writes the metadata file. About half a minute for a short reel, a few minutes for a full song.

Show the creator a contact strip or the video itself. If the cover frame is wrong, re-run with `--cover-at <second>`.

The report says lyric timing on screen follows the analysed line times and was not checked by ear; say so.

## 3. Approve and deliver

Only after the creator approves the final video:

```bash
mb approve --project <id> --stage final --json
mb deliver --project <id> --to "<folder>" --post-time "2026-11-24T08:00-06:00" \
  --platforms "YouTube Shorts,Instagram Reels" --json
```

If any shot shows realistic people made with AI, the metadata says altered or synthetic content: Yes; remind the creator to set that label on each platform. Motionboard does not post.
