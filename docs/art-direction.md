# Art direction

A music video made shot by shot drifts: each image matches its lyric and none of them belong to the same film. Motionboard keeps a film in one world with an **Art Direction Bible**, written by the production designer under the director's vision and approved by you.

| | What it is | Shared by |
|---|---|---|
| Mode | story pattern, shot rhythm, finishing animation | many films |
| Look | reusable rendering style (origami, after dark) and its motion grammar | many films |
| Art Direction Bible | this film's world, characters, materials, palette, light, camera, motifs, motion rules, constraints | one film |

## The Bible

A JSON or YAML file with these sections, all optional for a compact Bible:

| Section | Holds |
|---|---|
| `identity` | title, concept, premise, emotional intention, audience experience, central metaphor, why this visual concept fits this song |
| `world` | description, physical rules, architecture, environment, scale, time and light, what belongs and what never does, a prompt line |
| `characters` | per character (by project name): silhouette, construction, materials, costume, colour, details, constraints, prompt line, own motion |
| `materials`, `objects` | properties, how they take light and move; props and symbols with their meaning |
| `color`, `lighting` | named palette with hex and role, relationships, contrast; light sources, quality, shadows, atmosphere |
| `camera` | framing, distance, lens, depth of field, movement, negative space, rhythm, transitions |
| `motifs` | meaning, first appearance, evolution (stage, state, meaning), payoff, prompt line |
| `motion` | allowed, forbidden, material behaviour, camera, invariants, optional figure and ambient sentences |
| `constraints` | required, forbidden, negative prompt, never changes, may evolve |

The shape is [specs/003-creative-direction-system/contracts/art-direction.schema.json](../specs/003-creative-direction-system/contracts/art-direction.schema.json). A complete example is the acceptance fixture [engine/tests/fixtures/almost-yours/bible.json](../engine/tests/fixtures/almost-yours/bible.json) (The Museum of Almosts).

**Profiles.** `compact` needs a concept, a world description and a palette, and never blocks anything: use it for travel videos, mood loops and lyric videos. `full` needs the narrative parts (premise, intention, metaphor, why it fits the song, physical rules, two or more colours, light, camera, motifs that evolve and pay off, motion rules, what never changes), and plates wait until you approve it.

## Versions and approval

```bash
mb art draft -p <id> --file art-direction.json --profile full --note "first version"
mb art check -p <id>          # errors block approval; warnings point at gaps and vague words
mb art submit -p <id>         # awaiting your review
mb art approve -p <id>        # you said yes (or approve in the Studio's Art view)
mb art reject -p <id> --note "the thread should start slack"
mb art history -p <id>
mb art show -p <id> [--pending] [--version N] [--markdown]
```

- One approved version and at most one open draft per project. Saving while a draft is open replaces the draft.
- A revision is a new version based on the approved one. The approved version stays in force, and stays what prompts use, until you approve the revision. Approved versions are never edited or revoked.
- `mb approve --stage art_direction` is the same as `mb art approve`.
- `art-direction.md` in the project folder is regenerated from the database after every change. Edit the JSON and save it again; edits to the Markdown are overwritten.

## When the direction changes

```bash
mb art impact -p <id>
```

Before you approve a revision, the impact lists the shots that have plates or clips made under the current direction, and why: a changed character reaches the shots that character is in; world, colour, light, materials, objects and constraints reach every shot with a plate; camera reaches plates and clips; film-wide motion reaches clips; a motif reaches the shots that carry it. Identity prose is listed for review but affects no asset.

Approving recomposes every shot's prompts from the new direction. It never regenerates or changes the state of a plate or clip. In the Studio, those shots show a **DIRECTION** marker until you redo them:

```bash
mb plates -p <id> --shots 2,3,4 --adapter <adapter>
mb clips -p <id> --shots 2,3,4 --redo
```

A prompt you edited by hand is replaced when the direction is approved, as it is today when a character's style line changes; the report lists the shots it recomposed.

## Prompts in three parts

```bash
mb shot prompts -p <id> --shot 3
```

- **plate**: the shot's first frame, then each character's design (the Bible's prompt line wins over the style line), the motifs' state in this shot, the world, colour and light lines, the look's style, and the never-change rules.
- **motion**: the action, then what stays fixed, the continuity rules, how figures move under the motion grammar, each character's own movement, the scene and the camera; under 200 words, with the generic style trimmed first.
- **continuity**: the Bible's never-change rules, the shot's own continuity requirement and, for motion, the grammar's invariants.
- **negative**: the look's negative prompt plus the Bible's negative, forbidden and excluded items, sent to image sources that take one.

Only an approved Bible reaches prompts. Without one, prompts are as before.

## Motion grammar

A look can say how its subjects move:

```yaml
motion:
  subject: "the paper figures"
  identity: "each paper figure keeps the same folds, colour and proportions from the first frame to the last"
  figure: "The paper figures move like folded paper handled with care: precise pivots at the folds, ..."
  ambient: "Only light and air move: ..."
  allowed: [precise pivots at the folds, deliberate small gestures, ...]
  forbidden: [breathing, blinking, skin, sweat, hair, fabric, melting, stretching, warping, random organic body movement]
  materials: [paper bends only at its creases and never stretches]
  camera: [slow dolly, gentle push in, locked off macro]
  invariants: [the paper keeps its crisp folded geometry]
```

Looks without a `motion` block use natural human movement (breathing, blinking, hair and fabric), word for word as before. The Bible's `motion` section and each character's `motion` refine the look's grammar for one film.

Forbidden movement is never written into a prompt, not even as "no breathing": video models tend to produce what they are told about. LTX-2.3 and LTX-2.5 take no negative prompt, so the engine warns instead: `mb sheet` and `mb approve --stage storyboard` list shots whose action asks for something the grammar forbids.

## Shot creative context

Optional on any shot:

```bash
mb shot set -p <id> --shot 3 --field intent --value "the almost: everything the song promises, one fold away"
mb shot set -p <id> --shot 3 --field audience --value "held breath"
mb shot set -p <id> --shot 3 --field metaphor --value "two cases, one gap"
mb shot set -p <id> --shot 3 --field motifs --value "ruby thread: the two ends almost touching"
mb shot set -p <id> --shot 3 --field continuity --value "HIM stays turned slightly away even while reaching"
mb art motifs -p <id>
```

Motifs and continuity go into the prompts (and changing them on a shot with a finished plate marks it for redo, like a visual edit). Intent, audience and metaphor are for the crew and the reviews. Shots files for `mb draft --shots-file` accept the same keys under `creative`.

## Character references

```bash
mb character ref add -p <id> --name HER --file her-face.png --purpose face
mb character ref add -p <id> --name HER --file her-full.png --purpose silhouette --description "full figure, skirt open"
mb character ref list -p <id>
mb character ref primary -p <id> --id <ref id>
mb character ref remove -p <id> --id <ref id>     # the file stays on disk
```

Purposes: face, silhouette, costume, material, detail, turnaround, other. A character's first reference is its primary. A plate request gathers every reference of every character linked to the shot. How each image source uses them, and what happens when it cannot take them all: [adapters.md](adapters.md#references).

## Reviews

The crew records reviews as findings with four parts: what is seen, what the audience will feel, why it matters for the story, and the change to make.

```bash
mb critique add -p <id> --stage rough_cut --role editor --verdict revise --file review.json
mb critique list -p <id> [--stage plate] [--shot 2] [--open]
mb critique resolve -p <id> --id <critique id>
```

Stages: concept, art_direction, plate, rough_cut. Roles: director, production_designer, cinematographer, editor, emotion_editor, creator. Reviews never block an approval: open revise or blocked reviews are listed as not verified when you approve the matching gate. The Studio shows a shot's findings in its panel.

There is no automatic visual continuity check. Continuity, motif progression and whether an image serves the film are reviewed by people and the crew skills, by looking.

## Upgrading an existing project

`mb db migrate` (run by `./install.sh`) applies migration 0003:

- Each character's single reference image becomes its primary reference; the file does not move and `reference_image` keeps pointing at it.
- Shots gain an empty creative context; plate requests gain the references they sent and any they did not.
- No project gets a Bible. Nothing new blocks plates until you save a full Bible.
- The Studio needs schema 3; if it says the database is older, run `mb db migrate`.
- Behaviour that changes on purpose: the origami look no longer asks figures to breathe or blink; an HTTP image adapter now stops on shots with character references unless its config says how to send them (`{ref_b64}`, `refs_field`) or sets `reference_strategy` (before, it dropped them without saying so).
- Exports from older versions import unchanged; new exports carry Bible versions, references, creative context and reviews.
