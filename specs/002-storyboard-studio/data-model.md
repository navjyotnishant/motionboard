# Data Model: Storyboard Studio

The Studio uses the shared schema in [001 data-model](../001-music-video-pipeline/data-model.md). It adds no tables.

## What the Studio writes directly (PATCH, plus a `change_event` row with actor `studio`)
- `shot`: lyric, visual, action, camera, has_figure, lip_sync, plate_prompt, motion_prompt, start and end (boundary drag updates two neighbours in one transaction), `dirty` and state per the state machine rules.
- `character`: name, style_line, reference_image.
- `project`: title, idea, theme, aspect only before clips exist.
- `review_note`: comments.

## What goes through `mb` (rules live in the engine)
draft, approve and revoke gates, approve or reject a version (moves states), make plates, queue clips, queue control, guard presets, adapters, export and import, finish, deliver, concepts add.

## Client view models
- **BoardShot**: shot fields + active plate URL + active clip proxy URL + state badge + version counts.
- **TimelineModel**: duration, peaks, beats, lines, shot regions.
- **QueueItem**: job + last memory sample + guard limits.
- **ConceptCard**: concept fields + chosen flag.

## Concurrency
Every PATCH sends the row's `updated_at`; a mismatch returns 409 and the tab shows "changed elsewhere, reload" (last save wins on confirm).
