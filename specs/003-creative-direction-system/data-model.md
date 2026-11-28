# Data Model: Creative Direction and Visual Intelligence

Migration `0003_creative_direction.sql`, owned by the engine. Conventions from 001 hold: text ULID ids, ISO 8601 UTC text times, JSON in text columns, every write through `db/repo.py` (change events, secret refusal).

## New table: art_direction

One row per version of a project's Art Direction Bible.

| field | type | notes |
|---|---|---|
| id | text PK | |
| project_id | text FK project, cascade | |
| version | int | 1, 2, 3 per project; unique with project_id |
| profile | text | `compact` or `full` |
| status | text | `draft`, `in_review`, `approved`, `superseded` |
| body | text | JSON Bible (shape below) |
| note | text | what changed and why (designer's change note) or the reason it was sent back |
| based_on | text FK art_direction nullable | the approved version this revision started from |
| impact | text | JSON: changed sections and affected shots and assets against `based_on`, refreshed on each draft write and frozen at approval |
| created_at, updated_at | text | |
| created_via | text | `chat` or `studio` |
| approved_at | text nullable | |
| approved_via | text nullable | `chat` or `studio` |

Indexes: unique `(project_id, version)`; partial unique `(project_id) WHERE status = 'approved'`; partial unique `(project_id) WHERE status IN ('draft','in_review')`.

State machine:

```text
draft --submit--> in_review --approve--> approved --(next approval)--> superseded
  ^                   |
  +------reject-------+          draft --approve--> approved   (compact films may skip review)
```

Saving a draft while a version is open replaces the open version's body (same version number, status back to draft). Approved and superseded rows are never edited.

### Bible body (JSON)

All sections optional unless the profile requires them. Text fields are prose for the crew; `prompt_line` fields are short phrases written for image and video models. Unknown top-level keys are refused.

```text
identity:    title, concept, premise, emotional_intention, audience_experience, central_metaphor, song_relationship
world:       description, physical_rules[], architecture, environment, scale, time_and_light, belongs[], excluded[], prompt_line
characters[]: name, silhouette, construction, materials, costume, color, details[], constraints[], references_note,
             prompt_line, motion{allowed[], forbidden[], description}
materials[]: name, properties, light_response, motion_response, prompt_line
objects[]:   name, role (prop|symbol), meaning, appearance, prompt_line
color:       palette[] {name, hex #RRGGBB, role primary|secondary|accent}, relationships, contrast, prompt_line
lighting:    sources[], quality, shadows, atmosphere, prompt_line
camera:      framing, distance, lens, depth_of_field, movement[], negative_space, rhythm, transitions
motifs[]:    name, meaning, first_appearance, evolution[] {stage, state, meaning}, payoff, prompt_line
motion:      subject, identity, figure, ambient, allowed[], forbidden[], materials[], camera[], invariants[]
constraints: required[], forbidden[], negative, never_change[], may_evolve[]
```

Profile requirements:

| profile | errors when missing |
|---|---|
| compact | identity.concept, world.description, color.palette (1+) or color.prompt_line |
| full | identity.premise, emotional_intention, central_metaphor, song_relationship; world.description and physical_rules (1+); color.palette (2+, valid hex); lighting.sources and quality; camera.framing and movement; motifs (1+, each with meaning, evolution 2+ stages and payoff); motion.allowed and forbidden; constraints.never_change (1+) |

Warnings (both profiles): project characters used in figure shots but missing from `characters`; Bible characters not in the project; vague words ("cinematic", "beautiful", "consistent", "stunning") used without any other words in a field.

## New table: character_reference

| field | type | notes |
|---|---|---|
| id | text PK | |
| character_id | text FK character, cascade | |
| path | text | absolute; files live in `<project>/plates/characters/` |
| purpose | text | `face`, `silhouette`, `costume`, `material`, `detail`, `turnaround`, `other` |
| description | text | optional |
| is_primary | bool | partial unique: one primary per character |
| ord | int | order within the character |
| meta | text | JSON for adapter specific hints (for example a crop) |
| created_at | text | |

Migration: one row per existing non-empty `character.reference_image`, `purpose = 'other'`, `is_primary = 1`, `ord = 0`, same path. `character.reference_image` stays and is kept equal to the primary's path by the engine.

## Changed table: shot

| field | type | notes |
|---|---|---|
| creative | text, default `{}` | JSON: `intent`, `audience`, `metaphor`, `motifs` [{name, state}], `continuity`, `materials` [name], `objects` [name]; every key optional |
| plate_base, motion_base | text, nullable (0004) | the prompt the engine last generated; NULL on shots made before 0004 until settled |
| plate_authored, motion_authored | integer, default 0 (0004) | 1 when `plate_prompt` / `motion_prompt` is the creator's override; the engine never rewrites it |
| override_kept | text, default `{}` (0004) | JSON `{plate: version, motion: version}`: the art direction version at which the creator kept the override |

`motifs`, `continuity`, `materials` and `objects` feed prompt composition and, when changed on a shot with a finished plate, mark it for redo like a visual edit. `intent`, `audience` and `metaphor` feed reviews only. `materials` and `objects` name entries of the approved Bible (research R14).

`plate_prompt` and `motion_prompt` remain the effective prompts every reader uses. Migration `0004_prompt_overrides.sql` adds the five columns and changes no existing value (research R16).

Bible body additions: `materials[].scope` and `objects[].scope` (`all` or `shot`, default shot); `exceptions.characters: [{name, reason}]`.

## Changed table: plate_request

| field | type | notes |
|---|---|---|
| refs | text, default `[]` | JSON list sent: {character, path, purpose, primary, description} |
| refs_dropped | text, default `[]` | JSON list not sent, each with `reason` (capacity, strategy, file missing) |

`reference_image` stays: the first sent reference, for older readers.

## New table: critique

| field | type | notes |
|---|---|---|
| id | text PK | |
| project_id | text FK project, cascade | |
| stage | text | `concept`, `art_direction`, `plate`, `rough_cut` |
| role | text | `director`, `production_designer`, `cinematographer`, `editor`, `emotion_editor`, `creator` |
| verdict | text | `ready`, `revise`, `blocked` |
| summary | text | |
| findings | text | JSON list of {observation, audience_impact, implication, recommendation, shots[], motif} |
| checked | text | JSON list of what was looked at |
| not_checked | text | JSON list of what was not |
| art_direction_id | text FK art_direction nullable, set null | the version reviewed, for art_direction critiques |
| created_at | text | |
| resolved_at | text nullable | |

## Look file (repo YAML, not DB)

`looks/<slug>.yaml` gains an optional `motion` block with the motion grammar keys above (`subject`, `identity`, `figure`, `ambient`, `allowed`, `forbidden`, `materials`, `camera`, `invariants`). Looks without it use the default human grammar, which reproduces the pre-003 motion text exactly.

## Unchanged

`stage_approval` keeps its four stages. Art direction approval lives on the version row because an approval must name the version it approved; `mb approve --stage art_direction` and the Studio route to it.

## Derived values (computed, not stored)

- **Effective grammar** for a shot: look grammar, then Bible `motion` overrides (non-empty fields win), then each linked character's Bible `motion`.
- **Composed prompts**: plate, motion, continuity and negative text from the shot, its cast, the look, the effective grammar and the approved Bible. Plate and motion results are stored in `shot.plate_prompt` and `shot.motion_prompt` as before.
- **Motif progression**: shots in order with the state of each motif.
