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
