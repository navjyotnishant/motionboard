---
name: mb-storyboard
description: Build a music video storyboard timed to a song with Motionboard. Use when the creator says "storyboard this song", "start a music video", "make a reel for my song", "brainstorm a video idea", or wants to pick a mode (Studio Session, Travel, Two Lovers, Lyric Story, Mood Loop) and a look (Origami, Exotic, Vintage Film, Neon Night, Cosmic). Ends with a contact sheet and stops for approval; no images or video are made here.
---

# Motionboard: Storyboard

**Where `mb` runs.** On the creator's Mac, never in a cloud workspace.
- Claude Code: the terminal.
- Claude app (desktop or mobile, with the Mac linked): the Mac's shell tool (device bash or Desktop Commander). If `mb` is not on that shell's PATH, use `~/.local/bin/mb`. If no Mac tool is available, say the Mac must be linked through the Claude desktop app, and stop.
- Long jobs (clips, finish) run detached (`mb worker --detach`); check them with `mb queue --json` instead of waiting on one call.
- Images and videos it makes live on the Mac; stage or open them to show the creator.

Storyboard first is the rule: nothing renders until the creator approves this board.

All engine calls run from the plugin's `engine/` folder as `mb <command> --json`. Every call prints one JSON report. Relay its `verified` and `not_verified` lists honestly; never claim something the report lists as not verified.

## 1. Gather (ask only what is missing, in one message)

- Song file path (wav, mp3, m4a) and the lyrics (pasted or a file).
- One line idea, if they have one.
- Aspect: 9:16 reel or 16:9 full video.
- Look: stylized or realistic people. Realistic people means the video must be labelled as altered or synthetic content on YouTube and Instagram; say so.

Write pasted lyrics to `<project folder>/lyrics.txt` only after the project exists; until then keep them in a temp file.

## 2. Create and analyse

```bash
mb project new --title "<title>" --song <path> --lyrics-file <file> --idea "<idea>" --aspect 9:16 --look stylized --json
mb analyze --project <id> --json            # auto segment (65 s, loudest sustained window)
mb analyze --project <id> --start 134 --end 199 --json   # or a segment the creator names
```

Tell the creator the segment picked, the tempo, the number of sung lines, and whether lines were matched to the voice or only spread on the beat grid.

## 3. Choose a start: brainstorm or mode

Run `mb modes --json` and show modes and looks briefly (name and one line each). Offer two paths:

**Brainstorm.** Write exactly three distinct concepts from the lyrics, idea and analysis. Each concept: `title`, `premise` (one line), `hero_image_idea`, `sample_shots` (three short shots), plus the mode and look it uses. Save them as JSON, then:

```bash
mb concepts add --project <id> --file concepts.json --json
```

Show the three side by side. When the creator picks one (or mixes), `mb concepts choose`, then write one shot idea per sung line (see step 4).

**Mode plus look.** The creator picks one mode and one look. The mode carries the signature animation used in finishing; say which.

## 4. Draft

Without shot ideas the engine fills shots from the mode's pattern:

```bash
mb draft --project <id> --mode two-lovers --look origami --json
```

With a chosen concept, write `shots.json` first: one entry per timed shot, each with `visual`, `action`, `camera`, `has_figure`, and `lip_sync` only for singing shots. Rules for every shot:

- Exactly one clear action, written as a gesture or movement the model can see ("she lifts her hand to the glass"), never a feeling.
- Object or scenery shots set `has_figure: false`; the engine then adds the look's no figure line so stray people do not appear.
- Characters are named in capitals (HER, HIM, SINGER) consistently.
- No on screen text, place names or exhibit labels in the visual.

```bash
mb draft --project <id> --mode two-lovers --look origami --shots-file shots.json --replace --json
```

## 4b. Characters

The draft creates the mode's cast (HER and HIM, SINGER) and links each to the shots whose visual names them in capitals.

- `mb character list -p <id> --json` shows each character and its shots.
- Ask the creator how each one looks. Save it with `mb character set -p <id> --name HER --field style_line --value "..."`. Only linked shots get the line in their plate prompt.
- A reference image keeps a face consistent: `mb character add|set ... --ref <image>` or `--field reference_image`. Plate adapters receive it with each request.
- `mb character link|unlink -p <id> --name HER --shots 2,5` changes who is in a shot. A shot needs a figure first.
- Changing a style line or reference marks finished plates for redo. Say which shots changed.
- Realistic looks with people set the synthetic flag; delivery metadata says so. Never clear it.

## 5. Review

```bash
mb sheet --project <id> --kind storyboard --json
```

Show the contact sheet image. List shots as `NN  0:04.2–0:07.9  lyric  |  action`. Take edits:

```bash
mb shot set --project <id> --shot 3 --field action --value "<new action>" --json
mb shot move --project <id> --shot 3 --end 7.9 --json     # cut snaps to a beat within 0.12 s
```

Fields: lyric, visual, action, camera, plate_prompt, motion_prompt, has_figure, lip_sync. Prompts follow the look automatically when visual, action or camera change.

## 6. Stop for approval

Ask the creator to approve the storyboard. Only on a clear yes:

```bash
mb approve --project <id> --stage storyboard --json
```

Then point to the next stage: plates and clips (`mb-clips`). Also mention the Storyboard Studio can show the same board (`mb-studio`).

## Never

- Never generate plates or clips in this skill.
- Never spend money here.
- Never approve on the creator's behalf.
