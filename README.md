# Motionboard

Storyboard first music videos, made on your own machine.

Motionboard is an open source Claude plugin. Give it a song, lyrics and an idea. It helps you build a storyboard timed to the music, makes an image plate per shot from whatever image source you use, animates each shot locally with an open video model (LTX-2.3 by default), and finishes the cut with lyrics, grade and an end card. A local Storyboard Studio web app shows the whole board, the render queue and your memory use.

> Status: early development. The engine, skills and five mode packs work end to end with the stub backend and on the reference Mac. The Storyboard Studio web app is next.

## Principles

- **Storyboard first.** Nothing renders until you approve the board.
- **Local and free by default.** Paid services are optional and always ask first.
- **Never crash the machine.** Every heavy job runs under a memory and swap guard you control.
- **No bundled weights.** You download models yourself and accept their licenses.
- **Runs on localhost only.** No account, no hosted site.

Full rules: [.specify/memory/constitution.md](.specify/memory/constitution.md).

## Skills

| Skill | What it does |
|---|---|
| `mb-setup` | Checks your machine, tools and models; prints exact steps for anything missing |
| `mb-storyboard` | Brainstorm or mode plus look, timed shot list, characters, contact sheet, approval |
| `mb-clips` | Image plates per shot from any source, local video clips under the memory guard |
| `mb-finish` | Animation pack, lyrics, grade, end card, cover, metadata, delivery folder |

Each skill drives the `mb` CLI. Every command takes `--json` and prints one report.

## Modes

| Mode | Story | Signature animation |
|---|---|---|
| Two Lovers | a couple across scenes | ruby thread, fairy dust lyrics |
| Studio Session | the singer in a recording booth, chorus lip-sync | REC light, VU meters, typed lyric sheet, cassette card |
| Travel | a journey, one place per section | route line, ink stamp lyrics, boarding pass |
| Lyric Story | one scene per sung line | one big word per beat, handwriting |
| Mood Loop | slow ambient shots | light leaks, drifting motes, breathing lyrics |

Looks: origami, exotic, vintage film, neon night, cosmic.

## Docs

[Install](docs/install.md) · [First video](docs/first-video.md) · [Plate adapters](docs/adapters.md) · [Memory guard](docs/guard.md) · [Licences](docs/licenses.md)

## Requirements

- Apple Silicon Mac, macOS 14+, 32 GB memory or more (Linux works except the MLX video backend)
- uv, ffmpeg 7+, Node 20+
- Claude Code

## Layout

```text
.claude-plugin/   plugin manifest
skills/           plugin commands
engine/           Python engine, `mb` CLI
studio/           local Next.js Storyboard Studio
modes/            story modes and their signature animation packs
looks/            looks (style lines)
specs/            Spec Kit specs, plans and tasks
```

## Licence

- Engine, Studio and plugin glue: MIT ([LICENSE](LICENSE)).
- Mode animation packs (`modes/*/animation/`): PolyForm Noncommercial 1.0.0. Free to use for your own videos and to study or change; not for commercial reuse or resale of the packs themselves. Videos you make with them are yours.
- Model weights you download keep their own licences.
