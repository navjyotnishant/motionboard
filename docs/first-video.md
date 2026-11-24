# Your first video

The plugin skills run these steps for you in Claude Code. This page shows the same steps as `mb` commands, so you can see what happens. Every command takes `--json` and prints one report.

## 1. Project and song

```bash
mb project new --title "Paper Boats" --song song.mp3 --lyrics-file lyrics.txt --aspect 9:16
mb analyze -p <id>
```

`analyze` picks about 60 seconds (the first chorus when it can find it), cuts it on a beat, and measures tempo, beats, loudness and sung lines.

## 2. Storyboard

```bash
mb modes                                    # story modes with their animation packs, and looks
mb draft -p <id> --mode two-lovers --look origami
mb character list -p <id>
mb character set -p <id> --name HER --field style_line --value "a woman in a red paper coat"
mb shot set -p <id> --shot 3 --field action --value "she lets the boat go"
mb sheet -p <id> --kind storyboard          # contact sheet image
mb approve -p <id> --stage storyboard
```

Shots tile the segment exactly. Cuts sit on sung lines or beats. Editing a shot after its plate or clip exists marks it for redo.

## 3. Plates

```bash
mb adapter --list
mb plates -p <id> --adapter manual          # or any adapter you added, see adapters.md
mb review -p <id> --shot 0 --decision approve --all
mb approve -p <id> --stage plates
```

## 4. Clips

```bash
mb fit --width 576 --height 1024 --frames 97   # will one shot fit in memory? nothing starts
mb clips -p <id>
mb worker                                   # renders one at a time under the memory guard
mb queue                                    # progress; --stop, --pause, --resume, --move
mb review -p <id> --shot 0 --kind clip --decision approve --all
mb approve -p <id> --stage clips
```

Lip-sync shots render with audio to video and the vocal slice for that shot. The worker skips finished shots, so you can stop and resume.

## 5. Finish and deliver

```bash
mb theme -p <id> --set artist=NAVAAN --set "song=Paper Boats" --set "release_note=OUT NOW"
mb finish -p <id>
mb approve -p <id> --stage final
mb deliver -p <id> --to ~/Dropbox/shorts --post-time "2026-12-01 18:00 CT" --platforms "YouTube Shorts,Instagram Reels"
```

`finish` cuts on shot times, grades, renders the mode's animation pack, adds the end card and writes the cover and metadata. Metadata says when realistic AI people appear (altered or synthetic content).
