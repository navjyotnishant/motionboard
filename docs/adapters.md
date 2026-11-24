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
