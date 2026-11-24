# Motionboard

Storyboard first music videos, made on your own machine.

Motionboard is an open source Claude plugin. Give it a song, lyrics and an idea. It helps you build a storyboard timed to the music, makes an image plate per shot from whatever image source you use, animates each shot locally with an open video model (LTX-2.3 by default), and finishes the cut with lyrics, grade and an end card. A local Storyboard Studio web app shows the whole board, the render queue and your memory use.

> Status: early development. Not usable yet.

## Principles

- **Storyboard first.** Nothing renders until you approve the board.
- **Local and free by default.** Paid services are optional and always ask first.
- **Never crash the machine.** Every heavy job runs under a memory and swap guard you control.
- **No bundled weights.** You download models yourself and accept their licenses.
- **Runs on localhost only.** No account, no hosted site.

Full rules: [.specify/memory/constitution.md](.specify/memory/constitution.md).

## Commands (planned)

| Command | What it does |
|---|---|
| Setup check | Checks your machine, tools and models; prints exact steps for anything missing |
| Storyboard | Brainstorm or template, timed shot list, contact sheet, approval |
| Plates and clips | Image plates per shot, local video clips under the memory guard |
| Finish and deliver | Lyrics, grade, end card, cover, metadata, delivery folder |
| Studio | Opens the local Storyboard Studio |

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
templates/        storyboard templates
themes/           finishing themes
specs/            Spec Kit specs, plans and tasks
```

## Licence

MIT. Model weights you download keep their own licences.
