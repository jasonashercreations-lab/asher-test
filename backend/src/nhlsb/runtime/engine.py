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
        """Main loop with two independent cadences:

          - Every 1.0s: render + broadcast a frame, AND tick the local clock
            down by 1 second when the game is in active play. The local tick
            is what makes the displayed clock move smoothly between API polls.

          - Every poll_interval_sec (default 1.0s): hit the NHL API for ground
            truth. When the API value lands, snap the state's clock to it.

          - Stoppage detection: track the last 3 distinct API clock values.
            If the same value comes back 3 polls in a row AND the local tick
            has already moved past it, the play is stopped (whistle, TV
            timeout, etc.) - freeze the local tick until the API moves again.
        """
        self._running = True
        last_state_fetch = 0.0
        last_local_tick = time.time()
        # Recent API clock observations for stoppage detection
        recent_api_clocks: list[str] = []
        # Whether the local tick is currently frozen (stoppage detected)
        clock_frozen = False

        # Render initial frame immediately
        await self.broadcast_frame()

        while self._running:
            now = time.time()
            interval = (self.project.source.poll_interval_sec
                        if isinstance(self.project.source, NHLSource) else 0.5)

            # ---- API poll for ground truth ----
            if now - last_state_fetch >= interval:
                fetched = await self._fetch_state()
                last_state_fetch = now
                self.last_fetch_at = now
                if fetched is not None:
                    new_clock = fetched.clock or ""
                    # Track recent API clock observations
                    recent_api_clocks.append(new_clock)
                    if len(recent_api_clocks) > 3:
                        recent_api_clocks.pop(0)
                    # Stoppage = same value 3 times in a row
                    clock_frozen = (
                        len(recent_api_clocks) >= 3
                        and len(set(recent_api_clocks)) == 1
                    )
                    # Snap state to the API value
                    self.state = fetched
                    last_local_tick = now
                    await self.broadcast_frame()
                    continue

            # ---- Local 1Hz tick between API polls ----
            if now - last_local_tick >= 1.0:
                if self._tick_local_clock(frozen=clock_frozen):
                    await self.broadcast_frame()
                last_local_tick = now

            await asyncio.sleep(0.1)

    def _tick_local_clock(self, frozen: bool) -> bool:
        """Decrement the displayed clock by 1 second if appropriate.
        Returns True if state changed (caller should re-broadcast)."""
        if frozen:
            return False
        if not isinstance(self.project.source, NHLSource):
            return False
        # Don't tick if game is over, in intermission, or in unknown state
        period = (self.state.period_label or "").upper()
        if period in ("FINAL", "INT.", ""):
            return False
        # Parse "MM:SS" - decrement by 1 second
        clock_str = self.state.clock or ""
        try:
            m, s = clock_str.split(":")
            total = int(m) * 60 + int(s)
        except (ValueError, AttributeError):
            return False
        if total <= 0:
            return False
        total -= 1
        new_clock = f"{total // 60:02d}:{total % 60:02d}"
        if new_clock == clock_str:
            return False
        # Also tick down active penalty timers
        if self.state.away.penalty_remaining_sec > 0:
            self.state.away.penalty_remaining_sec = max(
                0, self.state.away.penalty_remaining_sec - 1)
        if self.state.home.penalty_remaining_sec > 0:
            self.state.home.penalty_remaining_sec = max(
                0, self.state.home.penalty_remaining_sec - 1)
        self.state.clock = new_clock
        return True

    def stop(self):
        self._running = False
