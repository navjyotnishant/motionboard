# Quickstart: Creative Direction (Almost Yours, The Museum of Almosts)

## Automated acceptance

```bash
cd engine
uv run pytest tests/acceptance/test_almost_yours.py -q
```

It builds a real project from the 10 s fixture song with the two-lovers mode and origami look, adds HER and HIM with two references each, drafts shots from `tests/fixtures/almost-yours/shots.json` (both characters in some shots, the ruby thread's state per shot), saves and approves the full Bible in `bible.json`, then checks the 14 acceptance requirements of the brief against database rows: both characters' references reach one plate request, adapters refuse or report dropped references, origami motion prompts carry no human motion, the thread progresses across shots, prompts inherit the approved direction, a revision to HER's palette reports exactly HER's plated shots, an editor critique flags a shot, full-profile plates are blocked until the creator approves, and every builtin mode and look still loads.

## By hand (stub backend, no GPU)

```bash
export MB_BACKEND=stub
P=$(mb project new --title "Almost Yours test" --song engine/tests/fixtures/song10s.wav \
     --lyrics-file engine/tests/fixtures/lyrics.txt --json | jq -r .project)
mb analyze -p $P
mb draft -p $P --mode two-lovers --look origami --shots-file engine/tests/fixtures/almost-yours/shots.json
mb character ref add -p $P --name HER --file engine/tests/fixtures/plates/shot-01.png --purpose face
mb character ref add -p $P --name HER --file engine/tests/fixtures/plates/shot-02.png --purpose silhouette
mb character ref add -p $P --name HIM --file engine/tests/fixtures/plates/shot-03.png --purpose face
mb art draft -p $P --file engine/tests/fixtures/almost-yours/bible.json
mb art check -p $P           # errors: none; warnings listed
mb approve -p $P --stage storyboard
mb plates -p $P              # refused: full Bible not approved yet
mb art approve -p $P         # the creator approves
mb shot prompts -p $P --shot 2   # plate, motion, continuity, negative
mb adapter --add muse --kind handoff
mb plates -p $P --adapter muse
mb plate requests -p $P      # each two-character shot lists HER and HIM references
mb art motifs -p $P          # ruby thread: state per shot
mb art draft -p $P --file engine/tests/fixtures/almost-yours/bible-v2.json --note "HER deeper garnet"
mb art impact -p $P          # HER's shots only
cat ~/Motionboard/projects/*almost-yours-test*/art-direction.md
mb studio start              # Art view: status, palette, references, motif grid, pending change
```

## Not covered by automation

- Rendering real plates and clips on Apple Silicon with the new prompts and references (needs Muse or another image source and LTX weights). Nothing in this feature was visually validated on a production run.
- Whether a given image tool actually honours several reference images: Motionboard passes them and reports what it passed.
