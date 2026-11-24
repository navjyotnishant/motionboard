# Quickstart: validate the Studio

## Prerequisites
Feature 001 quickstart steps 1 and 2 done (DB migrated, smoke project exists, stub backend).

## 1. Start
```bash
uv run mb studio start --json   # builds once, serves 127.0.0.1:4317, prints URL with token
```
Expect: URL opens the Bin with the smoke project tile. `curl http://<lan-ip>:4317` fails (loopback only).

## 2. Board and sync
Open the project. Edit shot 2 action in the panel; in a terminal run `uv run mb shot set --shot <id> --field camera --value "slow push in"`. Expect both changes visible in the board within 3 s without reload.

## 3. Timeline
Drag the boundary between shots 2 and 3. Expect it to snap to a beat, both shots update, reload keeps it.

## 4. Start flows
`/new` with the fixture song: choose Template "Lyric Story" and expect a drafted board; choose Brainstorm with `claude` available and expect three concept cards; rename `claude` on PATH and expect the "needs Claude" message.

## 5. Review
Reject a plate with a note, upload a new plate, approve. Expect versions strip shows both and the note.

## 6. Queue
Approve gates, queue clips (stub backend). Open drawer: progress and memory meter move; pause after shot 1, resume; no shot renders twice.

## 7. Animatic and exports
Play animatic: cuts match shot times. Export JSON, PDF, HTML; import JSON as a new project; boards match.

## 8. Performance
Import the 80 shot fixture; board interactive under 5 s.
