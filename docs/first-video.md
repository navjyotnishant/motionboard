# Your first video

With the Claude plugin, the crew skills run these steps for you and stop at every approval. This page shows the same production as `mb` commands, role by role, so you can see what happens or run it yourself. Every command takes `--json` and prints one report with `verified` and `not_verified` lists.

Example: a 9:16 reel for a song called "Paper Boats".

## 1. Writer: concept, story and words

The writer picks what the video is about before anyone thinks about pictures.

- Three concepts that differ in meaning or point of view, not only in look.
- A one page `story.md`: what it is about under the words, start, turn and end, whose eyes we are in.
- The words: `lyrics.txt` for a song (section tags like `[Verse 1]`, `[Chorus]`), or `script.txt` for a promo.

With no song yet, the writing waits in `~/Motionboard/drafts/<slug>/` until the composer creates the project. Once the project exists:

```bash
mb modes                                              # modes and looks to name in each concept
mb concepts add -p <id> --file concepts.json
mb concepts choose -p <id> --concept "<title>"
```

## 2. Composer: the song and its analysis

Use your own recording as it is, or make a song or instrumental bed locally with ACE-Step 1.5 (optional, free, installed only when you say yes). Then:

```bash
mb project new --title "Paper Boats" --song song.wav --lyrics-file lyrics.txt --aspect 9:16 --look stylized
mb analyze -p <id>                          # auto: about 65 s, the loudest sustained window
mb analyze -p <id> --start 42 --end 107     # or the segment you choose
mb analyze -p <id> --start 0 --end 223.2    # or the full song
```

`analyze` cuts the segment on a beat and measures tempo, beats, loudness and sung lines. Lines are matched to the voice with local Whisper when it is installed, and only spread on the beat grid when it is not; the report says which. Check the tempo against what you hear (half or double tempo errors happen).

## 3. Director: treatment and storyboard

The director writes `treatment.md` first: what the song means, the story on screen, point of view, motifs, the visual arc, where the singer sings, and what we refuse to show. Shots come from what each line means, not what it names.

```bash
mb draft -p <id> --mode two-lovers --look origami                         # a starting board from the mode
mb draft -p <id> --mode two-lovers --look origami --shots-file shots.json --replace   # the director's shots
mb character list -p <id>
mb character set -p <id> --name HER --field style_line --value "a woman in a red paper coat"
mb character add -p <id> --name HIM --ref him.png                         # a reference keeps a face consistent
mb shot set -p <id> --shot 3 --field action --value "she lets the boat go"
mb shot move -p <id> --shot 3 --end 7.9                                   # the cut snaps to a beat
mb sheet -p <id> --kind storyboard                                        # contact sheet image
mb approve -p <id> --stage storyboard
```

Shots tile the segment exactly. The draft and sheet reports flag sung lines the singer holds only in part and shots that repeat their lyric word for word; fix them before approval. Editing a shot after its plate or clip exists marks it for redo.

## 4. Cinematographer: plates and clips

**Plates** (the first frame of every shot), from any image source:

```bash
mb adapter --list
mb plates -p <id> --adapter manual          # your own images, or any adapter you added (see adapters.md)
mb plate upload -p <id> --shot 3 --file shot-03.png
mb sheet -p <id> --kind plates
mb review -p <id> --shot 0 --decision approve --all
mb approve -p <id> --stage plates
```

Paid adapters refuse until you confirm the stated cost with `--confirm-cost`.

**Clips**, rendered locally under the memory guard:

```bash
mb guard                                    # the active guard preset
mb clips -p <id> --shots 3,9,18             # three test shots first; a fit check runs before queueing
mb worker --detach                          # renders one shot at a time in the background
mb queue                                    # progress, memory, problems per take; --pause, --resume, --stop
mb clips -p <id>                            # the rest, once the test shots look right
mb clips -p <id> --shots 6 --redo --seeds 7,2024                  # more takes of one shot
mb clips -p <id> --shots 6 --redo --backend ltx25                 # lip sync with LTX-2.5
mb clips -p <id> --shots 46 --redo --backend ltx25 --sing-until 1.9   # mute a backing echo after 1.9 s
```

Lip-sync shots render from the vocal slice for that shot. A new take never replaces the take in use. The worker skips finished shots, so you can stop and resume.

## 5. Editor: takes, cut, finish and delivery

```bash
mb sheet -p <id> --kind clips               # clips in use, with scene jump warnings
mb use -p <id> --asset <asset id>           # put a take in use
mb review -p <id> --shot 7 --kind clip --decision reject --note "reads as arriving, should leave"
mb approve -p <id> --stage clips

mb theme -p <id> --set artist=NAVAAN --set "song=Paper Boats" --set "release_note=OUT NOW" \
  --set lyrics_y=0.75 --set end_style=credits --set end_hold=4.5
mb finish -p <id>
mb approve -p <id> --stage final
mb deliver -p <id> --to ~/Dropbox/shorts --post-time "2026-12-01T18:00-06:00" --platforms "YouTube Shorts,Instagram Reels"
```

Watch every take in full before approving clips; the automatic checks do not see a changed face or lips that do not move. `finish` cuts on shot times, grades, renders the mode's animation pack, adds the end card and writes the cover and metadata. Metadata says when realistic AI people appear (altered or synthetic content). Running `finish` again overwrites the cover, so re-apply a custom cover afterwards.

Motionboard does not post. Publishing is your call.
