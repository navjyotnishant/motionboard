# Plate adapters

A plate is the still image a clip starts from. Motionboard does not choose your image source. An adapter connects one.

```bash
mb adapter --add <name> --kind <manual|command|http|handoff> --config '<json>' --cost <usd per image>
mb adapter --list
```

| Kind | Use it for | Config |
|---|---|---|
| `manual` | your own files, any app | `{"watch_folder": "plates/inbox"}`; drop `shot-01.png` and so on |
| `command` | a local image model with a CLI | `{"cmd": ["python", "gen.py", "--prompt", "{prompt}", "--out", "{out}", "--size", "{w}x{h}"], "cwd": "~/tools/sd"}` |
| `http` | a JSON image API | `{"url": "...", "body": {"prompt": "{prompt}", "size": "{w}x{h}"}, "image_field": "data.0.b64_json", "key_file": "~/.keys/api"}` |
| `handoff` | an MCP image tool in Claude (for example Muse) | `{"hint": "Muse"}`; Claude makes each image and runs `mb plate fulfil` |

Placeholders: `{prompt} {negative} {out} {w} {h} {ref} {seed}`. `{ref}` is the character reference image for shots that have one.

## Keys

Keys are never stored in the database. Give a `key_file` path or a `key_env` variable name. The engine reads the key when it calls the API and sends it as a bearer header. Config that looks like it holds a key is refused.

## Cost

An adapter with `--cost` above zero is paid. `mb plates` refuses with `COST_NOT_CONFIRMED` and prints the estimate until you run it again with `--confirm-cost`. Nothing is sent before that.

## Command adapters and memory

Command adapters run under the active memory guard, like clip renders.

## References

A plate request carries every reference image of every character in the shot: characters by name, each one's primary first. A shot with HER and HIM, two references each, carries four. `mb plate requests` lists them with character, purpose and primary flag, and `mb adapter --list` shows how many each adapter can use.

| Kind | Reference capacity | How |
|---|---|---|
| manual | all | Listed for you; you make the image and drop it in the inbox |
| handoff | all | Listed for the agent that makes the image with an MCP tool |
| command | all with `{refs}` as a whole argument (one argument per path); one with `{ref}`; none otherwise | `"cmd": ["python", "gen.py", "--out", "{out}", "--refs", "{refs}"]` |
| http | all with `"refs_field": "input.images"` (a list at that path, `"refs_encoding": "base64"`, `"data_url"` or `"path"`); one with `{ref_b64}` or `{ref}` in the body; none otherwise | `"body": {"prompt": "{prompt}", "image": "{ref_b64}"}` |

When a shot has more references than the adapter can use, its request stops with a message naming the characters and the fix. Nothing is dropped silently. Choose what to send with `reference_strategy` in the adapter config, or per run:

```bash
mb plates -p <id> --adapter one-ref --reference-strategy primary   # each character's primary only
mb plates -p <id> --adapter one-ref --reference-strategy first     # the first N, in order
mb plates -p <id> --adapter text-only --reference-strategy none    # send none
```

Whatever is not sent (including files missing on disk) is stored on the request and listed in the report with the reason. A report never claims a reference the image source did not receive. Whether a particular image model honours several references is up to that model; Motionboard passes them and reports what it passed.

### Telling the image source which reference is which

A list of four paths does not say which is HER's face and which is HIM's silhouette. Add any of these to the adapter config; without them nothing changes.

Command adapters:

```json
{"cmd": ["python", "gen.py", "--out", "{out}", "--manifest", "{refs_manifest}", "--refs", "{refs}"],
 "refs_format": "{character}:{purpose}={path}"}
```

- `refs_format` shapes each argument `{refs}` expands to. Fields: `index`, `character`, `purpose`, `primary`, `path`, `description`.
- `{refs_manifest}` is the path of a JSON file written for the request: `{"request", "shot", "references": [{index, character, purpose, primary, path, description}]}`.
- `{refs_json}` is the same reference list inline.

HTTP adapters:

```json
{"url": "...", "body": {"prompt": "{prompt}"}, "refs_field": "input.references",
 "refs_meta": {"image": "image", "subject": "character", "role": "purpose", "main": "primary"},
 "refs_manifest_field": "input.reference_info"}
```

- `refs_meta` makes each entry at `refs_field` an object. Each key is your API's field name; each value is one of `image` (the encoded image), `index`, `character`, `purpose`, `primary`, `path`, `description`.
- `refs_manifest_field` puts the metadata list, without image data, at a second path, for APIs that take images and labels as parallel lists. It needs `refs_field`: the list labels those images, entry for entry.

Manual and handoff adapters already list every reference with its character, purpose and primary flag in `mb plate requests`. Whether a model uses the labels is up to that model.
