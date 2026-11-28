---
description: "Task list for Creative Direction and Visual Intelligence"
---

# Tasks: Creative Direction and Visual Intelligence

**Input**: Design documents from `/specs/003-creative-direction-system/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: required by the brief. pytest with `MB_BACKEND=stub`, ruff, Vitest, Playwright, `tsc --noEmit`.

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Foundation (US1)

- [x] T001 [US1] Migration `engine/src/motionboard/db/migrations/0003_creative_direction.sql`: `art_direction`, `character_reference` (with copy of legacy references), `critique`, `shot.creative`, `plate_request.refs`, `plate_request.refs_dropped`
- [x] T002 [US1] `migrate(conn, target)` in `engine/src/motionboard/db/connection.py` for migration tests
- [x] T003 [P] [US1] Bible schema (package copy of `contracts/art-direction.schema.json`), small validator, profiles, vague-word and cast warnings, Markdown renderer in `engine/src/motionboard/direction/bible.py`
- [x] T004 [P] [US1] Section diff and affected shots and assets in `engine/src/motionboard/direction/impact.py`
- [x] T005 [US1] Versions: draft, check, submit, reject, approve, history, show, export, motif progression in `engine/src/motionboard/direction/service.py`
- [x] T006 [US1] `mb art ...` and `mb approve --stage art_direction` in `engine/src/motionboard/cmd_direction.py` and `cmd_storyboard.py`
- [x] T007 [US1] Plates gate rule for full Bibles in `storyboard/board.py` and `plates/service.py`
- [x] T008 [US1] Export and import of Bible versions, references, creative fields, critiques in `storyboard/io_json.py`
- [x] T009 [P] [US1] Tests: `tests/unit/test_bible.py`, `test_direction_cli.py`, `test_migration_003.py`

## Phase 2: Production designer (US4)

- [x] T010 [US4] `skills/mb-production-designer/SKILL.md`
- [x] T011 [US4] Plugin manifest description and version, `scripts/package-plugin.sh` run, `dist/motionboard.plugin`

## Phase 3: Crew integration (US4)

- [x] T012 [US4] Director: concept defence, designer brief, Bible approval routing, visual journey, disagreements, reject beautiful-but-wrong in `skills/mb-director/SKILL.md`
- [x] T013 [US4] Cinematographer: read Bible and prompts first, camera rules, design and grammar, first frame vs movement, continuity in `skills/mb-cinematographer/SKILL.md`
- [x] T014 [US4] Editor: visual progression, motif tracking, payoff, repetition, transitions, continuity, critique recording in `skills/mb-editor/SKILL.md`
- [x] T015 [US4] Emotional editor: subtext vs illustration, metaphor fit, symbolism decorative or developing, show too much or too little, believable progression in `skills/mb-emotion-editor/SKILL.md`
- [x] T016 [US4] Writer and composer handoff mentions; check every handoff for contradictions

## Phase 4: Character and motion intelligence (US2, US3, US5)

- [x] T017 [US2] References service and `mb character ref` in `storyboard/characters.py`, `cmd_characters.py`; legacy `reference_image` mirror
- [x] T018 [US2] `Reference`, capacity and strategy selection in `plates/adapter.py`; capacity and sending in `manual.py`, `handoff.py`, `command.py` (`{refs}`), `http_api.py` (`{ref_b64}`, `refs_field`)
- [x] T019 [US2] Gather every cast member's references; store sent and dropped in `plates/service.py`; `--reference-strategy`; adapter listing capacity in `cmd_clips.py`
- [x] T020 [US3] Motion grammar: `Look.motion`, defaults, merge, forbidden check in `direction/grammar.py`, `storyboard/templates.py`; origami grammar in `looks/origami.yaml`
- [x] T021 [US3] Separate plate, motion, continuity, negative composition in `storyboard/compose.py`; wire draft, board, characters, plates negative
- [x] T022 [US5] Shot creative fields in `storyboard/board.py`; shots file `creative`; `mb shot prompts`; grammar warnings in sheet and approve
- [x] T023 [US5] Critiques in `direction/critique.py`; `mb critique`; open critiques in approval reports
- [x] T024 [P] Tests: `test_references.py`, `test_adapter_capacity.py`, `test_grammar.py`, `test_compose.py`, `test_critique.py`; existing tests pass

## Phase 5: Studio (US6)

- [x] T025 [US6] Drizzle mirror and `MIN_SCHEMA` in `studio/src/lib/schema.ts`, `config.ts`; read model in `data.ts`; types
- [x] T026 [US6] Bridge actions in `studio/src/lib/mb.ts`; PATCH shot creative fields in `app/api/shots/[id]/route.ts`
- [x] T027 [US6] View-model helpers in `studio/src/lib/art.ts`
- [x] T028 [US6] Art view `studio/src/components/art/ArtDirection.tsx`; view switch in `BoardView.tsx`
- [x] T029 [US6] Shot creative context and critiques in `SidePanel.tsx`; direction-changed marker in `ShotCard.tsx`; gate reason in `GateBar.tsx`
- [x] T030 [P] [US6] Tests: `studio/tests/unit/art.test.ts`, bridge whitelist cases, `studio/tests/e2e/g-art-direction.spec.ts`

## Phase 6: Acceptance and delivery

- [x] T031 Fixtures `engine/tests/fixtures/almost-yours/` and `engine/tests/acceptance/test_almost_yours.py` (14 requirements)
- [x] T032 Docs: README (crew, Art Direction), `docs/art-direction.md` (guide and migration notes), `docs/first-video.md`, 001 data-model pointer
- [x] T033 Full runs: pytest, ruff, vitest, tsc, Playwright; record results (ruff clean on src and tests; pytest 138 passed; acceptance 2 passed; vitest 18; tsc clean; studio build OK; Playwright 8)
- [x] T034 Diff review, migration on a copy of a real database, secret and media scan; push branch; draft PR (real DB copy: schema 2 to 3, 4 references carried with identical paths, 97 shots get empty creative)

## Phase 7: Corrective pass (review of PR #1)

- [x] T035 Shot associations for Bible materials and objects in `engine/src/motionboard/direction/assoc.py`; `scope` in the Bible schema; `materials` and `objects` in shot creative context (`storyboard/draft.py`, `storyboard/board.py`)
- [x] T036 Plate composition includes the shot's object and material lines, without repeating the look (`storyboard/compose.py`); `mb shot prompts` reports them with the reason
- [x] T037 Impact by entry for materials and objects (`direction/impact.py`); research R4 table updated
- [x] T038 Effective grammar merges character forbidden movement, material behaviour and invariants (`direction/grammar.py`); Bible lines that name forbidden movement are warned
- [x] T039 Conflict detection `direction/conflicts.py`; reported by `mb draft`, `mb shot set`, `mb shot prompts`, `mb sheet`, storyboard approval, `mb clips`
- [x] T040 `mb plates` stops with `DIRECTION_CONFLICT` before any request; `--accept-conflicts` (`plates/service.py`, `cmd_clips.py`, `report.py`)
- [x] T041 Migration `0004_prompt_overrides.sql`; baselines and authored flags in `compose.recompose`, `compose.settle`, `board.set_field`, `draft.draft`; export and import
- [x] T042 Approval reports overrides and their conflicts (`direction/service.py`, `cmd_direction.py`); `mb shot override list|keep|clear`
- [x] T043 Full-profile character designs are blocking, with `exceptions.characters` (`direction/bible.py`, `direction/service.py`, schema, Markdown view)
- [x] T044 Reference metadata for command and HTTP adapters (`plates/adapter.py`, `plates/command.py`, `plates/http_api.py`), validated on add
- [x] T045 Studio: schema 4 mirror, read model, bridge actions, authored marker and Use generated, Objects and Materials fields; vitest and Playwright cases
- [x] T046 Regression tests `engine/tests/unit/test_corrections_003.py` (15 tests) on the Almost Yours Bible; fixtures updated (washi prompt line, shot 2 lists the display case)
- [x] T047 Spec, plan, research, data model, contracts, docs and skills updated; plugin 0.6.1 rebuilt
- [x] T048 Full runs recorded: ruff clean on src and tests; pytest 153 passed (2 acceptance); vitest 21; tsc clean; Studio build OK; Playwright 8. Migration 0003 and 0004 on a copy of a real schema-2 database: schema 4, 97 shots keep their prompts; settling one project adopted 73 of 74 motion prompts and 0 plate prompts as authored. No render was run; visual validation is not part of this work.
