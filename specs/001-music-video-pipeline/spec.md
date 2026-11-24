# Feature Specification: Music Video Pipeline (Motionboard v1)

**Feature Branch**: `001-music-video-pipeline`

**Created**: 2026-11-24

**Status**: Draft

**Input**: User description: "Open source plugin that turns a song plus a storyboard into a finished music video on a creator's own Mac, using the workflow proven on the NAVAAN Almost Yours reel: storyboard first, image plates, local LTX-2.3 image to video per shot, optional lip-sync, then a finishing pass with lyrics, grade and end card. Four commands. Configurable memory guard. No bundled weights."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Storyboard from a song (Priority: P1)

A creator gives Motionboard a song file, its lyrics and a one paragraph idea. Motionboard measures tempo, beats and sung line timings, proposes a shot list (one shot per line or beat group), and writes a storyboard: for each shot the time range, the lyric, the visual, the single action, the camera move, whether a character appears, and the image prompt. The creator reviews it as a contact sheet and edits any shot.

**Why this priority**: The storyboard decides the whole video. Without it nothing else can run, and it is useful on its own (it can be handed to any tool or editor).

**Independent Test**: Run the storyboard command on a 60 second song. It produces a storyboard file and a contact sheet whose shot boundaries land within 0.1 s of measured beats or line starts.

**Acceptance Scenarios**:

1. **Given** a song, lyrics and an idea, **When** the creator runs the storyboard command, **Then** a storyboard with timed shots and a contact sheet is created in the project folder.
2. **Given** an existing storyboard, **When** the creator changes one shot, **Then** only that shot is marked for new plates and clips.
3. **Given** a target of 9:16 or 16:9, **When** the storyboard is made, **Then** framing notes and safe areas follow that aspect.

---

### User Story 2 - Plates and clips on the local machine (Priority: P1)

From an approved storyboard, Motionboard makes one image plate per shot (via a configured image backend), shows them for approval, then renders each shot to video with the local model, one shot at a time, under the memory guard. Finished shots are skipped on rerun.

**Why this priority**: This is the core value: free, local, consistent shots.

**Independent Test**: With an approved 5 shot storyboard, the command renders 5 clips of the right length and size without the machine running out of memory, and a rerun does no new work.

**Acceptance Scenarios**:

1. **Given** an approved storyboard, **When** plates are generated, **Then** the creator sees a plate contact sheet and the expected image cost before any paid call.
2. **Given** approved plates, **When** clips render, **Then** each clip matches its shot length (frames rounded to the model's frame rule) and resolution.
3. **Given** memory falls below the configured floor during a render, **When** the guard trips, **Then** the job stops cleanly, the reason is reported, and the remaining shots can resume later.
4. **Given** a shot marked as lip-sync, **When** it renders, **Then** the matching vocal segment drives the mouth movement.

---

### User Story 3 - Finish and deliver (Priority: P2)

Motionboard trims and joins the clips on the song's cut points, upscales to the delivery size, adds a lyric overlay styled from the storyboard's theme, a grade, grain and an end card (artist, song, album, release note), and lays the original audio under it. It also makes a cover image and a metadata file, and can copy the delivery to a chosen folder.

**Why this priority**: Turns clips into something postable. Valuable, but creators could finish in their own editor.

**Independent Test**: From a folder of clips plus storyboard, produce one MP4 whose duration, frame count, size and audio match the song segment, plus a cover and metadata file.

**Acceptance Scenarios**:

1. **Given** rendered clips, **When** finish runs, **Then** cuts land on the storyboard times within one frame.
2. **Given** an end card config, **When** finish runs, **Then** no follow or subscribe ask appears unless the creator adds one.
3. **Given** a delivery folder, **When** deliver runs, **Then** video, cover and metadata are copied there with the post time noted.

---

### User Story 4 - Setup check and fit check (Priority: P2)

A new creator runs the setup check. Motionboard reports the machine (chip, memory, free disk), which tools are present (Python env, ffmpeg, the model runtime, the finishing renderer), which model weights are downloaded, and gives the exact download steps and license links for what is missing. Before any render it runs a fit check for the chosen model, size and frame count against the configured memory limits.

**Why this priority**: Prevents crashes and confusing failures, which cost a restart on the reference machine.

**Independent Test**: On a machine without weights, the check lists the missing model with its license link and size, and makes no download on its own.

**Acceptance Scenarios**:

1. **Given** a missing model, **When** setup check runs, **Then** it shows size, license and download steps and waits for the creator.
2. **Given** a render request that would not fit, **When** the fit check runs, **Then** it refuses and suggests a smaller size, fewer frames or a lighter preset.
3. **Given** the creator edits the guard limits, **When** a render starts, **Then** the new limits are used and printed.

---

### User Story 5 - Realistic characters and lip-sync performance (Priority: P3)

The creator can choose a realistic look instead of a stylized one, keep the same character across shots from a reference image, and mark performance shots where the character sings the line. Motionboard isolates the vocal for those segments and flags the video as containing realistic synthetic people.

**Why this priority**: Proven in a test, wanted, but builds on stories 1 to 3.

**Independent Test**: A 3 shot storyboard with one sung line produces a clip whose mouth movement follows that line, and the metadata says altered or synthetic content: Yes.

**Acceptance Scenarios**:

1. **Given** a character reference, **When** plates are made, **Then** each character shot uses it.
2. **Given** a realistic character, **When** metadata is written, **Then** the synthetic content flag is set.

---

### Edge Cases

- Song longer than the target length: the storyboard step picks a segment (prefer first chorus) and says which.
- Shot shorter than the model's minimum frames: merge with a neighbour or hold a still, and say so.
- Model weights partly downloaded: setup check detects it and gives resume steps.
- Guard trips on the same shot twice: stop, suggest a lower size or frame count for that shot, do not loop.
- Plate contains unwanted figures in an object only shot: the storyboard marks no figure shots, and prompts exclude people for them.
- Lyrics missing or timing wrong: fall back to beat grid, and report that sync was not checked against vocals.
- Image backend not configured: allow creator supplied plates.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide four commands: setup check, storyboard, plates and clips, finish and deliver.
- **FR-002**: System MUST measure tempo, beats and loudness of the chosen song segment and use them for shot timing.
- **FR-003**: System MUST write the storyboard as an editable plain file plus a visual contact sheet.
- **FR-004**: System MUST NOT render clips until the creator approves the storyboard and the plates.
- **FR-005**: System MUST render clips locally with LTX-2.3 as the default backend, behind a backend interface that allows more models later.
- **FR-006**: System MUST run every heavy job under a memory and swap guard with configurable thresholds, safe presets and a dry run fit check.
- **FR-007**: System MUST skip shots that already have a valid clip unless the creator asks to redo them.
- **FR-008**: System MUST support 9:16 and 16:9 output.
- **FR-009**: System MUST support lip-sync shots driven by an audio segment.
- **FR-010**: System MUST NOT include model weights; it MUST show license and download steps instead.
- **FR-011**: System MUST state the expected cost and ask before any paid call (for example image generation).
- **FR-012**: System MUST produce the final video with original audio, a cover image and a metadata file.
- **FR-013**: System MUST never print or store API keys or tokens in logs or project files.
- **FR-014**: System MUST report at the end of each stage what was verified and what was not.
- **FR-015**: System MUST support a stylized look and a realistic look, and set a synthetic content flag for realistic people.
- **FR-016**: Plate generation MUST be loosely coupled: any image source the creator has access to (a local model, an MCP tool, or an HTTP API) plugs in through a small adapter, and creator supplied plates are always accepted. No single image provider is required.
- **FR-017**: v1 MUST ship one finishing style (dust lyrics, continuous thread, end card, as in Almost Yours) whose colors, fonts and texts are themeable per project. More styles are out of scope for v1.

### Key Entities

- **Project**: one video; song, lyrics, idea, aspect, look, settings, folder.
- **Storyboard**: ordered shots with timing, lyric, visual, action, camera, character flag, prompts, status.
- **Shot**: one entry with its plate, clip, lip-sync flag and render settings.
- **Backend**: a video or image generator with its requirements (memory, frame rule, sizes, license).
- **Guard profile**: memory floor, swap ceiling, poll interval, preset name.
- **Delivery**: final video, cover, metadata, target folder and post time.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A creator with the weights downloaded goes from song to approved storyboard in under 15 minutes of their own time.
- **SC-002**: A 60 second, 23 shot vertical video renders on a 36 GB Apple Silicon Mac with zero out of memory crashes.
- **SC-003**: Re-running any stage after an interruption redoes no finished shot.
- **SC-004**: Cut points in the final video land within one frame of the storyboard times.
- **SC-005**: The NAVAAN After Dark video is produced end to end with Motionboard as the first real test, with no manual script edits.
- **SC-006**: Total spend for a 60 second video is under 1 US dollar using default settings (image plates only).

## Assumptions

- v1 targets Apple Silicon Macs with at least 32 GB memory; smaller machines get lower presets.
- The creator owns or has rights to the song and lyrics.
- Claude Code (or a compatible agent) runs the commands; the plugin is skills plus bundled scripts.
- Python, ffmpeg and Node are available or installable by the setup check's instructions.
- Wan 2.2 and LTX-2.5 are out of scope for v1 (backlog; they do not fit 36 GB today).
- Posting to platforms is out of scope; delivery ends at a folder plus metadata.
