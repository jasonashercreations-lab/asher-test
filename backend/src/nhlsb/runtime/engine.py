"""Runtime engine. Owns the current Project, polls the data source, and
broadcasts rendered frames to subscribers (WebSocket clients, output devices).

Single-instance per process. Frontend connects via WS to receive live frames.

Clock behavior
--------------
Two independent cadences keep the displayed clock smooth without hammering
the NHL API:

  - Local 1Hz tick: every 1.0s the engine advances the displayed clock by
    1 second (during play) OR recomputes intermission remaining from an
    anchor (during intermission). This is what produces visible smoothness.

  - API poll: every `poll_interval_sec` (default 5s) the engine fetches
    ground truth from the NHL API. During *play*, the API clock value is
    snapped into state. During *intermission*, the clock is owned entirely
    by the local anchor; the API is only used to detect the start and end
    of intermission and to refresh non-clock fields (scores, stats).

Stoppage detection (play only): if the same API clock value is observed
on 3 consecutive polls, the local tick is frozen until the API moves
again (whistle, TV timeout, etc.).
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

        # ---- clock-tracking state (reset on project change) ----
        # Anchor for intermission countdown: (wall_time_when_captured, seconds_at_capture).
        # While set, the local tick computes remaining = initial - (now - started_at)
        # and the API clock is ignored.
        self._intermission_anchor: Optional[Tuple[float, int]] = None
        # Whether the last API poll reported intermission. Used to detect transitions.
        self._was_intermission: bool = False
        # Last few API clock values during play, for stoppage detection.
        self._recent_api_clocks: list[str] = []
        # Whether the local play tick is currently frozen (whistle / stoppage).
        self._clock_frozen: bool = False

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
        # Reset clock-tracking state - new project may be a different game / source
        self._intermission_anchor = None
        self._was_intermission = False
        self._recent_api_clocks.clear()
        self._clock_frozen = False
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
                    await self._apply_fetched(fetched, now)

            # ---- Local 1Hz tick between API polls ----
            if now - last_local_tick >= 1.0:
                if self._tick_local_clock(now):
                    await self.broadcast_frame()
                last_local_tick = now

            await asyncio.sleep(0.1)

    async def _apply_fetched(self, fetched: GameState, now: float) -> None:
        """Merge a fresh API state into self.state, handling intermission
        transitions and stoppage tracking. May broadcast a frame."""
        in_int = fetched.intermission

        # --- Intermission transition: PLAY -> INT ---
        if in_int and not self._was_intermission:
            initial_sec = _parse_clock(fetched.clock)
            # Anchor the countdown to the moment the API confirmed intermission.
            self._intermission_anchor = (now, initial_sec)
            self._recent_api_clocks.clear()
            self._clock_frozen = False
            self.state = fetched
            self._was_intermission = True
            await self.broadcast_frame()
            return

        # --- Intermission transition: INT -> PLAY ---
        if not in_int and self._was_intermission:
            self._intermission_anchor = None
            self._recent_api_clocks.clear()
            self._clock_frozen = False
            self.state = fetched
            self._was_intermission = False
            await self.broadcast_frame()
            return

        # --- Continuing intermission ---
        # Refresh scores / stats / period label from API but DO NOT touch
        # the clock - the local anchor owns it, smooth and uninterrupted.
        if in_int:
            preserved_clock = self.state.clock
            self.state = fetched
            self.state.clock = preserved_clock
            return

        # --- Active play: snap clock to API, track for stoppage ---
        new_clock = fetched.clock or ""
        self._recent_api_clocks.append(new_clock)
        if len(self._recent_api_clocks) > 3:
            self._recent_api_clocks.pop(0)
        self._clock_frozen = (
            len(self._recent_api_clocks) >= 3
            and len(set(self._recent_api_clocks)) == 1
        )
        self.state = fetched
        await self.broadcast_frame()

    def _tick_local_clock(self, now: float) -> bool:
        """Advance the displayed clock by 1 second of wall time.
        Returns True if state changed (caller should re-broadcast)."""
        if not isinstance(self.project.source, NHLSource):
            return False

        # ---- Intermission: compute remaining from anchor ----
        # Smooth, monotonic, API-independent. Stops at 00:00 until the API
        # reports the next period started (handled in _apply_fetched).
        if self.state.intermission and self._intermission_anchor is not None:
            started_at, initial_sec = self._intermission_anchor
            elapsed = int(now - started_at)
            remaining = max(0, initial_sec - elapsed)
            new_clock = _format_clock(remaining)
            if new_clock == self.state.clock:
                return False
            self.state.clock = new_clock
            return True

        # ---- Active play: decrement by 1s ----
        if self._clock_frozen:
            return False
        period = (self.state.period_label or "").upper()
        if period in ("FINAL", "INT.", ""):
            return False
        total = _parse_clock(self.state.clock)
        if total <= 0:
            return False
        total -= 1
        new_clock = _format_clock(total)
        if new_clock == self.state.clock:
            return False
        # Tick down active penalty timers in lockstep with game clock
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
