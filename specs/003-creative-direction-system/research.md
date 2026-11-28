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
| world, color, lighting, constraints | every shot with an active plate |
| a material or an object (by name) | shots it belongs to before or after the change (R14); every shot when scoped `all` |
| identity | listed as changed for review; no asset is affected by prose alone |
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

## R14. Which materials and objects belong to a shot

**Decision**: one rule set in `direction/assoc.py`, used by composition and by impact. An entry belongs to a shot when the entry says `scope: all`, the shot lists its name (`creative.materials`, `creative.objects`), its name appears in the shot's visual as whole words (last word may be plural), or, for materials, the Bible's `materials` text of a character in the shot names it. A material contributes its `prompt_line` (or its name); an object its `prompt_line`, or `name: appearance`. A line already present in the prompt or the look's style line is not repeated.

**Why**: The first pass dropped materials and objects from prompts entirely. Injecting all of them everywhere puts a prop from one scene into every image. Name matching makes the common case free; the explicit list covers shots whose visual does not name the thing; `scope: all` covers the world's own surface.

**Rejected**: injecting every entry in every shot; a join table (the association is shot-level creative data and already has a home in `shot.creative`); matching on appearance text (too loose).

## R15. Custom motion prompts and the grammar

**Decision**: a prompt written by hand is stored as written. `direction/conflicts.py` reports where a shot contradicts the direction: forbidden movement in an action or in a motion prompt, forbidden or excluded things added by an authored plate prompt, an undesigned character under a full Bible. The effective grammar is the look, refined by the Bible, plus the rules of the characters in the shot and the motion behaviour of the shot's materials. `mb plates` refuses with `DIRECTION_CONFLICT` before any request row is written, unless each conflict is an override the creator kept or the run passes `--accept-conflicts`.

**Why**: The first pass checked only the `action` field, so `motion_prompt` in a shots file or from `mb shot set` reached the video model unchecked. Refusing is the only way to show a conflict before an image exists; the flag and the keep decision leave the choice with the creator (Principle IV).

**Rejected**: rewriting or stripping the creator's text; blocking the edit itself; a silent warning after generation.

## R16. Generated baselines and authored overrides

**Decision**: migration 0004 adds `plate_base`, `motion_base` (the generated prompt), `plate_authored`, `motion_authored` and `override_kept` to `shot`. `plate_prompt` and `motion_prompt` stay the effective text every reader uses. Writing a prompt by hand sets the authored flag; recomposition updates the base and rewrites the effective prompt only when the part is not authored. Writing the base text back, or an empty value, clears the override.

A shot made before 0004 has no base. It is settled on first use, before anything changes: the base becomes what the engine generates from the direction at that moment, and a stored prompt that differs is kept as authored.

**Why**: The first pass regenerated prompts on approval and replaced hand edits. Separate columns keep renderers, exports and the Studio reading one field. Settling treats an unknown difference as the creator's work: a hand edit and a prompt written by an older engine look the same, and losing a hand edit is the worse mistake.

**Cost, stated plainly**: on a database from an older engine, most motion prompts differ from today's composition and are adopted as authored. On a copy of a real schema-2 database, 73 of 74 motion prompts and 0 of 74 plate prompts in one project were adopted. They stop following the direction until cleared with `mb shot override clear --all --part motion`.

**Rejected**: assuming legacy prompts are generated (erases hand edits, the reported defect); a diff or merge of prose prompts (not reliable).

## R17. Characters a full Bible must design

**Decision**: under the full profile, a character with at least one shot and no `characters` entry is an error on check, submit and approve, reported also as `missing_designs`. `exceptions.characters: [{name, reason}]` records a deliberate gap, shown as a warning and in the Markdown view. The compact profile keeps the warning. After approval, a newly linked undesigned character is a plate conflict (R15).

**Why**: A warning let a full Bible be approved without its lead. The exception keeps the creator in charge of real cases (a figure seen only as a shadow).

## R18. Reference identity for adapters

**Decision**: every adapter kind can learn which reference is which. Command: `refs_format` shapes each `{refs}` argument; `{refs_manifest}` is a JSON file per request; `{refs_json}` is the list inline. HTTP: `refs_meta` turns each `refs_field` entry into an object with the API's own field names; `refs_manifest_field` puts the metadata list at a second path. Settings are validated when the adapter is added. Manual and handoff already list labelled references.

**Why**: A bare list of paths cannot tell HER's face from HIM's silhouette. Providers differ, so the mapping is configuration, not code.
