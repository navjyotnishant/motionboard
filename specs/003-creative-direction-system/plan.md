# Implementation Plan: Creative Direction and Visual Intelligence

**Branch**: `003-creative-direction-system` | **Date**: 2026-11-27 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-creative-direction-system/spec.md`

**Depends on**: 001 (engine, schema, `mb`), 002 (Studio), the crew skills (writer, emotion editor, composer, director, cinematographer, editor).

## Summary

Add the film's visual identity as a versioned, approvable Art Direction Bible in the shared database; make plates carry every character's references with honest adapter capacity; replace generic human motion with per-look motion grammar and separate plate, motion and continuity composition; let shots carry optional creative intent and let reviews carry structured findings; show it all in the Studio; and give the crew a production designer plus updated director, cinematographer, editor and emotional editor skills.

## Technical Context

**Language/Version**: Python 3.12 (engine), TypeScript 5 on Node 20+ (Studio).

**Primary Dependencies**: existing only: typer, PyYAML, Pillow (engine); Next.js 16, React 19, better-sqlite3, Drizzle, zod (Studio). No new dependencies.

**Storage**: the shared SQLite file; migration `0003_creative_direction.sql`; Markdown view written to the project folder.

**Testing**: pytest (unit, integration, acceptance) with `MB_BACKEND=stub`; ruff; Vitest (Studio lib); Playwright (Studio flows on the stub e2e server); `tsc --noEmit`.

**Target Platform**: Apple Silicon Mac, local only.

**Project Type**: CLI engine plus local web app plus Claude skills.

**Performance Goals**: `mb art approve` and impact on an 80-shot project under 1 s; Studio Art view interactive under 2 s on 80 shots.

**Constraints**: no network, no new providers, no automatic regeneration; existing CLI JSON shapes only gain keys.

**Scale/Scope**: one creator, projects up to about 100 shots, a handful of characters with up to about 10 references each.

## Constitution Check

| Principle | How this plan complies | Status |
|---|---|---|
| I. Storyboard First | Storyboard gate unchanged; Bible changes only re-compose prompts and report affected shots, the creator chooses what to redo. | Pass |
| II. Local First | No new services; HTTP adapter behaviour stays opt-in; cost confirmation untouched. | Pass |
| III. Never Crash | No new heavy jobs; command adapters still run under the guard. | Pass |
| IV. No Weights, Licences | No weights; synthetic people flag unchanged. | Pass |
| V. Review Gates | Bible approval is explicit and versioned; full-profile films need it before plates; it is a review inside the existing storyboard to plates boundary, not a fifth stage (research R2). | Pass, no amendment |
| VI. Honest Verification | Reports list references sent and dropped, affected shots, open critiques, and state that forbidden movement is not enforced by the model and continuity is not checked by computer vision. | Pass |
| VII. Simple and Portable | One database; Markdown is a generated view; JSON export carries the new data; looks stay YAML. | Pass |
| VIII. One Source, Two Ways In | Studio reads the same rows and writes only through whitelisted `mb` actions; Art view follows the dark imagery-first design. | Pass |

Post-design re-check: Pass. No constitution amendment.

## Project Structure

### Documentation (this feature)

```text
specs/003-creative-direction-system/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md
│   ├── art-direction.schema.json
│   ├── plate-adapter-references.md
│   └── studio.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
engine/src/motionboard/
├── db/migrations/0003_creative_direction.sql   # new tables and columns, reference migration
├── db/connection.py                            # migrate(conn, target) for migration tests
├── direction/                                  # new package
│   ├── bible.py        # schema, validation, profiles, Markdown rendering
│   ├── service.py      # versions: draft, submit, reject, approve, history, impact, export
│   ├── impact.py       # section diff and affected shots and assets
│   ├── grammar.py      # motion grammar: defaults, look and Bible merge, forbidden check
│   └── critique.py     # structured reviews
├── storyboard/compose.py      # plate, motion, continuity, negative composition; DB recompose
├── storyboard/draft.py        # uses compose; keeps plate_prompt/motion_prompt wrappers
├── storyboard/board.py        # creative fields, gate rule for art direction, grammar warnings
├── storyboard/characters.py   # references: add, list, remove, primary; legacy mirror
├── storyboard/io_json.py      # export and import of the new data
├── storyboard/templates.py    # Look.motion
├── plates/adapter.py          # Reference, capacity, strategy selection
├── plates/{manual,handoff,command,http_api}.py   # capacity and sending
├── plates/service.py          # gather references for every cast member
├── cmd_direction.py           # mb art ..., mb critique ...
├── cmd_characters.py          # mb character ref ...
├── cmd_storyboard.py          # mb shot prompts; approve --stage art_direction
└── cmd_clips.py               # --reference-strategy; adapter capacity in listing

looks/origami.yaml             # motion grammar

skills/mb-production-designer/SKILL.md          # new
skills/{mb-director,mb-cinematographer,mb-editor,mb-emotion-editor}/SKILL.md   # enhanced

studio/src/lib/{schema.ts,data.ts,mb.ts,art.ts,config.ts}
studio/src/components/art/ArtDirection.tsx      # new Art view
studio/src/components/board/{BoardView,SidePanel,GateBar,ShotCard}.tsx
studio/tests/unit/art.test.ts
studio/tests/e2e/g-art-direction.spec.ts

engine/tests/unit/test_{bible,direction_cli,references,adapter_capacity,grammar,compose,critique,migration_003}.py
engine/tests/acceptance/test_almost_yours.py
engine/tests/fixtures/almost-yours/{bible.json,bible-v2.json,shots.json,critique.json}
```

**Structure Decision**: a new `direction` package keeps Bible, impact, grammar and critique logic in one place, outside the already large `storyboard/board.py`. Prompt composition moves to `storyboard/compose.py` so plate, motion and continuity are separate functions; `draft.plate_prompt` and `draft.motion_prompt` remain as wrappers for existing callers and tests.

## Phases

1. Foundation: migration 0003, Bible model and validation, versions and approval, impact, Markdown view, `mb art`, export and import, migration tests.
2. Production designer skill and packaging.
3. Director, cinematographer, editor, emotion editor updates; handoffs aligned.
4. References and adapter capacity; motion grammar; composition; shot creative context; critiques.
5. Studio: schema mirror, read model, Art view, shot context, references, gate rule, tests.
6. Almost Yours acceptance test, docs, full test runs, diff review, draft PR.

7. Corrective pass after review (FR-027 to FR-036): shot associations for materials and objects (`direction/assoc.py`) in composition and impact; conflict detection (`direction/conflicts.py`) with character rules merged into the grammar and a plate-time stop; migration 0004 with generated baselines apart from authored overrides, settle for older shots, `mb shot override`; blocking character designs for full Bibles with recorded exceptions; reference metadata for command and HTTP adapters; Studio marker and clear action; regression tests `engine/tests/unit/test_corrections_003.py`.

Commits stay grouped by phase.

## Risks

- **Prompt churn**: resolved in phase 7. Recomposition regenerates baselines and never rewrites an authored override; overrides are reported with conflicts. New risk: on databases from older engines most motion prompts are adopted as authored when first settled and stop following the direction until cleared (research R16); reported, one command to clear.
- **A new stop before plates** (`DIRECTION_CONFLICT`): projects whose actions already ask for forbidden movement must fix them or pass `--accept-conflicts`.
- **HTTP adapter now errors** for shots with references: a deliberate change from silent drops; the hint names `reference_strategy: none` to keep the old behaviour knowingly.
- **Word limits**: continuity clause competes with the 200-word video limit. Mitigation: continuity sits before scene and style; the style tail is trimmed first; tested.

## Complexity Tracking

| Addition | Why needed | Simpler alternative rejected because |
|---|---|---|
| Version table instead of one Bible row | Approved and pending must coexist; history required | One row loses the approved version during review |
| `critique` table | Reviews must persist and point at shots for the Studio | Free text in `emotion.md` cannot be shown per shot or listed as open |
