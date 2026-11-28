# CLI contract: creative direction (additions to 001 contracts/cli.md)

Every command takes `--json` and prints one report `{ok, command, project, data, verified, not_verified, next[, error]}`. Error codes are the existing set. `-p` takes a project id or its last characters.

## mb art

| command | does | data |
|---|---|---|
| `mb art draft -p ID --file F [--profile compact\|full] [--note T]` | Save a Bible draft from JSON or YAML. Opens a new version based on the approved one, or replaces the open draft. Writes `art-direction.md`. | `version`, `status`, `profile`, `errors`, `warnings`, `impact` (preview against the approved version) |
| `mb art check -p ID` | Validate the open version. | `errors`, `warnings` |
| `mb art submit -p ID` | Open draft to `in_review`. Refuses with `INVALID_INPUT` when there are errors. | `version`, `status` |
| `mb art reject -p ID --note T` | `in_review` back to `draft` with the reason. | `version`, `status`, `note` |
| `mb art approve -p ID [--via chat\|studio]` | The creator approves the open version. Errors refuse with `GATE_NOT_APPROVED`. The previous approved version becomes `superseded`; prompts are recomposed; impact stored. | `version`, `superseded`, `impact`, `recomposed` (shot numbers) |
| `mb art show -p ID [--version N] [--pending] [--markdown]` | The approved version by default. | `version`, `status`, `profile`, `body` or `markdown`, `pending` (version and status of an open draft) |
| `mb art history -p ID` | All versions. | `versions` [{version, status, profile, note, created_at, approved_at, approved_via}] |
| `mb art impact -p ID` | Impact of the open version against the approved one, or of the last approval. | `impact` {changed: [sections], shots: [{shot, reasons, assets}]} |
| `mb art motifs -p ID` | Motif progression across shots. | `motifs` [{name, meaning, shots: [{shot, state}]}] |
| `mb art export -p ID [--out PATH]` | Write the Markdown view. | `path` |

`mb approve -p ID --stage art_direction` is the same as `mb art approve`. `--revoke` is refused for `art_direction` with a hint to save a revision.

Gate rule: `mb plates` and `mb approve --stage plates` refuse with `GATE_NOT_APPROVED` when the project's latest Bible version is `full` and no version is approved.

## mb character ref

| command | does |
|---|---|
| `mb character ref add -p ID --name HER --file F [--purpose face] [--description T] [--primary]` | Copy the image into `plates/characters/`, add a reference. The first reference of a character is primary. |
| `mb character ref list -p ID [--name HER]` | References by character, primary first. |
| `mb character ref remove -p ID --id REF` | Remove a reference (the file is kept on disk). A new primary is chosen if the primary was removed. |
| `mb character ref primary -p ID --id REF` | Make a reference the primary. |

Each change marks finished plates of that character's shots for redo (as `mb character set --field reference_image` does today). `mb character set --field reference_image` replaces the primary reference. `mb character list` gains `references` per character.

## mb shot

- `mb shot set --field intent|audience|metaphor|continuity|motifs --value V`: creative context. `motifs` takes a JSON list `[{"name": "...", "state": "..."}]` or lines `name: state`. Empty value clears the field.
- `mb shot prompts -p ID --shot N`: `{plate, motion, continuity, negative, grammar, warnings}` composed now from the approved Bible, the look and the shot.
- Shots file (`mb draft --shots-file`) entries may carry `creative: {...}` with the same keys.

## mb plates and mb adapter

- `mb plates ... [--reference-strategy strict|primary|first|none]` overrides the adapter's configured strategy for this run.
- Per shot results (`done`, `pending`, `failed`) gain `references` and `references_dropped`.
- `mb plate requests` entries gain `references` (all, labelled); `reference_image` stays (first reference).
- `mb adapter --list` entries gain `reference_capacity` (number or `"unlimited"`) and `reference_strategy`.

## mb critique

| command | does |
|---|---|
| `mb critique add -p ID --stage concept\|art_direction\|plate\|rough_cut --role ROLE --verdict ready\|revise\|blocked --file F` | File: `{summary, findings: [{observation, audience_impact, implication, recommendation, shots?, motif?}], checked: [], not_checked: []}`. Each finding needs all four parts. |
| `mb critique list -p ID [--stage S] [--shot N] [--open]` | Critiques, newest first. |
| `mb critique resolve -p ID --id C` | Mark resolved. |

Roles: `director`, `production_designer`, `cinematographer`, `editor`, `emotion_editor`, `creator`.

`mb approve` (storyboard, plates, clips, final) and `mb art approve` add open REVISE or BLOCKED critiques of the matching stage to `not_verified`. They never block.
