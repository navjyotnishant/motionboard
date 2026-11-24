# Contract: `mb` command line

All commands accept `--json` and then print exactly one JSON object on stdout:

```json
{ "ok": true, "command": "mb plates", "project": "01J...", "data": {}, "verified": ["..."], "not_verified": ["..."], "next": "mb clips --project 01J..." }
```

On failure: `ok: false`, `error: {code, message, hint}`, exit code non zero. Codes: `GATE_NOT_APPROVED`, `FIT_REFUSED`, `GUARD_STOPPED`, `COST_NOT_CONFIRMED`, `MISSING_TOOL`, `MISSING_MODEL`, `INVALID_INPUT`, `NOT_FOUND`.

| Command | Purpose | Key flags |
|---|---|---|
| `mb setup` | Machine, tools, models report; no downloads | `--fix-plan` prints exact install and download steps |
| `mb db migrate` | Create or upgrade schema | |
| `mb project new` | Create project folder and row | `--title --song --lyrics-file --idea --aspect 9:16|16:9 --look stylized|realistic` |
| `mb analyze` | Segment, tempo, beats, lines, waveform peaks | `--project --start --end` (optional; else auto pick) |
| `mb concepts add` | Store concepts written by Claude | `--project --file concepts.json` |
| `mb draft` | Build shots from chosen concept or template | `--project --concept ID | --template NAME` |
| `mb shot set` | Edit one shot field | `--shot --field --value` |
| `mb sheet` | Contact sheet image of storyboard or plates | `--project --kind storyboard|plates|clips` |
| `mb approve` | Approve or revoke a gate | `--project --stage storyboard|plates|clips|final [--revoke]` |
| `mb plates` | Request plates for shots needing them | `--project [--shots 3,7] --adapter NAME [--confirm-cost]` |
| `mb plate fulfil` | Attach an image to a pending handoff request | `--request ID --file PATH` |
| `mb fit` | Dry run fit check | `--project | --backend --width --height --frames` |
| `mb clips` | Queue clip jobs for approved plates | `--project [--shots] [--redo] [--preset safe|balanced|max]` |
| `mb worker` | Run queue until empty or stopped | `--detach` |
| `mb queue` | Show, pause, resume, stop, reorder | `--project --pause|--resume|--stop|--move JOB:POS` |
| `mb finish` | Assemble, overlay, grade, end card, cover, metadata | `--project` |
| `mb deliver` | Copy delivery to a folder with post time | `--project --to PATH --post-time ISO` |
| `mb export` / `mb import` | Project JSON (see storyboard.schema.json) | `--project --out` / `--file` |
| `mb guard` | List, set, create presets | `--set NAME | --create NAME --start --kill --swap` |
| `mb adapter` | List, add, test plate adapters | `--add --kind --config JSON | --test NAME` |

Rules:
- `mb plates` with a paid adapter and no `--confirm-cost` returns `COST_NOT_CONFIRMED` with the estimate in `data.est_cost_usd`.
- `mb clips` returns `GATE_NOT_APPROVED` unless storyboard and plates gates are approved.
- `mb clips` runs `mb fit` per distinct setting first; refusal lists suggestions.
- No command prints values read from `key_file` or `key_env`.
