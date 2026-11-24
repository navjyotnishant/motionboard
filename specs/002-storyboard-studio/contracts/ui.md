# Contract: UI layout and behaviour

## Screens
1. **Bin** (`/`): grid of project tiles (hero frame, title, aspect, stage). New project button.
2. **Start** (`/new`): song file, lyrics, idea; two large choices: Brainstorm or Template. Brainstorm shows three concept cards side by side; Template shows five tiles with a sample frame strip.
3. **Board** (`/p/:id`):
   - Top bar: project title, gate bar (Storyboard, Plates, Clips, Final with state), settings icon.
   - Centre: card grid in shot order; card = plate or clip (aspect correct), thin bar with shot number, timecode, state dot. Hover on a clip card scrubs the proxy. Click selects; double click opens the side panel.
   - Right side panel: all shot fields, characters, versions strip (plates and clips), notes, Approve and Reject.
   - Bottom: film strip plus waveform with beats and line markers; shot regions draggable with snapping; playhead follows playback.
   - Bottom drawer (Q): render queue with progress, time left, memory meter against guard floor and swap ceiling, pause, resume, stop, drag to reorder.
   - Animatic button: full screen player over the song.
4. **Settings** (`/settings`): guard presets, plate adapters (with test button), paths, accent colour.

## Visual rules
Dark by default (light optional). Frames are the content; controls recede. One accent colour. 1 px lines, no shadows, 8 px spacing grid, Inter, tabular timecodes. Never more than three primary buttons visible at once.

## Feedback
Every `mb` action shows a toast with the result and expandable `verified` and `not_verified` lists. Cost confirm is a modal stating the amount and adapter.
