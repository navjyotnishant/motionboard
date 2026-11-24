# Contract: Plate adapter

```python
class PlateAdapter(Protocol):
    name: str
    kind: Literal["manual", "command", "http", "handoff"]
    def estimate_cost(self, n_images: int) -> float: ...
    def request(self, req: PlateRequest) -> PlateResult | Pending: ...
```

`PlateRequest`: `shot_id, prompt, negative, width, height, reference_image | None, seed`.
`PlateResult`: `path, source, cost_usd`. `Pending` means the request row stays `pending` until fulfilled.

## Kinds

| kind | config | behaviour |
|---|---|---|
| manual | `{ "watch_folder": "plates/inbox" }` | Files named `shot-03.png` in the folder are attached to shot 3; also Studio upload and `mb plate fulfil`. |
| command | `{ "cmd": ["python", "gen.py", "--prompt", "{prompt}", "--out", "{out}", "--size", "{w}x{h}"], "cost_per_image_usd": 0 }` | Runs under the guard; `{ref}` placeholder optional. |
| http | `{ "url": "...", "method": "POST", "body": {...templated...}, "image_field": "data[0].b64_json", "key_file": "~/.x/key" or "key_env": "NAME", "cost_per_image_usd": 0.01 }` | Key loaded at call time, sent as bearer header, never logged. |
| handoff | `{ "hint": "Use the Muse image tool" }` | Creates `plate_request` rows. The `mb-clips` skill lists pending requests, generates images with the creator's MCP tool, saves them, then calls `mb plate fulfil`. |

Rules: cost shown and confirmed before any paid request; requests for object only shots add the no figure negative; character shots pass the character reference image when the adapter supports it.
