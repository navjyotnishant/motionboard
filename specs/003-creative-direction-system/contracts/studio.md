# Studio contract: art direction (extends 002 contracts)

## Read model (`GET /api/projects/:id`)

`board()` gains:

- `artDirection`: `{ approved: Version | null, pending: Version | null, versions: VersionSummary[], required: boolean }` where `Version = {id, version, profile, status, body, note, impact, approved_at, approved_via, created_at}`. `required` is true when the latest version is full profile.
- `characters[].references`: `[{id, path, purpose, description, is_primary, ord}]`.
- `shots[].creative`: parsed JSON (`{}` when unset).
- `critiques`: `[{id, stage, role, verdict, summary, findings, checked, not_checked, created_at, resolved_at}]`.

## Bridge actions (`POST /api/mb`), all argv-validated

| action | runs |
|---|---|
| `art_submit` `{project}` | `mb art submit` |
| `art_approve` `{project}` | `mb art approve --via studio` |
| `art_reject` `{project, note}` | `mb art reject --note` |
| `art_impact` `{project}` | `mb art impact` |
| `ref_add` `{project, name, file, purpose?, description?, primary?}` | `mb character ref add` |
| `ref_remove` `{project, id}` | `mb character ref remove` |
| `ref_primary` `{project, id}` | `mb character ref primary` |
| `critique_resolve` `{project, id}` | `mb critique resolve` |
| `shot_set` | field enum gains `intent`, `audience`, `metaphor`, `continuity`, `motifs` |

`approve` and `revoke` keep their four stages; the Art view uses `art_approve`.

## UI

- Top bar view switch: Grid, Story, **Art**.
- Art view: status pill (Draft, Awaiting review, Approved vN), palette swatches with names and roles, identity and world text, characters with reference thumbnails (purpose label, primary star, remove, make primary, add by file path), materials and objects, motif progression grid (motif rows, shot columns, state text on hover), motion allowed and forbidden lists, constraints. When a revision is pending: a band with the changed sections, affected shots (click to open the shot), Approve and Send back.
- Gate bar: plates disabled with "approve the art direction first" when `required` and nothing approved.
- Shot panel: a collapsed "Creative context" section (intent, audience, metaphor, motifs, continuity) and the shot's open critique findings; nothing shown when empty except the collapsed header.
- Shot card: small "direction changed" marker when the shot is in the approved version's impact and its active plate predates that approval.

## Corrective pass

- Minimum schema 4. Shots in the read model gain `plate_authored`, `motion_authored` (booleans), `plate_base`, `motion_base`; `creative` may carry `materials` and `objects`.
- Bridge actions: `override_clear {project, shot, part}`, `override_keep {project, shot, part}`; `shot_set` accepts fields `materials` and `objects`. PATCH `/api/shots/:id` accepts `materials` and `objects`.
- Shot panel: under a prompt the creator wrote, "Written by you, the engine will not rewrite it" with **Use generated** (clears the override). Creative context gains Objects and Materials as comma lists.
- Conflicts and the keep decision are shown by the CLI reports; the Studio does not list conflicts yet.
