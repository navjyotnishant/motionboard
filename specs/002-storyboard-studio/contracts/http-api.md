# Contract: Studio local HTTP API

Base `http://127.0.0.1:4317`. Mutating routes require the session cookie and a same origin `Origin` header; otherwise 403.

| Method | Path | Body / query | Returns |
|---|---|---|---|
| GET | `/api/events?since=SEQ` | | SSE stream of `{seq, entity, entity_id, kind, actor}` |
| GET | `/api/media?path=ABS` | Range header | file bytes; 403 outside project folders |
| PATCH | `/api/shots/:id` | `{updated_at, fields:{...}}` (zod validated) | updated shot or 409 |
| PATCH | `/api/characters/:id` | same pattern | |
| PATCH | `/api/projects/:id` | same pattern | |
| POST | `/api/notes` | `{asset_version_id, text}` | note |
| POST | `/api/mb` | `{action, args}` | the `mb` JSON report |
| POST | `/api/brainstorm` | `{project_id, answers:{mood, world, characters, look, aspect}}` | `{concepts:[...]}` or `{error:"CLAUDE_MISSING"}` |

`/api/mb` actions whitelist: `draft, approve, revoke, review, plates, plate_upload, clips, queue_pause, queue_resume, queue_stop, queue_move, guard_set, guard_create, adapter_add, adapter_test, export_json, export_pdf, export_html, import_json, template_save, finish`. Unknown action: 400. Paid `plates` without `confirm_cost: true`: passes through `COST_NOT_CONFIRMED` for the UI to show the estimate.
