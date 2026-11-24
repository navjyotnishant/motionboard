# Feature Specification: Storyboard Studio (local web app)

**Feature Branch**: `002-storyboard-studio`

**Created**: 2026-11-24

**Status**: Draft

**Input**: User description: "A web interface for the storyboard, inspired by the Boords board we used for Almost Yours, and improved. Minimalistic design. Runs locally as part of the plugin (Next.js is fine, but local, not a hosted website), backed by a local lightweight database. Give the user a brainstorm or a template to start from."

## Context

On Almost Yours the storyboard lived in Boords: one card per shot, an image on each card, the lyric and action under it, reviewed before any video started. What was missing: cards did not know the song's timing, there was no link from a card to its prompt, plate, clip and render status, and moving between ChatGPT, Boords, the terminal and the Mac folder was manual. Storyboard Studio puts the whole board in one local web app that the Motionboard commands and the creator both read and write.

## Scope

- Runs only on the creator's machine, started by a plugin command, served on localhost. Not a hosted website, no accounts, no cloud backend.
- Single creator. Multi user and hosting are out of scope.
- Minimal design throughout.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Board view tied to the song (Priority: P1)

The creator runs a plugin command and the Studio opens in the browser. It shows the project as shot cards in order, above a waveform of the song with sung lines and beats marked. Each card shows the plate thumbnail (or a blank frame), shot number, time range, lyric, visual, action, camera move, character flag and status. Clicking a card opens a side panel to edit any field. Dragging a shot boundary on the timeline changes its timing and snaps to beats.

**Why this priority**: The Boords experience the creator liked, made aware of the music. Everything else hangs on it.

**Independent Test**: Load a 23 shot storyboard. All cards show, play from any card plays the song from that shot's start, and a timing edit persists after a reload.

**Acceptance Scenarios**:

1. **Given** a project with a storyboard, **When** the Studio opens, **Then** cards appear in order with their timing on the waveform.
2. **Given** a card, **When** the creator edits its action and saves, **Then** the change persists and the card is marked as needing a new clip.
3. **Given** the timeline, **When** a boundary is dragged, **Then** it snaps to the nearest beat or line start and the neighbouring shot adjusts.
4. **Given** a 9:16 or 16:9 project, **When** the board renders, **Then** cards use that aspect and show the safe area.

---

### User Story 2 - Start from a brainstorm or a template (Priority: P1)

A new creator never starts from a blank page. Two starts:
- **Brainstorm**: point to the song, paste lyrics, answer a few prompts (mood, world, characters, look, aspect). Claude proposes three distinct concepts, each with a title, a one line premise, a hero image idea and three sample shots. The creator picks one, or mixes, and the full board is drafted.
- **Template**: pick a starter structure, for example Object World (a world built from one material, like the origami museum), Performance (singer and lip-sync with cutaways), Lyric Story (one scene per line), Two Lovers (a couple across scenes), Mood Loop (slow ambient shots). The template sets shot rhythm, camera language, style lines and finishing theme, and shots follow the song's lines and beats.

**Why this priority**: The blank page is where creators stall. Brainstorm and templates get a first board in minutes.

**Independent Test**: From only a song and lyrics, either path gives a full drafted board without typing a shot list.

**Acceptance Scenarios**:

1. **Given** a song and lyrics, **When** Brainstorm runs, **Then** three concepts appear side by side and choosing one drafts a full board.
2. **Given** a template, **When** applied, **Then** shot count and rhythm follow the song, not a fixed count.
3. **Given** a finished project, **When** saved as a template, **Then** it appears in the template list with song specific parts removed.

---

### User Story 3 - Review and approve, card by card (Priority: P1)

Each card moves through clear states: draft, plate ready, plate approved, clip rendering, clip ready, clip approved, needs redo. The creator approves or rejects plates and clips on the card, leaves a note, and asks for a redo with an edited prompt. Pipeline gates (storyboard, plates, clips) are buttons in the Studio as well as chat steps.

**Why this priority**: The constitution requires review gates. Doing them on the board replaces chat screenshots.

**Independent Test**: Reject a plate with a note, regenerate, approve. History shows both versions and the note.

**Acceptance Scenarios**:

1. **Given** a plate, **When** rejected with a note, **Then** the card moves to needs redo and keeps the note with that version.
2. **Given** several versions, **When** an older one is picked, **Then** it becomes active.
3. **Given** all cards approved, **When** the stage is approved, **Then** the next pipeline stage may start.

---

### User Story 4 - Watch renders live, safely (Priority: P2)

While clips render, the Studio shows the queue: current shot, progress, time per frame, time left, and live memory and swap against the guard limits. The creator can pause after the current shot, reorder, or stop. Finished clips play inline on their card. Guard limits are editable on a settings page with presets.

**Why this priority**: Long local renders are the riskiest part; seeing memory against the limits builds trust.

**Independent Test**: Start a 3 shot render, pause after shot 1, resume. Queue and memory readout stay accurate and no shot renders twice.

**Acceptance Scenarios**:

1. **Given** a render running, **When** memory nears the floor, **Then** the readout warns before the guard stops the job.
2. **Given** a guard stop, **When** the card is opened, **Then** it shows the reason and a suggested smaller setting.

---

### User Story 5 - Animatic and export (Priority: P2)

The creator plays the board as an animatic: plates, or clips where ready, in sequence over the song with lyrics, to judge pacing before rendering. The board exports as a PDF contact sheet, JSON, and a self contained read only HTML file saved to disk.

**Why this priority**: Cheap pacing check; lets the board leave the Studio as files.

**Independent Test**: Play an animatic with only plates; cuts match card times. Export JSON and import into a fresh project with no loss.

**Acceptance Scenarios**:

1. **Given** a mix of clips and plates, **When** the animatic plays, **Then** clips show where present, plates elsewhere.
2. **Given** an exported JSON, **When** imported, **Then** the board is identical.

---

### Edge Cases

- Studio closed while a render runs: the render continues; on reopen the board shows true state from the database.
- File edited on disk outside the Studio (prompt, plate): the Studio notices and shows the change.
- Two tabs editing one card: last save wins; the other tab is told to reload.
- Song replaced after the board exists: cards stay, mismatched timings are flagged.
- Long song (4 to 5 minutes, 80 plus shots): board stays responsive; thumbnails load lazily.
- No Claude available: editing, review, animatic and export work; Brainstorm says it needs Claude.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Studio MUST ship inside the plugin and run only on localhost, started and stopped by a plugin command. No account, no cloud backend, no internet needed for core use.
- **FR-002**: Studio MUST store state in a local lightweight embedded database (single file); images, audio and video stay on disk, referenced by path.
- **FR-003**: Studio MUST show ordered cards over a song waveform with beats and sung lines.
- **FR-004**: Creators MUST be able to edit every shot field and timing; chat commands and the Studio MUST read and write the same database.
- **FR-005**: Studio MUST offer Brainstorm returning at least three distinct concepts.
- **FR-006**: Studio MUST ship at least five starter templates and allow saving a project as a template.
- **FR-007**: Studio MUST track per shot states and keep every version of plates, clips and prompts with notes.
- **FR-008**: Studio MUST present approval gates for storyboard, plates and clips, matching the pipeline.
- **FR-009**: Studio MUST show the render queue with progress, time left, and live memory and swap against guard limits, with pause, resume, reorder and stop.
- **FR-010**: Studio MUST play an animatic of the board over the song.
- **FR-011**: Studio MUST export JSON, PDF contact sheet and self contained HTML to disk, and import JSON.
- **FR-012**: Studio MUST show the expected cost before any paid plate generation and require a click to confirm.
- **FR-013**: Studio MUST NOT show or store API keys in the browser or database.
- **FR-014**: Studio MUST accept any image source through the plate adapter (local model, MCP tool, API, or uploaded file).
- **FR-015**: Design MUST look like a media tool, minimal and imagery first: dark theme by default (light optional) so frames and clips read true, large plate and clip thumbnails as the main content, chrome that recedes (thin borders, quiet controls), one accent color, a film strip and waveform style timeline, hover to scrub clips, inline video playback, keyboard shortcuts for play, next and previous shot, approve and reject. Detail lives in side panels, not extra pages. Reference feel: Frame.io, Boords, a video editor's bin and timeline.

### Key Entities

- **Workspace**: the local install; settings, guard profiles, plate adapters, templates.
- **Project**: song, lyrics, idea, aspect, look, theme, status, stage approvals.
- **Concept**: a brainstorm option; title, premise, hero image idea, sample shots, chosen flag.
- **Template**: shot rhythm rules, camera language, style lines, finishing theme.
- **Shot**: order, time range, lyric, visual, action, camera, character flag, lip-sync flag, prompts, state.
- **Asset version**: a plate, clip or prompt version for a shot; path, source, cost, created time, note, active flag.
- **Character**: name, reference image, style line; linked to shots.
- **Render job**: shot, backend, settings, state, progress, memory readings, stop reason.
- **Review note**: when, which version, text, decision.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Song to drafted board in under 10 minutes using Brainstorm or a template.
- **SC-002**: A 23 shot board opens in under 2 seconds, an 80 shot board in under 5 seconds, on the reference Mac.
- **SC-003**: A change made in chat appears in an open Studio within 3 seconds, and the reverse.
- **SC-004**: The NAVAAN After Dark storyboard is made and approved in the Studio with no external board.
- **SC-005**: JSON export then import gives an identical board.

## Assumptions

- Single creator on one machine.
- A local web framework (Next.js is acceptable) serves the Studio on localhost; the plugin installs and starts it.
- Brainstorm and drafting use Claude through the plugin.
- Templates are plain files in the plugin.
