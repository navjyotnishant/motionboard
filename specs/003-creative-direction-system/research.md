# Research: Creative Direction and Visual Intelligence

Decisions made while reading the code on `main` at f0be7d1. Each has the alternatives that were rejected and why.

## R1. Where the Bible lives

**Decision**: SQLite table `art_direction`, one row per version, JSON body. `art-direction.md` in the project folder is regenerated from the database after every change and says so in its header.

**Why**: Constitution VII and VIII: one local database is the project state; the chat and the Studio read the same rows. A Markdown file as source would diverge the moment someone edits it in a text editor while the Studio edits the database.

**Rejected**: YAML file in the project folder as source (two sources of truth); one column per section (dozens of columns, every new field a migration); a separate document store (new dependency).

## R2. Approval of the Bible

**Decision**: approval is stored on the version row (`status`, `approved_at`, `approved_via`). `mb art approve` is the command; `mb approve --stage art_direction` routes to it so the existing approve habit works; the plates gate checks it when the Bible is full profile.

**Why**: `stage_approval` has one row per stage and cannot say which version was approved. Approving "the art direction" without naming the version would let a later draft inherit approval, which the brief forbids ("a revision must not silently overwrite the approved Bible"). This is the clear architectural reason to keep approval on the version and not create a parallel stage row.

**Rejected**: adding `art_direction` to the `stage_approval` CHECK (needs a table rebuild and still loses the version); a new approvals table (parallel system).

**Constitution note**: Principle V names four stage commands. The Bible gate is not a fifth stage: it sits inside the storyboard to plates boundary, like the plate cost confirmation, and only for full-profile films. No amendment is proposed.

## R3. Compact and full profiles

**Decision**: the profile is chosen per version. Full means the plates gate requires an approved version. Compact never blocks. No Bible at all behaves as before.

**Why**: "Appropriate complexity": a travel video should not need a motif evolution table. Making the gate depend on the profile keeps simple projects unchanged and makes the stricter path explicit.

## R4. What a Bible change affects

**Decision**: a pure function compares two bodies section by section and maps changes to shots:

| change | affected |
|---|---|
| a character entry (by name) | shots linked to that character |
| world, color, lighting, materials, objects, constraints, identity | every shot with an active plate |
| camera | every shot with an active plate or clip |
| motion (film level) | shots with an active clip |
| a character's motion | that character's shots with an active clip |
| a motif (by name) | shots whose creative `motifs` include it |

The result lists shots and the active asset ids that predate the approval. It is stored on the version and reported. Shot states are not changed.

**Why**: The brief says identify, do not regenerate. Changing `state` to `needs_redo` would also revoke plate approvals and re-queue clips (the queue treats `dirty` as "render again", see `jobs/queue.py has_valid_clip`). The creator decides which shots to redo with the existing `--shots` and `--redo` options.

**Rejected**: setting `dirty` (re-queues clips silently); per-field diffs mapped to individual words in prompts (fragile).

## R5. Prompts follow the approved Bible

**Decision**: when a version is approved, plate and motion prompts of every shot are recomposed from the new direction. Assets are untouched; the impact list says which existing plates and clips were made under the earlier direction.

**Why**: prompts describe the next request. Leaving old prompts in place would make the next `mb plates --shots 4` render the old direction. Recomposing on direction changes is what the engine already does for a character's style line.

**Known cost**: a hand-edited `plate_prompt` is replaced on approval, as it is today when a style line changes. The report lists recomposed shots.

## R6. Character description precedence

**Decision**: when the approved Bible has a `prompt_line` for a character, prompts use it; otherwise `character.style_line`. No mirroring writes.

**Why**: compact projects and projects without a Bible keep using style lines. Writing the Bible text into `style_line` would create a second copy that can be edited independently.

## R7. Reference model and migration

**Decision**: normalized `character_reference` table; migration copies each `reference_image` as the primary; `character.reference_image` is kept as a mirror of the primary, maintained only by the engine.

**Why**: the brief prefers normalized rows; existing readers (old Studio builds, export files, the plates report) still read `reference_image`.

**Rejected**: JSON array column on `character` (no ordering or primary constraint in SQL, harder to show per reference in the Studio); dropping `reference_image` (breaks older exports and readers).

## R8. Adapter reference capacity

**Decision**: capacity per adapter instance:

| kind | capacity |
|---|---|
| manual | unlimited (shown to the creator) |
| handoff | unlimited (listed for the agent that fulfils it) |
| command | many if an argv element is exactly `{refs}`; 1 if any element contains `{ref}`; else 0 |
| http | many if config has `refs_field`; 1 if the body template uses `{ref_b64}` or `{ref}`; else 0 |

Strategy (`reference_strategy` in adapter config or `--reference-strategy` per run): `strict` (default, error), `primary` (one primary per character, error if still over), `first` (first N in cast order), `none` (send none). Dropped references are stored on the request and reported with a reason.

**Why**: the HTTP adapter never sent references; failing loudly is a behaviour change, but it replaces a silent drop with a clear message and a one-word fix.

## R9. Motion grammar placement

**Decision**: grammar lives in the look YAML (reusable), refined by the Bible (film) and per character. Default grammar reproduces the existing human text so looks without a grammar are byte-for-byte unchanged.

**Why**: "Associated with the appropriate visual direction, with optional character-specific rules". Looks are reusable rendering styles, so the physical behaviour of their material belongs there; a specific film can tighten it.

**Rejected**: per-character only (every project re-types origami rules); hard-coded `if look == origami` branches (not reusable).

## R10. Negative movement

**Decision**: forbidden movement is never written into the positive motion prompt, even negated, and a board check warns when an action asks for it. Video backends take no negative prompt today (`backends/ltx23.py`, `ltx25.py` pass only `-p`).

**Why**: video models react to named concepts; "no breathing" tends to produce breathing. The limitation is stated in reports and docs.

## R11. Shot creative context storage

**Decision**: one JSON column `shot.creative` with five optional keys.

**Why**: five sparse fields on every shot would be columns that are empty for most projects; JSON keeps simple projects unchanged and the Studio can show only what is set. Validation of keys lives in the engine.

## R12. Critiques

**Decision**: a `critique` table with structured findings; never blocks approvals; open REVISE or BLOCKED critiques are listed in approval reports as not verified.

**Why**: the creator keeps authority (constitution, brief principle 6). Reviews must persist and be visible in the Studio, and their four-part structure keeps them about the film, not taste.

## R13. Studio tests

**Decision**: view-model logic (status labels, palette parsing, motif progression grid, affected-shot lookup) goes in `studio/src/lib/art.ts` with Vitest unit tests in Node; rendered components are covered by Playwright against the stub e2e server.

**Why**: the repo has no DOM test environment or React Testing Library; adding jsdom and RTL for a few components adds weight, while Playwright already exercises the real build against the shared database (which is also the "Studio and CLI read the same state" test).
