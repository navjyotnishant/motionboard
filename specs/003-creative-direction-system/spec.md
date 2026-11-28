# Feature Specification: Creative Direction and Visual Intelligence

**Feature Branch**: `003-creative-direction-system`

**Created**: 2026-11-27

**Status**: Approved for implementation (direction approved by the project owner; this spec reviewed against the constitution before planning)

**Input**: Implementation brief "Motionboard Feature 003: Creative Direction and Visual Intelligence". Motionboard should take a song and its emotional meaning, develop an original cinematic concept, establish a coherent visual universe and direct shots that belong to the same film, instead of generating attractive images that each match a lyric.

## Context

Motionboard already separates a **mode** (story structure, shot pattern, finishing animation) from a **look** (a reusable rendering style). Two films that share the origami look still need different worlds: the Museum of Almosts is a midnight museum with brass and smoked glass; another origami film could be a paper harbour at noon. Today nothing holds that film-specific identity, so it lives in chat, in `treatment.md` and in each shot's free text, and it drifts.

Four concrete gaps were found in the engine while preparing this spec:

1. **One reference per character, one per shot.** `character.reference_image` holds one image; `plates/service.py` picks one reference per shot with `LIMIT 1`. A shot with HER and HIM sends only one of them, silently.
2. **Human motion for paper figures.** `draft.motion_prompt()` always adds "steady breathing, soft blinking, hair and fabric shifting" to figure shots. On the origami look this asks a folded-paper figure to breathe and blink.
3. **The HTTP adapter never sends references.** A character reference is dropped without a word.
4. **No film-level identity or review.** Palette, materials, motifs and camera rules are not stored anywhere the cinematographer, editor or Studio can read, and a change to them cannot be traced to the plates it invalidates.

## Principles this feature serves

Meaning before imagery; originality before convention; visual identity before shot generation; continuity across the film; creative judgment over blind compliance; the director and creator keep authority; complexity proportional to the production.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A film has an Art Direction Bible (Priority: P1)

After the director picks a concept, the production designer writes the film's Art Direction Bible: identity, world, characters, materials and objects, colour and light, cinematic language, motifs and their progression, motion grammar and visual constraints. The creator reviews it (in chat or in the Studio) and approves it. Later revisions are drafts that never overwrite the approved version until the creator approves them.

**Why this priority**: Everything else (prompts, references, reviews, impact) reads the approved Bible. Without it there is no single visual truth for the film.

**Independent Test**: Create a project, save a full Bible draft, check it, approve it, save a revision. `mb art history` shows v1 approved then superseded, v2 pending; `mb art show` returns v1 until v2 is approved; the Markdown file in the project folder matches the database.

**Acceptance Scenarios**:

1. **Given** a project, **When** the designer saves a Bible with `mb art draft`, **Then** it is stored as version 1 with status draft, and `art-direction.md` is written in the project folder as a generated view.
2. **Given** a full-profile draft missing required sections, **When** it is checked or submitted, **Then** the report lists each missing part and the draft cannot be approved.
3. **Given** an approved v1, **When** a revision is saved, **Then** v2 is a draft, v1 stays approved and remains the version prompts use.
4. **Given** v2 pending, **When** the creator approves it, **Then** v1 becomes superseded, v2 approved, and the report lists the shots and assets the change affects.
5. **Given** a simple travel or mood-loop project, **When** it has no Bible or a compact one, **Then** nothing blocks plates; a compact profile needs only concept, world and palette.

---

### User Story 2 - Plates carry every character's references (Priority: P1)

Each character can have several reference images (face, silhouette, costume, material, detail, turnaround, other), one marked primary, in an order. When plates are requested for a shot, every character linked to the shot contributes its references, labelled by character and purpose. Adapters declare how many references they can use; a request that exceeds that fails with a clear message unless a selection strategy is configured, and the report says exactly which references were sent and which were not.

**Why this priority**: Two-character shots are common (HER and HIM in Almost Yours). Silently sending one reference breaks character identity, which is the first thing viewers notice.

**Independent Test**: A shot linked to HER (two references) and HIM (two references) produces a handoff request listing four references with character and purpose. A command adapter that only has `{ref}` refuses the same request with an actionable error; with `reference_strategy: primary` it sends one per character only if capacity allows, and reports the rest as dropped.

**Acceptance Scenarios**:

1. **Given** an existing database with single `reference_image` values, **When** it migrates, **Then** each becomes a primary reference row and the file path is unchanged.
2. **Given** a shot with two characters, **When** plates are requested through a handoff adapter, **Then** the pending request shows all references of both characters.
3. **Given** an adapter that supports fewer references than requested and no strategy, **When** plates are requested, **Then** that shot fails with `INVALID_INPUT`, the hint names the strategies, and no image is generated.
4. **Given** a strategy that drops references, **When** plates are requested, **Then** the report and the stored request list the dropped references by character and purpose.

---

### User Story 3 - Motion follows the film's physical rules (Priority: P1)

A look can define a motion grammar: what the subject is, how figures move, what never moves, how materials behave, camera rules and continuity invariants. The Bible can refine it for a film and for a character. Prompts are composed in three distinct parts: the plate prompt (the first frame), the motion prompt (what moves and how) and continuity instructions (what must not change). Looks without a grammar keep today's behaviour.

**Why this priority**: The breathing origami figure is a visible, repeatable defect in real renders.

**Independent Test**: Draft a two-lovers board on the origami look. No motion prompt contains breathing, blinking, hair or fabric instructions; each describes paper behaviour. The same board on a look without a grammar produces the same motion prompts as before this feature.

**Acceptance Scenarios**:

1. **Given** the origami look, **When** a figure shot's motion prompt is composed, **Then** it describes fold pivots and paper tension and has no human-motion clause.
2. **Given** a shot whose action asks for something the grammar forbids (for example "she breathes"), **When** the board is checked, **Then** a warning names the shot and the forbidden movement.
3. **Given** an approved Bible with never-change rules, **When** prompts are composed, **Then** the continuity clause appears in both plate and motion prompts and `mb shot prompts` shows the three parts separately.
4. **Given** any composed motion prompt, **Then** it stays within the 200 word limit with the action, continuity and cast kept and the style tail trimmed first.

---

### User Story 4 - The crew works as one film unit (Priority: P2)

A new production designer skill turns the director's approved concept into the Bible and defends its choices. The director briefs the designer, approves the Bible on the creator's behalf only when the creator says so, and resolves disagreements. The cinematographer reads the Bible before any plate and separates first frame from movement. The editor reviews the whole film's visual progression and motif payoff. The emotional editor checks that imagery carries subtext rather than illustrating lyrics.

**Why this priority**: The engine can store direction; only the crew turns it into decisions. This is skills and handoffs, built on Stories 1 to 3.

**Independent Test**: Read the five skills end to end: the handoffs agree on file names, commands and who approves what; none lets an agent approve a gate or change an approved Bible on its own.

**Acceptance Scenarios**:

1. **Given** an approved concept, **When** the designer skill runs, **Then** it produces a Bible draft through `mb art draft` and asks the director and creator to review it.
2. **Given** an approved Bible, **When** the cinematographer prepares plates, **Then** it reads `mb art show` and `mb shot prompts` first and does not introduce a style the Bible does not define.

---

### User Story 5 - Shots carry creative intent, reviews carry reasons (Priority: P2)

A shot can optionally hold its dramatic intention, the audience experience, its visual metaphor, the state of each motif in it, and continuity requirements. Reviews at concept, art direction, plate and rough-cut stages are stored as findings with four parts: observation, audience impact, creative implication, recommendation, and they can point at shots.

**Why this priority**: Without intent on the shot, reviewers argue about pictures; with it they argue about the film. Without stored findings, the reasons vanish with the chat.

**Independent Test**: Set motif states for the ruby thread on five shots; `mb art motifs` shows the progression in shot order. Add an editor critique that flags one shot as beautiful but not serving the story; `mb critique list --shot N` returns it and the Studio shows it on that shot.

**Acceptance Scenarios**:

1. **Given** a shot, **When** none of the creative fields are set, **Then** nothing in the board, prompts or Studio requires them.
2. **Given** a motif state on a shot, **When** the plate prompt is composed, **Then** the motif's look from the Bible and the shot's state are in it.
3. **Given** a critique finding missing its recommendation, **When** it is added, **Then** it is refused with the missing part named.
4. **Given** open REVISE critiques, **When** the storyboard or Bible is approved, **Then** the approval is not blocked, and the report lists the open critiques as not verified.

---

### User Story 6 - The Studio shows the direction (Priority: P2)

The Studio gains an Art view beside Grid and Story: status (draft, awaiting review, approved), palette swatches, world and materials, characters with their references, props and motifs with their progression across shots, motion rules, and pending changes with the shots they affect. The creator can submit, approve or send back a Bible and manage references from there. The shot panel shows the shot's creative context and critiques in a compact, collapsed section.

**Why this priority**: The creator approves; the creator needs to see. Builds on Stories 1, 2 and 5.

**Independent Test**: With the e2e stub project, approve a Bible from the Studio; `mb art show` from chat reports the same version approved. Add a reference in chat; it appears in the Studio without a reload.

**Acceptance Scenarios**:

1. **Given** a pending revision, **When** the Art view opens, **Then** it shows "awaiting review", the changed sections and the affected shots.
2. **Given** a shot with creative context, **When** its panel opens, **Then** intent, metaphor, motif state and continuity are visible in a collapsed section that does not push the main fields down.

### Edge Cases

- A project with no Bible at all behaves exactly as before (no gate, no new prompt text).
- A Bible names a character that does not exist in the project: warning, not an error; it is reported in the check.
- A project character used in figure shots is missing from a full Bible: warning listing the shots.
- A reference file is deleted on disk: it is reported as missing and not sent; the request lists it as dropped with reason "file missing".
- A revision is saved while another draft is open: the open draft is replaced (one open draft per project), its version number kept.
- Approving a Bible with validation errors: refused with `GATE_NOT_APPROVED` and the error list.
- A creator wants to undo approval: approval is not revoked; they approve a revision instead, so history stays linear.
- Prompt word limit: action, continuity and cast lines are kept; the generic style tail is trimmed first.
- Old JSON exports (without Bible, references or creative fields) import unchanged.

## Requirements *(mandatory)*

### Functional Requirements

**Art Direction Bible**

- **FR-001**: The system MUST store a per-project Art Direction Bible as structured data in the project database, with sections identity, world, characters, materials, objects, color, lighting, camera, motifs, motion and constraints, each optional unless the profile requires it.
- **FR-002**: The Bible MUST support two profiles: compact (concept, world, palette) and full (the sections and fields listed in data-model.md). Validation MUST return errors (block submit and approval) and warnings (reported only).
- **FR-003**: The Bible MUST be versioned. Each version has a status draft, in_review, approved or superseded; at most one approved and at most one open (draft or in_review) version per project; approved versions are never edited in place.
- **FR-004**: Approval MUST be an explicit creator action (`mb art approve`, `mb approve --stage art_direction`, or the Studio button) and MUST record when and through which surface it happened.
- **FR-005**: When a project's open or latest Bible uses the full profile and no version is approved, the engine MUST refuse plate requests and the plates gate with `GATE_NOT_APPROVED`. Compact or absent Bibles MUST NOT block anything.
- **FR-006**: On approval of a revision, the engine MUST compute which sections changed and which shots and active assets they affect (characters to their linked shots, world, palette, light, constraints to every shot with a plate, motion to shots with clips, motifs to shots carrying that motif), store that impact with the version, and report it. It MUST NOT regenerate or change the state of any asset.
- **FR-007**: The engine MUST write a readable Markdown view of the Bible (approved plus pending) to the project folder after every Bible change, marked as generated from the database.
- **FR-008**: Pending revisions MUST show their impact against the approved version before approval.

**Character references**

- **FR-009**: A character MUST support any number of references, each with path, purpose (face, silhouette, costume, material, detail, turnaround, other), description, primary flag (at most one per character), order and adapter metadata.
- **FR-010**: Migration MUST copy each existing `character.reference_image` into a primary reference without moving the file; `character.reference_image` remains as a mirror of the primary for older readers.
- **FR-011**: A plate request MUST gather the references of every character linked to the shot through `shot_character`, primary first, then by order, labelled with character and purpose, and store them with the request.
- **FR-012**: Every adapter kind MUST declare its reference capacity. Manual and handoff show all references to the person or agent fulfilling the request. Command adapters support one (`{ref}`) or many (`{refs}`). HTTP adapters support one (`{ref_b64}`) or many (`refs_field`), and none otherwise.
- **FR-013**: When references exceed capacity and no strategy is configured, the shot's request MUST fail with an actionable error. Strategies `primary`, `first` and `none` MAY be set on the adapter or per run; whatever is dropped MUST be listed in the report and stored on the request.

**Motion grammar and prompt composition**

- **FR-014**: A look MAY define a motion grammar (subject noun, identity invariant, figure movement, ambient movement, allowed, forbidden, material behaviour, camera, invariants). Without one, motion prompts MUST equal today's output.
- **FR-015**: The origami look MUST define a grammar with no breathing, blinking, skin, hair or fabric behaviour.
- **FR-016**: The approved Bible MAY refine the grammar for the film and for each character; its never-change constraints and shot continuity requirements MUST appear as a continuity clause in plate and motion prompts.
- **FR-017**: Plate, motion and continuity text MUST be composed by separate functions; `mb shot prompts` MUST return them separately, with the negative prompt.
- **FR-018**: The board check MUST warn when a shot's action or motion prompt asks for movement the grammar forbids.

**Shot creative context and reviews**

- **FR-019**: A shot MAY hold intent, audience, metaphor, motifs (name and state) and continuity, editable through `mb shot set` and the shots file. Motif states and continuity affect prompts; the others do not.
- **FR-020**: The engine MUST store critiques at concept, art_direction, plate and rough_cut stages, by role, with verdict ready, revise or blocked, findings each having observation, audience impact, implication and recommendation (optionally shots and motif), and what was and was not checked.
- **FR-021**: Approvals MUST list open revise or blocked critiques for that stage in `not_verified`; critiques MUST NOT block approval.

**Crew skills**

- **FR-022**: A new `mb-production-designer` skill MUST own the Bible; director, cinematographer, editor and emotion-editor skills MUST be updated to read, respect and review it. No other new skill.

**Studio**

- **FR-023**: The Studio MUST show the Bible (status, palette, world, materials, characters with references, objects, motifs with progression, motion rules, pending changes and affected shots) and let the creator submit, approve or send back, and manage references, all through the engine CLI.
- **FR-024**: The shot panel MUST show creative context and critiques without adding a large form.

**Compatibility and portability**

- **FR-025**: Existing projects, modes, looks and animation packs MUST keep working; existing CLI commands and JSON report shapes MUST stay compatible (new keys only).
- **FR-026**: Project JSON export and import MUST carry Bible versions, references, creative fields and critiques; older exports MUST import unchanged. They MUST also carry each shot's generated baselines, authored flags and keep decisions (`override_kept`). A keep decision stays tied to the art direction version it was made for, so it does not apply to a newer version after import.

**Corrective pass (review of the first implementation)**

- **FR-027**: A Bible material or object MUST reach a shot's plate prompt only when it belongs to that shot: its entry says `scope: all`, the shot lists it (`creative.materials`, `creative.objects`), its name appears in the shot's visual, or (materials) a character in the shot is made of it. Materials contribute their prompt line; objects their prompt line, or their name and appearance. Nothing else is injected. `mb shot prompts` MUST say which belong to the shot and why.
- **FR-028**: A motion prompt supplied by hand (a shots file, `mb shot set`, the Studio) MUST be kept as written and MUST be checked against the effective motion grammar. A contradiction is reported on the command that wrote it, on `mb sheet`, on storyboard approval and on `mb clips`.
- **FR-029**: The effective grammar for a shot MUST merge the look, the approved Bible and, for each character in the shot, that character's forbidden movement, material behaviour and invariants. A character can add rules, never lift one. Material behaviour of the shot's own materials joins the rules. Forbidden terms and material behaviour are never written into prompts; character invariants join the continuity clause.
- **FR-030**: `mb plates` MUST stop before any image is requested or paid for when the shots to generate contradict the direction, naming each conflict, unless the creator kept the authored prompt on purpose or the run passes `--accept-conflicts`.
- **FR-031**: The generated prompt of a shot (its baseline) MUST be stored apart from a creator-authored override. An art direction approval, a character edit or a shot edit regenerates baselines and MUST NOT rewrite an authored override.
- **FR-032**: After an approval, every authored override MUST be reported: whether the generated prompt under it changed and whether it now contradicts the approved Bible (forbidden or excluded things in a plate prompt; forbidden movement in a motion prompt).
- **FR-033**: The creator MUST be able to keep an override (recorded for the current Bible version; a later version asks again), revise it, or clear it back to the generated prompt, from the CLI and, for clearing, from the Studio.
- **FR-034**: A full Bible MUST NOT be submitted or approved while a character that appears in the storyboard has no design, unless the Bible records an intentional exception with a reason (`exceptions.characters`). The gap MUST be reported as an error and as structured data (`missing_designs`), distinct from advisory warnings. Compact Bibles keep the advisory. A character added to a shot after approval is caught before plates.
- **FR-035**: Command and HTTP adapters MUST be able to receive, for every reference, the character, purpose, primary flag, path, description and position: a manifest file or inline JSON and a per-argument format for commands; an object mapping and a parallel metadata list for HTTP. Existing `{ref}`, `{refs}`, `{ref_b64}` and `refs_field` configurations MUST behave as before.
- **FR-036**: A change to one material or one object MUST be reported as affecting only the shots it belongs to under FR-027 (before or after the change), not every shot.

### Key Entities

- **Art Direction (version)**: one version of a project's Bible: profile, status, body, change note, based-on version, timestamps, approval surface, stored impact.
- **Character Reference**: one image for one character with purpose, description, primary flag and order.
- **Shot Creative Context**: optional intent, audience, metaphor, motif states and continuity on a shot.
- **Critique**: a structured review at a stage, by a role, with findings that can point at shots.
- **Motion Grammar**: physical movement rules of a look, refined by the Bible.

## Success Criteria *(mandatory)*

- **SC-001**: In the Almost Yours acceptance scenario, a shot with HER and HIM carries references of both characters (4 of 4 references listed), proven by an automated test on real shot and character rows.
- **SC-002**: 0 origami motion prompts contain breathing, blinking, hair or fabric instructions across a full drafted board.
- **SC-003**: Changing HER's palette in an approved Bible reports 100% of HER's shots with active plates as affected and 0 of the shots she is not in, when only her character section changes.
- **SC-004**: All existing engine tests pass unchanged except where this spec changes behaviour on purpose (origami motion text, plate request report keys added).
- **SC-005**: A project created before this feature opens in the Studio and CLI, drafts, requests plates and renders exactly as before.
- **SC-006**: A compact-profile project reaches plates with no more approval steps than before.
- **SC-007**: In the Almost Yours fixture the washi paper line is in the plates of HER's shots and not in the empty gallery; the display case is in the two shots that name or list it; the paper boat is in no plate until a shot selects it.
- **SC-008**: Approving a revised Bible leaves every authored prompt byte for byte unchanged and lists each one.

## Assumptions

- The creator is the only approver; agents propose and review.
- Video backends (LTX-2.3, LTX-2.5) take no negative prompt, so forbidden movement is enforced by leaving it out of the positive prompt and by warnings, not by the model.
- Visual continuity is reviewed by people and agents looking at frames; no computer-vision continuity check is built.
- The Museum of Almosts is an acceptance fixture, not built-in behaviour.

## Out of Scope

Cross-film taste memory; autonomous changes to approved direction; automatic regeneration of affected assets; a computer-vision continuity model; a continuity-supervisor skill; new paid providers; hosted services; licensing changes.
