"""Runtime engine. Owns the current Project, polls the data source, and
broadcasts rendered frames to subscribers (WebSocket clients, output devices).

Single-instance per process. Frontend connects via WS to receive live frames.

Clock behavior
--------------
Play:
    Clock updates ONLY when the NHL API poll returns a fresh value. No
    local ticking, no snap-back artifacts. The displayed clock advances
    in chunks the size of `poll_interval_sec`.

Intermission:
    The first poll that reports `inIntermission=true` captures
    `(now, secondsRemaining)` as an anchor. The local 1Hz tick then
    recomputes `remaining = initial − (now − started_at)` every second
    so the intermission clock counts down smoothly without further API
    involvement. The API is only re-consulted to detect when the next
    period starts (intermission anchor is cleared and the clock snaps
    to the new period's API value).
"""
from __future__ import annotations
import asyncio
import io
import time
from pathlib import Path
from typing import Callable, Awaitable, Optional, Tuple

from ..core import nhl, renderer
from ..core.models import GameState, Project, NHLSource, MockSource
from ..project.manager import default_project


FrameBytes = bytes
Subscriber = Callable[[FrameBytes], Awaitable[None]]


def _parse_clock(s: str) -> int:
    """'MM:SS' -> total seconds. Returns 0 on parse failure."""
    try:
        m, ss = (s or "").split(":")
        return int(m) * 60 + int(ss)
    except (ValueError, AttributeError):
        return 0


def _format_clock(total: int) -> str:
    total = max(0, int(total))
    return f"{total // 60:02d}:{total % 60:02d}"


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

        # ---- intermission anchor (reset on project change) ----
        # (wall_time_when_captured, seconds_at_capture). While set, the local
        # tick computes remaining = initial − (now − started_at) and the API
        # clock is ignored.
        self._intermission_anchor: Optional[Tuple[float, int]] = None
        # Whether the last API poll reported intermission. Used for transitions.
        self._was_intermission: bool = False

    # ---- subscription ----
    def subscribe(self, fn: Subscriber):
        self._subscribers.add(fn)

    def unsubscribe(self, fn: Subscriber):
        self._subscribers.discard(fn)

    # ---- project mutation ----
    def set_project(self, project: Project) -> None:
        self.project = project
        if isinstance(project.source, MockSource):
            self.state = project.source.state
        # Reset intermission tracking - new project may be a different game
        self._intermission_anchor = None
        self._was_intermission = False
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
        last_local_tick = time.time()

        await self.broadcast_frame()

        while self._running:
            now = time.time()
            interval = (self.project.source.poll_interval_sec
                        if isinstance(self.project.source, NHLSource) else 0.5)

            # ---- API poll: drives play clock and intermission start/end ----
            if now - last_state_fetch >= interval:
                fetched = await self._fetch_state()
                last_state_fetch = now
                self.last_fetch_at = now
                if fetched is not None:
                    await self._apply_fetched(fetched, now)

            # ---- 1Hz tick: only for the intermission countdown ----
            if now - last_local_tick >= 1.0:
                if self._tick_intermission(now):
                    await self.broadcast_frame()
                last_local_tick = now

            await asyncio.sleep(0.1)

    async def _apply_fetched(self, fetched: GameState, now: float) -> None:
        """Merge a fresh API state into self.state, handling intermission
        transitions. May broadcast a frame."""
        in_int = fetched.intermission

        # --- PLAY -> INT: capture anchor, broadcast ---
        if in_int and not self._was_intermission:
            initial_sec = _parse_clock(fetched.clock)
            self._intermission_anchor = (now, initial_sec)
            self.state = fetched
            self._was_intermission = True
            await self.broadcast_frame()
            return

        # --- INT -> PLAY: clear anchor, snap to API ---
        if not in_int and self._was_intermission:
            self._intermission_anchor = None
            self.state = fetched
            self._was_intermission = False
            await self.broadcast_frame()
            return

        # --- Continuing intermission: refresh non-clock fields, preserve local clock ---
        if in_int:
            preserved_clock = self.state.clock
            self.state = fetched
            self.state.clock = preserved_clock
            return

        # --- Active play: take API state as-is. No local ticking, no snap. ---
        self.state = fetched
        await self.broadcast_frame()

    def _tick_intermission(self, now: float) -> bool:
        """Recompute the intermission clock from the anchor. Returns True if
        the displayed value changed."""
        if not isinstance(self.project.source, NHLSource):
            return False
        if not (self.state.intermission and self._intermission_anchor is not None):
            return False
        started_at, initial_sec = self._intermission_anchor
        elapsed = int(now - started_at)
        remaining = max(0, initial_sec - elapsed)
        new_clock = _format_clock(remaining)
        if new_clock == self.state.clock:
            return False
        self.state.clock = new_clock
        return True

    def stop(self):
        self._running = False
