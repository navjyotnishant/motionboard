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

**Brainstorm.** Write exactly three distinct concepts from the lyrics, idea and analysis. The three must differ in what the song means and whose story it is, not only in look; none of them may be the lyric acted out line by line. Each concept: `title`, `premise` (one line), `hero_image_idea`, `sample_shots` (three short shots), plus the mode and look it uses. Save them as JSON, then:

```bash
mb concepts add --project <id> --file concepts.json --json
```

Show the three side by side. When the creator picks one (or mixes), `mb concepts choose`, then write the treatment (step 3b) and, from it, one shot idea per timed shot (step 4).

**Mode plus look.** The creator picks one mode and one look. The mode carries the signature animation used in finishing; say which.

## 3b. Direct it: write the treatment before any shot

This is the step that decides whether the video is worth watching. A lyric is already heard. A picture that repeats it adds nothing, and a video made of such pictures is a slideshow of the words. Work as a director, not as an illustrator.

Write `<project folder>/treatment.md` and show it to the creator before drafting shots. Keep it to one page:

1. **What the song is about, under the words.** One sentence the lyric never says out loud. ("He has agreed to be someone's secret, and tonight he stops agreeing.")
2. **The story on screen.** Who wants what, what stands in the way, what changes by the end. Three short beats: start, turn, end. The picture may tell a story the lyric only hints at.
3. **The point of view.** Whose eyes we are in, and what the audience knows that a character does not.
4. **Two or three motifs.** Objects, places or gestures that come back and change meaning (a second cup, a phone face down, a light left on). Say what each one means the first time and the last time.
5. **The visual arc.** How light, colour, distance and pace move across the song: verse against chorus, the bridge, the last chorus. Night in the lyric can be noon on screen if noon tells the truth better.
6. **Where the singer sings.** Which lines are performance and which are story. Performance needs a reason and a place.
7. **What we refuse to show.** The obvious pictures for this lyric, listed so they stay out.

Then, for every sung line, ask three questions in this order: what does the line mean, what does this character do when they feel that, where is the camera. Write the shot from the answers, never from the nouns in the line.

- "You leave your jacket by my door" is about someone who keeps one foot in. Show a toothbrush put back in a bag, or him setting out two cups and putting one away. Not a jacket on a door.
- "You only miss me in the dark" does not need a dark room. A bright crowded street where she does not look up from her phone says it harder.
- "Slow" in a lyric is not a slow push in. "Burn" is not a flame. "Rain" is not rain.

Use contrast and counterpoint (a warm picture under a cold line), the reaction and not the event, the moment before or after and not the moment itself, and a motif returning in place of a new idea. Give the chorus a different picture each time it comes back: the same words must mean more the third time.

Literal is allowed when it is a choice, about once or twice in a song, where the plain picture lands hardest. `mb draft`, `mb sheet` and `mb approve --stage storyboard` list shots that repeat their lyric word for word under `not_verified`. That check only catches shared words (it will not see "coat" for "jacket"), so read every shot against its line yourself. A board that passes it can still be flat.

## 4. Draft

Without shot ideas the engine fills shots from the mode's pattern:

```bash
mb draft --project <id> --mode two-lovers --look origami --json
```

With a chosen concept, write `shots.json` first: one entry per timed shot, each with `visual`, `action`, `camera`, `has_figure`, `motion_prompt`, and `lip_sync` only for singing shots. Rules for every shot:

- Exactly one clear action, written as a gesture or movement the model can see ("she lifts her hand to the glass"), never a feeling.
- Each shot shows what its line means, taken from the treatment, not what the line names.
- Object or scenery shots set `has_figure: false`; the plate prompt then carries the look's no figure line. Clip prompts never list things that are not in the frame ("no people, no streets"): a video model reads the list as things to show.
- A sung line belongs to singing shots as a whole. Put cuts at the edges of a sung line, or make every shot inside the line a singing shot. `mb draft` lists lines that the singer holds only in part; fix each one before approval, because a singer who arrives or leaves mid line reads as broken lip sync.
- When a person's face is hidden or turned away in the plate, do not ask them to turn to the camera: the model has nothing to draw the face from and invents a stranger. Make a plate that shows the face.
- Characters are named in capitals (HER, HIM, SINGER) consistently.
- No on screen text, place names or exhibit labels in the visual.
- Write a detailed `motion_prompt` for every shot. Video models follow long prompts far better than short ones. Use one flowing paragraph of 120 to 200 words, with no lists, in this order:
  1. The action, in the present tense.
  2. How it moves: speed, gestures, small lifelike details (breath, blinks, hair, fabric, rain, smoke).
  3. Who is in the shot and how they look, matching their style line.
  4. Where it is: the setting and what is behind them.
  5. The camera: shot size, angle and one movement (or locked off).
  6. The light and colour.
  7. Any change during the shot.
- Write the motion prompt from the plate's first frame. Never ask for something the image cannot become, such as a new person or a different room.
- For lip-sync shots, the person sings clearly. Never write "softly" or "barely": those words make the mouth hardly move. Say that the lips move precisely in sync with each sung syllable, the jaw and throat move naturally, the face stays stable and the camera is static or slow.
- Keep "film still", "still image" and "photo" out of motion prompts, because they ask for no motion. "The camera is still" is fine.
- When you leave `motion_prompt` out, the engine builds a fuller paragraph from the shot, its cast and the look. A hand-written one is still better, and shots with realistic people should always get one.

```bash
mb draft --project <id> --mode two-lovers --look origami --shots-file shots.json --replace --json
```

## 4b. Characters

The draft creates the mode's cast (HER and HIM, SINGER) and links each to the shots whose visual names them in capitals.

- `mb character list -p <id> --json` shows each character and its shots.
- Ask the creator how each one looks. Save it with `mb character set -p <id> --name HER --field style_line --value "..."`. Only linked shots get the line in their plate prompt.
- A reference image keeps a face consistent: `mb character add ... --ref <image>`, or for an existing character `mb character set ... --field reference_image --value <image>`. Plate adapters receive it with each request.
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
