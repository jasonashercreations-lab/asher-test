"""Runtime engine. Owns the current Project, polls the data source, and
broadcasts rendered frames to subscribers (WebSocket clients, output devices).

Single-instance per process. Frontend connects via WS to receive live frames.
"""
from __future__ import annotations
import asyncio
import io
import time
from pathlib import Path
from typing import Callable, Awaitable

from ..core import nhl, renderer
from ..core.models import GameState, Project, NHLSource, MockSource
from ..project.manager import default_project


FrameBytes = bytes
Subscriber = Callable[[FrameBytes], Awaitable[None]]


class Engine:
    def __init__(self, assets_root: Path):
        self.assets_root = assets_root
        self.project: Project = default_project()
        self.state: GameState = self._initial_state()
        self.last_fetch_ok: bool = True
        self.last_fetch_at: float = 0.0
        self.last_error: str = ""
        self._subscribers: set[Subscriber] = set()
        self._task: asyncio.Task | None = None
        self._running = False

    # ---- subscription ----
    def subscribe(self, fn: Subscriber):
        self._subscribers.add(fn)

    def unsubscribe(self, fn: Subscriber):
        self._subscribers.discard(fn)

    # ---- project mutation ----
    def set_project(self, project: Project) -> None:
        self.project = project
        # Reset cached state shape for source changes
        if isinstance(project.source, MockSource):
            self.state = project.source.state
        # Re-render immediately
        asyncio.create_task(self.broadcast_frame())

    # ---- frame production ----
    def render_frame(self) -> bytes:
        img = renderer.render(self.project, self.state, assets_root=self.assets_root)
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=False)
        return buf.getvalue()

    async def broadcast_frame(self):
        if not self._subscribers:
            return
        frame = self.render_frame()
        dead = []
        for sub in list(self._subscribers):
            try:
                await sub(frame)
            except Exception:
                dead.append(sub)
        for d in dead:
            self._subscribers.discard(d)

    # ---- main loop ----
    def _initial_state(self) -> GameState:
        # Default mock state for first paint
        return MockSource().state

    async def _fetch_state(self) -> GameState | None:
        src = self.project.source
        if isinstance(src, MockSource):
            return src.state
        if isinstance(src, NHLSource):
            try:
                gid = src.game_id or nhl.find_live_game(src.team_filter)
                if gid is None:
                    self.last_error = "no game found"
                    self.last_fetch_ok = False
                    return None
                # NHL fetch is sync; offload to thread to keep loop responsive
                state = await asyncio.to_thread(nhl.fetch_game, gid)
                self.last_fetch_ok = True
                self.last_error = ""
                return state
            except Exception as e:
                self.last_error = str(e)
                self.last_fetch_ok = False
                return None
        return None

    async def run(self):
        self._running = True
        last_state_fetch = 0.0
        last_render = 0.0
        # Render initial frame immediately
        await self.broadcast_frame()
        while self._running:
            now = time.time()
            interval = (self.project.source.poll_interval_sec
                        if isinstance(self.project.source, NHLSource) else 0.5)
            if now - last_state_fetch >= interval:
                fetched = await self._fetch_state()
                if fetched is not None:
                    self.state = fetched
                last_state_fetch = now
                self.last_fetch_at = now
                await self.broadcast_frame()
                last_render = now
            await asyncio.sleep(0.1)

    def stop(self):
        self._running = False
