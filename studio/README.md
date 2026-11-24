# Motionboard Storyboard Studio

Local web app for the Motionboard board: shots in order over the song, review and approve, render queue with the
memory meter, animatic, export. It runs on 127.0.0.1 only and shares the engine's SQLite database.

```bash
mb studio start    # installs and builds on first run, prints the URL with a session token
mb studio stop
```

Development: `npm run dev` with `MB_STUDIO_TOKEN` set, then open `http://127.0.0.1:3000/?session=...`.
Tests: `npm test` (unit), `npm run typecheck`.
