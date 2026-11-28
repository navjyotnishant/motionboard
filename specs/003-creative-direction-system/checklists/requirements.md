# Specification Quality Checklist: Creative Direction and Visual Intelligence

**Purpose**: Validate the spec and plan before and after implementation.
**Feature**: [spec.md](../spec.md)

## Content quality

- [x] Each user story is independently testable and states why it has its priority
- [x] Requirements say what, not which library; implementation detail lives in plan, research and data-model
- [x] No open [NEEDS CLARIFICATION] markers (the brief answered scope; remaining choices recorded in research.md)
- [x] Out of scope matches the brief

## Requirement completeness

- [x] Every brief workstream (A to H) maps to requirements: A FR-001..008, B FR-022, C FR-022, D FR-009..013, E FR-014..018, F FR-019, G FR-020..021, H FR-023..024
- [x] Every one of the 14 brief acceptance requirements maps to a test in `tests/acceptance/test_almost_yours.py`
- [x] Backward compatibility stated (FR-025, FR-026, SC-004, SC-005)
- [x] Edge cases listed (no Bible, missing files, open drafts, word limit, old exports)

## Constitution

- [x] I Storyboard First: storyboard gate unchanged
- [x] V Review Gates: Bible approval explicit and versioned; no fifth stage (research R2)
- [x] VI Honest Verification: sent and dropped references, impact, open critiques, model limits reported
- [x] VII One database, Markdown generated, JSON export carries new data
- [x] VIII Studio writes only through `mb`
- [x] No constitution amendment needed

## Review notes

- Spec reviewed against the constitution and repository architecture on 2026-11-27 before planning.
- Plan reviewed against data-model and contracts before tasks.
- Decision with the most product impact: the HTTP adapter now refuses shots with references unless configured (R8). Documented in the PR as a deliberate change.
