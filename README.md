# NHL Scoreboard Studio

Desktop app for authoring and displaying a real-time NHL scoreboard.

**Read SETUP.txt first.** It walks you through the one-time GitHub setup
that auto-builds the Windows installer for you in the cloud.

## Features

- Live NHL Web API integration (no auth, no API key)
- Full visual editor: theme, layout, per-team color overrides
- Live preview while you edit (WebSocket frame stream)
- Output → "Open Scoreboard Window" button — opens a fullscreen
  scoreboard you can drag to a second monitor / TV
- Auto-upgrade installer — new .msi replaces old version automatically
- Project files (.nhlsb) save/load
- Pi-ready architecture (same code runs as systemd service for LED panels)

## Documentation

- `SETUP.txt` — how to build and ship the installer (start here)
- `docs/ARCHITECTURE.md` — how the codebase fits together
- `docs/PI_DEPLOYMENT.md` — running on a Raspberry Pi for LED panels
