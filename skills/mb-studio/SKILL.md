---
name: mb-studio
description: Open the Motionboard Storyboard Studio, the local web app that shows the board, the render queue and the memory meter. Use when the creator says "open the studio", "show me the board", "storyboard studio", or wants to review shots visually.
---

# Motionboard: Studio

The Studio is a local web app on 127.0.0.1. It reads and writes the same database as the chat, so changes made here or in the Studio show up in both within a second or two.

## Start

1. Run `mb studio start --json`.
   - First start runs `npm ci` and `next build`; tell the creator it takes a minute or two.
   - The report's `data.url` carries a session token. Give the creator the URL exactly. Do not paste it anywhere else.
2. If the report says `MISSING_TOOL`, Node is not installed. Give the hint from the report.

## While it runs

- Edits in chat (`mb shot set`, `mb character set`, approvals) appear in the Studio live. Edits in the Studio appear in `mb` commands at once.
- The Studio calls the same `mb` commands, so the same rules hold: gates, cost confirmation before paid plates, the memory guard.
- `mb studio status --json` says whether it is running and where.

## Stop

`mb studio stop --json` stops the server and removes the session token. Old links stop working.

## Never

- Never open the Studio to the network. It binds to 127.0.0.1 on purpose.
- Never share the token URL outside the creator's own machine.
