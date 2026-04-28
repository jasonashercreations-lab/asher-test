# Architecture

## Components

```
┌──────────────────────┐         ┌──────────────────────────┐
│  React Editor (TS)   │  HTTP   │  Python Service          │
│  Vite + Tailwind     │ ──────► │  FastAPI                 │
│  shadcn-style UI     │  + WS   │  + Renderer (PIL)        │
│  Live preview        │         │  + NHL Web API client    │
└──────────────────────┘         │  + Project save/load     │
                                  └────────────┬─────────────┘
                                               │
                            ┌──────────────────┼──────────────────┐
                            ▼                  ▼                  ▼
                       PNG / WS frames   Native window      LED matrix
                       (browser preview) (kiosk display)    (Pi hardware)
```

## Backend

`backend/src/nhlsb/`

- **`core/models.py`** — Pydantic data model. Single source of truth for everything serialized: `Project`, `Theme`, `Layout`, `GameState`, `GameSource`, `OutputDevice`. Mirrored in `frontend/src/types/project.ts`.
- **`core/renderer.py`** — Pure function `(Project, GameState) -> PIL.Image`. Reads layout fractions and theme colors from the project; no hardcoded values.
- **`core/fonts.py`** — Built-in 5×7 bitmap font; pluggable interface for BDF and TTF (stubbed).
- **`core/seg.py`** — 7-segment digit renderer for the score and clock.
- **`core/sprites.py`** — Procedural pixel-art sprite + PNG asset loader.
- **`core/teams.py`** — All 32 NHL team color palettes.
- **`core/nhl.py`** — NHL Web API client (`api-web.nhle.com`).
- **`runtime/engine.py`** — Owns the current `Project` and `GameState`. Runs the polling loop and broadcasts new frames to WebSocket subscribers.
- **`project/manager.py`** — Load/save `.nhlsb` JSON project files.
- **`api/` (routes inside `main.py`)** — FastAPI endpoints: project CRUD, NHL game listing, status, asset upload, WebSocket frame stream, static frontend serving.

## Frontend

`frontend/src/`

- **`types/project.ts`** — TypeScript mirrors of backend models.
- **`api/client.ts`** — Typed HTTP client.
- **`api/ws.ts`** — `/ws/preview` subscriber.
- **`store/project.ts`** — Zustand store. `updateProject` debounces PUTs to the backend (100 ms).
- **`components/Preview.tsx`** — Live preview canvas, zoom controls.
- **`components/Toolbar.tsx`** — Project name, save, load.
- **`components/panels/`** — Six dockable editor panels:
  - `GameSourcePanel` — switch between NHL live and Mock; mock has full state editor
  - `ThemePanel` — color pickers for every visual element + 4 presets
  - `LayoutPanel` — region size sliders, sprite toggle, stat row toggles
  - `TeamsPanel` — per-team color/sprite overrides
  - `OutputPanel` — add stream/window/LED matrix outputs
  - `StatusPanel` — backend status, current state inspection

## Data flow

```
User edits a slider in LayoutPanel
  ↓
Zustand store updateProject() runs the mutator
  ↓
schedulePush() debounces (100ms) and PUTs /api/project
  ↓
Engine.set_project() updates the live project
  ↓
Engine.broadcast_frame() renders + pushes via WebSocket
  ↓
Preview component receives blob, swaps the <img> src
```

End-to-end latency from slider drag to preview update: ~150 ms.

## Project file format

`.nhlsb` is a JSON file containing the full Pydantic-serialized `Project` model. Schema-versioned so future migrations are non-breaking. Drag-drop or use the toolbar Open menu.

## Hot reload

Asset uploads (`POST /api/assets/sprites`) trigger a `broadcast_frame()` immediately. Future: file watcher on the assets/ dir for in-place edits.

## Deployment

- **Desktop** — Tauri wraps the React frontend and spawns a PyInstaller-bundled Python service. Real `.msi`/`.dmg`/`.deb` installer. See `desktop/README.md`.
- **Pi** — Same Python service as a systemd unit, frontend served from the same port. Open editor from any browser on LAN. See `docs/PI_DEPLOYMENT.md`.
- **Hybrid** — Point a desktop install at a remote Pi by changing the API base URL (TODO: add server picker UI).
