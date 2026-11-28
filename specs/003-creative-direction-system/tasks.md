---
description: "Task list for Creative Direction and Visual Intelligence"
---

# Tasks: Creative Direction and Visual Intelligence

**Input**: Design documents from `/specs/003-creative-direction-system/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: required by the brief. pytest with `MB_BACKEND=stub`, ruff, Vitest, Playwright, `tsc --noEmit`.

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Foundation (US1)

- [ ] T001 [US1] Migration `engine/src/motionboard/db/migrations/0003_creative_direction.sql`: `art_direction`, `character_reference` (with copy of legacy references), `critique`, `shot.creative`, `plate_request.refs`, `plate_request.refs_dropped`
- [ ] T002 [US1] `migrate(conn, target)` in `engine/src/motionboard/db/connection.py` for migration tests
- [ ] T003 [P] [US1] Bible schema (package copy of `contracts/art-direction.schema.json`), small validator, profiles, vague-word and cast warnings, Markdown renderer in `engine/src/motionboard/direction/bible.py`
- [ ] T004 [P] [US1] Section diff and affected shots and assets in `engine/src/motionboard/direction/impact.py`
- [ ] T005 [US1] Versions: draft, check, submit, reject, approve, history, show, export, motif progression in `engine/src/motionboard/direction/service.py`
- [ ] T006 [US1] `mb art ...` and `mb approve --stage art_direction` in `engine/src/motionboard/cmd_direction.py` and `cmd_storyboard.py`
- [ ] T007 [US1] Plates gate rule for full Bibles in `storyboard/board.py` and `plates/service.py`
- [ ] T008 [US1] Export and import of Bible versions, references, creative fields, critiques in `storyboard/io_json.py`
- [ ] T009 [P] [US1] Tests: `tests/unit/test_bible.py`, `test_direction_cli.py`, `test_migration_003.py`

## Phase 2: Production designer (US4)

- [ ] T010 [US4] `skills/mb-production-designer/SKILL.md`
- [ ] T011 [US4] Plugin manifest description and version, `scripts/package-plugin.sh` run, `dist/motionboard.plugin`

## Phase 3: Crew integration (US4)

- [ ] T012 [US4] Director: concept defence, designer brief, Bible approval routing, visual journey, disagreements, reject beautiful-but-wrong in `skills/mb-director/SKILL.md`
- [ ] T013 [US4] Cinematographer: read Bible and prompts first, camera rules, design and grammar, first frame vs movement, continuity in `skills/mb-cinematographer/SKILL.md`
- [ ] T014 [US4] Editor: visual progression, motif tracking, payoff, repetition, transitions, continuity, critique recording in `skills/mb-editor/SKILL.md`
- [ ] T015 [US4] Emotional editor: subtext vs illustration, metaphor fit, symbolism decorative or developing, show too much or too little, believable progression in `skills/mb-emotion-editor/SKILL.md`
- [ ] T016 [US4] Writer and composer handoff mentions; check every handoff for contradictions

## Phase 4: Character and motion intelligence (US2, US3, US5)

- [ ] T017 [US2] References service and `mb character ref` in `storyboard/characters.py`, `cmd_characters.py`; legacy `reference_image` mirror
- [ ] T018 [US2] `Reference`, capacity and strategy selection in `plates/adapter.py`; capacity and sending in `manual.py`, `handoff.py`, `command.py` (`{refs}`), `http_api.py` (`{ref_b64}`, `refs_field`)
- [ ] T019 [US2] Gather every cast member's references; store sent and dropped in `plates/service.py`; `--reference-strategy`; adapter listing capacity in `cmd_clips.py`
- [ ] T020 [US3] Motion grammar: `Look.motion`, defaults, merge, forbidden check in `direction/grammar.py`, `storyboard/templates.py`; origami grammar in `looks/origami.yaml`
- [ ] T021 [US3] Separate plate, motion, continuity, negative composition in `storyboard/compose.py`; wire draft, board, characters, plates negative
- [ ] T022 [US5] Shot creative fields in `storyboard/board.py`; shots file `creative`; `mb shot prompts`; grammar warnings in sheet and approve
- [ ] T023 [US5] Critiques in `direction/critique.py`; `mb critique`; open critiques in approval reports
- [ ] T024 [P] Tests: `test_references.py`, `test_adapter_capacity.py`, `test_grammar.py`, `test_compose.py`, `test_critique.py`; existing tests pass

## Phase 5: Studio (US6)

- [ ] T025 [US6] Drizzle mirror and `MIN_SCHEMA` in `studio/src/lib/schema.ts`, `config.ts`; read model in `data.ts`; types
- [ ] T026 [US6] Bridge actions in `studio/src/lib/mb.ts`; PATCH shot creative fields in `app/api/shots/[id]/route.ts`
- [ ] T027 [US6] View-model helpers in `studio/src/lib/art.ts`
- [ ] T028 [US6] Art view `studio/src/components/art/ArtDirection.tsx`; view switch in `BoardView.tsx`
- [ ] T029 [US6] Shot creative context and critiques in `SidePanel.tsx`; direction-changed marker in `ShotCard.tsx`; gate reason in `GateBar.tsx`
- [ ] T030 [P] [US6] Tests: `studio/tests/unit/art.test.ts`, bridge whitelist cases, `studio/tests/e2e/g-art-direction.spec.ts`

## Phase 6: Acceptance and delivery

- [ ] T031 Fixtures `engine/tests/fixtures/almost-yours/` and `engine/tests/acceptance/test_almost_yours.py` (14 requirements)
- [ ] T032 Docs: README (crew, Art Direction), `docs/art-direction.md` (guide and migration notes), `docs/first-video.md`, 001 data-model pointer
- [ ] T033 Full runs: pytest, ruff, vitest, tsc, Playwright; record results
- [ ] T034 Diff review, migration on a copy of a real database, secret and media scan; push branch; draft PR
