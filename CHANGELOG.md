# Changelog

## v1.1 — Big usability + security pass

### New features
- **Autosave** — edits are written to disk 3 s after the last change. The toolbar shows a status badge (saving / saved / unsaved / error). Ctrl+S still works.
- **Undo / redo** — full history of edits with Ctrl+Z and Ctrl+Shift+Z (or Ctrl+Y). Toolbar buttons too. 50-step history per session.
- **Drag-drop import** — drop a `.nhlsb` file anywhere on the editor window to open it (or use the upload button in the toolbar).
- **Visual game picker** — Source panel now lists today's games as cards with team color stripes and live state. Click to switch.
- **Auto-rotate** — NHL source can auto-advance to the next live game when the current one ends, or cycle through every live game on a timer (set in seconds in the Source panel).
- **Mock quick-set bar** — buttons for Goal AWAY/HOME, Penalty AWAY/HOME (2:00), End period, Resume, Clear pens, FINAL. Lets you test scenarios without typing.
- **Period transition splash** — when a period ends, "END OF 1ST" overlays full-bleed for a few seconds before showing the regular intermission view. Toggleable + duration adjustable in the Layout panel.
- **Live thumbnails on output cards** — every Output panel card shows the current frame.
- **Wheel-zoom + pan on Preview** — scroll to zoom around the cursor, drag to pan, double-click to reset.
- **Assets panel** — upload/delete sprites, fonts, logos, banners through the UI. Image previews for visual asset kinds.
- **"Reset to NHL official" button** in the Teams panel — wipes every override on the selected team in one click.
- **Multi-monitor fullscreen window** — Output panel now lists the actual displays detected by Tauri; clicking Open Window launches a native fullscreen window on the chosen display (no F11 needed).
- **Better Status panel** — current source URL, active game ID with deep link to NHL.com gamecenter, WebSocket subscriber count.
- **4 preset projects** — `broadcast-studio`, `cycling-live`, `minimalist-bar`, `retro-led` ship in `examples/` and auto-copy into the user's projects directory on first run.
- **Error boundary** — a single throwing component no longer blanks the whole editor; you get a tracebacky error card with a "Try again" button.

### Security / correctness fixes
- **Path-traversal hardening** on every endpoint that accepts a filename — `../` is stripped, the resolved path is checked against the root directory before any I/O.
- **File-size caps** on uploads — 5 MB on `.nhlsb` imports, 25 MB on assets. No more accidental OOM from a 4 GB "sprite".
- **CORS lock** — wildcard `"*"` is gone. Only localhost, LAN ranges (192.168.x.x / 10.x.x.x / 172.16-31.x.x), and the Tauri webview origins are allowed by default.
- **Extension whitelist** on asset uploads — only image extensions for sprites/logos/banners, only `.ttf/.otf/.bdf` for fonts.
- **Symlink-escape protection** — `safe_join` resolves symlinks and verifies the result is still under the root directory.
- **OT-aware penalty math** — penalties spanning into overtime now use the correct period length (5 min in regular season, 20 min in playoffs).

### Architecture
- Sidecar process is now killed only when the **main** Tauri window closes — so closing a scoreboard window no longer takes down the backend.
- Engine exposes `active_game_id` for the editor to display.
- `GameState` allows transient runtime attrs (period-splash flag) without polluting the saved project file.

### Deferred (planned but not yet implemented)
- HLS / RTMP streaming output (needs ffmpeg pipeline)
- Theme marketplace (needs hosted catalog)
- API key auth (low value while default is localhost-only)
- Multi-game grid mode (auto-rotate cycling delivers most of the value)
