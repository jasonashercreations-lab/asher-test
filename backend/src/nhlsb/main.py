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
import re
import shutil
import sys
from pathlib import Path
from typing import Optional

from fastapi import (
    FastAPI, WebSocket, WebSocketDisconnect, HTTPException,
    UploadFile, File, Body, Request,
)
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
    """Returns (assets_root, projects_dir, presets_dir, frontend_dist_or_None)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        bundle = Path(sys._MEIPASS)
        assets = bundle / "assets"
        if sys.platform == "win32":
            user_root = Path(os.environ.get("APPDATA", Path.home())) / "NHLScoreboardStudio"
        elif sys.platform == "darwin":
            user_root = Path.home() / "Library" / "Application Support" / "NHLScoreboardStudio"
        else:
            user_root = Path(os.environ.get("XDG_DATA_HOME",
                                            Path.home() / ".local" / "share")) / "nhlsb"
        projects = user_root / "projects"
        # Presets ship with the bundle (read-only), copied to user dir on first run.
        presets = bundle / "examples"
        candidate = bundle / "frontend_dist"
        frontend = candidate if candidate.exists() else None
    else:
        here = Path(__file__).resolve().parent
        repo_root = here.parent.parent.parent
        assets = repo_root / "assets"
        projects = repo_root / "examples"
        presets = repo_root / "examples"
        candidate = repo_root / "frontend" / "dist"
        frontend = candidate if candidate.exists() else None

    assets.mkdir(parents=True, exist_ok=True)
    projects.mkdir(parents=True, exist_ok=True)
    return assets, projects, presets, frontend


ASSETS_ROOT, PROJECTS_DIR, PRESETS_DIR, FRONTEND_DIST = _resolve_paths()


# -------- Filename sanitization --------
# Strips path components and disallows traversal characters. Used on every
# user-supplied filename before joining with a directory path.
_BAD_NAME_CHARS = re.compile(r"[^A-Za-z0-9._\- ]")


def _safe_filename(name: str, allowed_exts: Optional[set[str]] = None) -> str:
    """Sanitize a filename: strip directories, restrict to safe chars, optionally
    enforce an extension whitelist. Raises HTTPException(400) if unusable."""
    if not name:
        raise HTTPException(400, "filename required")
    # Strip any directory components (path traversal defense)
    base = Path(name).name
    if not base or base in (".", ".."):
        raise HTTPException(400, "invalid filename")
    # Restrict to a safe character set
    cleaned = _BAD_NAME_CHARS.sub("_", base)
    if allowed_exts is not None:
        ext = Path(cleaned).suffix.lower()
        if ext not in allowed_exts:
            raise HTTPException(400, f"extension {ext!r} not allowed")
    return cleaned


def _safe_join(root: Path, name: str) -> Path:
    """Resolve `root / name` and verify the result is still under `root`.
    Defends against symlink escapes in addition to ../ traversal."""
    full = (root / name).resolve()
    try:
        full.relative_to(root.resolve())
    except ValueError:
        raise HTTPException(400, "path escapes root")
    return full


# -------- App + engine --------
app = FastAPI(title="nhlsb", version="1.1")

# CORS: localhost-only by default. Tauri's webview hits us from a custom
# origin (tauri://localhost on Win/Linux, https://tauri.localhost on macOS),
# and the Pi deployment is reached over LAN by users we trust on their own
# network. The wildcard "*" is gone - if anyone exposes the port to the
# public internet, they don't get CORS-bypassed by default.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^(https?://(127\.0\.0\.1|localhost|0\.0\.0\.0|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+)(:\d+)?|tauri://localhost|https://tauri\.localhost)$",
    allow_methods=["*"], allow_headers=["*"],
)

engine = Engine(assets_root=ASSETS_ROOT)


@app.on_event("startup")
async def _startup():
    asyncio.create_task(engine.run())
    # First-run preset bootstrap: copy bundled examples into the user's
    # writable projects dir so they show up in "Open project" immediately.
    if PRESETS_DIR != PROJECTS_DIR and PRESETS_DIR.exists():
        for p in PRESETS_DIR.glob("*.nhlsb"):
            target = PROJECTS_DIR / p.name
            if not target.exists():
                try:
                    shutil.copy2(p, target)
                except OSError:
                    pass


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
    safe = _safe_filename(name, allowed_exts={".nhlsb"})
    path = _safe_join(PROJECTS_DIR, safe)
    save_project(engine.project, path)
    return {"path": str(path)}


@app.post("/api/project/load")
async def load_project_endpoint(payload: SavePayload):
    safe = _safe_filename(payload.filename, allowed_exts={".nhlsb"})
    path = _safe_join(PROJECTS_DIR, safe)
    if not path.exists():
        raise HTTPException(404, f"Not found: {safe}")
    p = load_project(path)
    engine.set_project(p)
    return engine.project


@app.post("/api/project/import")
async def import_project_endpoint(file: UploadFile = File(...)):
    """Drag-drop import: accept a .nhlsb file uploaded directly, save under a
    unique name in PROJECTS_DIR, and load it into the engine."""
    if not file.filename:
        raise HTTPException(400, "filename required")
    safe = _safe_filename(file.filename, allowed_exts={".nhlsb"})
    # Ensure unique name (don't clobber existing)
    target = PROJECTS_DIR / safe
    if target.exists():
        stem, ext = target.stem, target.suffix
        i = 1
        while True:
            target = PROJECTS_DIR / f"{stem}-{i}{ext}"
            if not target.exists():
                break
            i += 1
    target = _safe_join(PROJECTS_DIR, target.name)
    # 5MB cap on .nhlsb (way more than realistic - they're tiny JSON)
    MAX_BYTES = 5 * 1024 * 1024
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413, ".nhlsb file too large (>5MB)")
    target.write_bytes(data)
    try:
        p = load_project(target)
    except Exception as e:
        target.unlink(missing_ok=True)
        raise HTTPException(400, f"invalid .nhlsb file: {e}")
    engine.set_project(p)
    return {"path": str(target), "project": p.model_dump()}


@app.delete("/api/projects/{name}")
async def delete_project(name: str):
    safe = _safe_filename(name, allowed_exts={".nhlsb"})
    path = _safe_join(PROJECTS_DIR, safe)
    if not path.exists():
        raise HTTPException(404)
    path.unlink()
    return {"ok": True}


@app.get("/api/projects")
async def list_projects():
    try:
        return [p.name for p in PROJECTS_DIR.glob("*.nhlsb") if p.is_file()]
    except OSError:
        return []


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
    return Response(content=frame, media_type="image/png",
                    headers={"Cache-Control": "no-store"})


@app.get("/api/output/{idx}/preview.png")
async def output_preview_png(idx: int):
    """Per-output thumbnail. Currently shares the engine frame since all
    outputs render the same scene; reserved for future per-output styling."""
    if idx < 0 or idx >= len(engine.project.outputs):
        raise HTTPException(404, "no such output")
    frame = engine.render_frame()
    return Response(content=frame, media_type="image/png",
                    headers={"Cache-Control": "no-store"})


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
    src = engine.project.source
    src_kind = src.kind
    src_meta: dict = {}
    if src_kind == "nhl":
        src_meta = {
            "team_filter": src.team_filter,
            "game_id": src.game_id,
            "poll_interval_sec": src.poll_interval_sec,
            "active_game_id": engine.active_game_id,
        }
    return {
        "last_fetch_ok": engine.last_fetch_ok,
        "last_fetch_at": engine.last_fetch_at,
        "last_error": engine.last_error,
        "current_state": engine.state.model_dump(),
        "source_kind": src_kind,
        "source_meta": src_meta,
        "subscriber_count": len(engine._subscribers),  # noqa - informational
    }


@app.get("/api/health")
async def health():
    return {"ok": True, "bundled": getattr(sys, "frozen", False)}


# -------- Assets --------
ALLOWED_KINDS = ("sprites", "fonts", "logos", "banners")
ALLOWED_EXTS = {
    "sprites": {".png", ".jpg", ".jpeg", ".gif", ".webp"},
    "logos":   {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"},
    "banners": {".png", ".jpg", ".jpeg", ".gif", ".webp"},
    "fonts":   {".ttf", ".otf", ".bdf"},
}
MAX_ASSET_BYTES = 25 * 1024 * 1024  # 25 MB cap per asset upload


@app.get("/api/assets")
async def list_assets():
    out = {}
    for sub in ALLOWED_KINDS:
        d = ASSETS_ROOT / sub
        d.mkdir(parents=True, exist_ok=True)
        try:
            files = []
            for p in d.iterdir():
                try:
                    if p.is_file():
                        files.append(p.name)
                except OSError:
                    continue
            out[sub] = sorted(files)
        except OSError:
            out[sub] = []
    return out


@app.post("/api/assets/{kind}")
async def upload_asset(kind: str, file: UploadFile = File(...)):
    if kind not in ALLOWED_KINDS:
        raise HTTPException(400, f"kind must be one of {ALLOWED_KINDS}")
    if not file.filename:
        raise HTTPException(400, "filename required")
    safe = _safe_filename(file.filename, allowed_exts=ALLOWED_EXTS[kind])
    target_dir = ASSETS_ROOT / kind
    target_dir.mkdir(parents=True, exist_ok=True)
    target = _safe_join(target_dir, safe)

    # Stream to disk with a hard cap, so a malicious huge upload can't OOM us.
    data = await file.read(MAX_ASSET_BYTES + 1)
    if len(data) > MAX_ASSET_BYTES:
        raise HTTPException(413, f"asset too large (>{MAX_ASSET_BYTES // 1024 // 1024}MB)")
    target.write_bytes(data)
    await engine.broadcast_frame()
    return {"path": str(target.relative_to(ASSETS_ROOT))}


@app.delete("/api/assets/{kind}/{name}")
async def delete_asset(kind: str, name: str):
    if kind not in ALLOWED_KINDS:
        raise HTTPException(400)
    safe = _safe_filename(name)
    p = _safe_join(ASSETS_ROOT / kind, safe)
    if not p.exists():
        raise HTTPException(404)
    p.unlink()
    await engine.broadcast_frame()
    return {"ok": True}


@app.get("/api/assets/{kind}/{name}")
async def get_asset(kind: str, name: str):
    if kind not in ALLOWED_KINDS:
        raise HTTPException(400)
    safe = _safe_filename(name)
    p = _safe_join(ASSETS_ROOT / kind, safe)
    if not p.exists():
        raise HTTPException(404)
    return FileResponse(p)


# -------- Frontend (source mode + Pi deployment) --------
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
