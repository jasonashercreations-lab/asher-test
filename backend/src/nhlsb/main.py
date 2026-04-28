"""FastAPI application. PyInstaller-aware for bundled (.exe) deployment.

Path resolution:
  Source mode      - assets/projects from the repo
  Bundled mode     - assets from PyInstaller _MEIPASS, projects in user dir
  Frontend         - NOT served here when bundled (Tauri serves it).
                     Served as fallback in source mode for the Pi deployment.
"""
from __future__ import annotations
import asyncio
import os
import sys
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .core import nhl, teams as teams_module
from .core.models import Project, GameState
from .runtime.engine import Engine
from .project.manager import save_project, load_project, default_project


# -------- Path resolution --------
def _resolve_paths():
    """Returns (assets_root, projects_dir, frontend_dist_or_None)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # PyInstaller bundle
        bundle = Path(sys._MEIPASS)
        assets = bundle / "assets"
        # Projects go in user dir so they persist + are writable
        if sys.platform == "win32":
            user_root = Path(os.environ.get("APPDATA", Path.home())) / "NHLScoreboardStudio"
        elif sys.platform == "darwin":
            user_root = Path.home() / "Library" / "Application Support" / "NHLScoreboardStudio"
        else:
            user_root = Path(os.environ.get("XDG_DATA_HOME",
                                            Path.home() / ".local" / "share")) / "nhlsb"
        projects = user_root / "projects"
        # Bug 3: also serve the frontend in bundled mode so external browsers
        # can hit /#/scoreboard for fullscreen output windows on second monitors.
        candidate = bundle / "frontend_dist"
        frontend = candidate if candidate.exists() else None
    else:
        # Source mode
        here = Path(__file__).resolve().parent
        repo_root = here.parent.parent.parent       # backend/src/nhlsb -> nhlsb/
        assets = repo_root / "assets"
        projects = repo_root / "examples"
        candidate = repo_root / "frontend" / "dist"
        frontend = candidate if candidate.exists() else None

    assets.mkdir(parents=True, exist_ok=True)
    projects.mkdir(parents=True, exist_ok=True)
    return assets, projects, frontend


ASSETS_ROOT, PROJECTS_DIR, FRONTEND_DIST = _resolve_paths()


# -------- App + engine --------
app = FastAPI(title="nhlsb", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)
engine = Engine(assets_root=ASSETS_ROOT)


@app.on_event("startup")
async def _startup():
    asyncio.create_task(engine.run())


# -------- Project --------
@app.get("/api/project", response_model=Project)
async def get_project():
    return engine.project


@app.put("/api/project", response_model=Project)
async def put_project(project: Project):
    engine.set_project(project)
    return engine.project


class SavePayload(BaseModel):
    filename: str


@app.post("/api/project/save")
async def save_project_endpoint(payload: SavePayload):
    name = payload.filename
    if not name.endswith(".nhlsb"):
        name += ".nhlsb"
    path = PROJECTS_DIR / name
    save_project(engine.project, path)
    return {"path": str(path)}


@app.post("/api/project/load")
async def load_project_endpoint(payload: SavePayload):
    path = PROJECTS_DIR / payload.filename
    if not path.exists():
        raise HTTPException(404, f"Not found: {payload.filename}")
    p = load_project(path)
    engine.set_project(p)
    return engine.project


@app.get("/api/projects")
async def list_projects():
    return [p.name for p in PROJECTS_DIR.glob("*.nhlsb")]


# -------- Teams --------
@app.get("/api/teams")
async def get_teams():
    return {abbr: {"primary": p.to_hex(), "secondary": s.to_hex(),
                   "emblem": e.to_hex()}
            for abbr, (p, s, e) in teams_module.TEAMS.items()}


# -------- Live game data --------
@app.get("/api/games/today")
async def games_today():
    try:
        return await asyncio.to_thread(nhl.list_today_games)
    except Exception as e:
        raise HTTPException(502, str(e))


@app.get("/api/games/{game_id}", response_model=GameState)
async def get_game(game_id: int):
    try:
        return await asyncio.to_thread(nhl.fetch_game, game_id)
    except Exception as e:
        raise HTTPException(502, str(e))


# -------- Render --------
@app.get("/api/preview.png")
async def preview_png():
    frame = engine.render_frame()
    return Response(content=frame, media_type="image/png")


@app.websocket("/ws/preview")
async def ws_preview(ws: WebSocket):
    await ws.accept()
    queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=2)

    async def push(frame: bytes):
        if queue.full():
            try: queue.get_nowait()
            except asyncio.QueueEmpty: pass
        await queue.put(frame)

    engine.subscribe(push)
    await push(engine.render_frame())
    try:
        while True:
            frame = await queue.get()
            await ws.send_bytes(frame)
    except WebSocketDisconnect:
        pass
    finally:
        engine.unsubscribe(push)


# -------- Status --------
@app.get("/api/status")
async def status():
    return {
        "last_fetch_ok": engine.last_fetch_ok,
        "last_fetch_at": engine.last_fetch_at,
        "last_error": engine.last_error,
        "current_state": engine.state.model_dump(),
    }


@app.get("/api/health")
async def health():
    return {"ok": True, "bundled": getattr(sys, "frozen", False)}


# -------- Assets --------
@app.get("/api/assets")
async def list_assets():
    out = {}
    for sub in ("sprites", "fonts"):
        d = ASSETS_ROOT / sub
        d.mkdir(parents=True, exist_ok=True)
        out[sub] = sorted(p.name for p in d.iterdir() if p.is_file())
    return out


@app.post("/api/assets/{kind}")
async def upload_asset(kind: str, file: UploadFile = File(...)):
    if kind not in ("sprites", "fonts"):
        raise HTTPException(400, "kind must be 'sprites' or 'fonts'")
    target_dir = ASSETS_ROOT / kind
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / file.filename
    target.write_bytes(await file.read())
    await engine.broadcast_frame()
    return {"path": str(target.relative_to(ASSETS_ROOT))}


@app.get("/api/assets/{kind}/{name}")
async def get_asset(kind: str, name: str):
    p = ASSETS_ROOT / kind / name
    if not p.exists():
        raise HTTPException(404)
    return FileResponse(p)


# -------- Frontend (source mode only) --------
if FRONTEND_DIST:
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
else:
    @app.get("/")
    async def root():
        return JSONResponse({
            "status": "ok",
            "msg": "API only. Frontend served by Tauri.",
            "bundled": getattr(sys, "frozen", False),
        })
