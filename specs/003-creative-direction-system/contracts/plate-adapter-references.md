# Plate adapter contract: references (extends 001 contracts/plate-adapter.md)

## Request

`PlateRequest` gains `references: list[Reference]`, where `Reference = {character, path, purpose, primary, description}`. Order: characters by name, then each character's primary first, then by `ord`. `reference_image` remains and equals the first reference's path (or `None`).

## Capacity

Every adapter exposes `reference_capacity() -> int | None` (`None` means unlimited).

| kind | capacity | how references are used |
|---|---|---|
| manual | unlimited | Listed in the report and in `mb plate requests` for the creator; the adapter itself only waits for a file. |
| handoff | unlimited | Listed in `mb plate requests`; the agent passes each to the image tool it uses. |
| command | `{refs}` as a whole argv element: unlimited, expands to one argv entry per path. Any element containing `{ref}`: 1. Neither: 0. | |
| http | `refs_field` in config: unlimited; the request body gets a list at that dotted path, encoded per `refs_encoding` (`base64` default, `data_url`, `path`). `{ref_b64}` or `{ref}` in the body template: 1. Neither: 0. | |

## Strategy

`reference_strategy` in the adapter config, overridable per run with `mb plates --reference-strategy`:

| strategy | behaviour |
|---|---|
| `strict` (default) | More references than capacity: the shot fails with `INVALID_INPUT`, hint names the other strategies. |
| `primary` | Keep each character's primary only; still over capacity: fail as strict. |
| `first` | Keep the first N in request order. |
| `none` | Send none. |

Missing files are never sent and are reported with reason `file missing`, whatever the strategy. Everything not sent is stored in `plate_request.refs_dropped` with a reason and returned in the report. An adapter never claims a reference it did not use.

## Reference identity (optional)

Each reference sent has `index` (0-based, in the order sent), `character`, `purpose`, `primary`, `path`, `description`.

| Kind | Setting | Effect |
|---|---|---|
| command | `"refs_format": "{character}:{purpose}={path}"` | shapes each argument that `{refs}` expands to (default `{path}`) |
| command | `{refs_manifest}` inside an element | path of `<out>.refs.json`: `{"request", "shot", "references": [...]}`; takes every reference |
| command | `{refs_json}` inside an element | the reference list as inline JSON; takes every reference |
| http | `"refs_meta": {"image": "image", "subject": "character", "role": "purpose"}` | each `refs_field` entry becomes an object; keys are the API's field names, values one of `image`, `index`, `character`, `purpose`, `primary`, `path`, `description` |
| http | `"refs_manifest_field": "input.reference_info"` | the metadata list (no image data) at that path, parallel to `refs_field` |
| manual, handoff | none needed | `mb plate requests` already lists each reference with character, purpose and primary |

`mb adapter --add` rejects an unknown field, `refs_meta` without `refs_field`, and `refs_format` without a `{refs}` element. Configurations without these settings behave exactly as before.
