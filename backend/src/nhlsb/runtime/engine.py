"""Runtime engine. Owns the current Project, polls the data source, and
broadcasts rendered frames to subscribers (WebSocket clients, output devices).

Single-instance per process. Frontend connects via WS to receive live frames.

Clock behavior
--------------
Play:
    Clock updates only when the NHL API poll returns a fresh value. No local
    ticking, no snap-back artifacts. Displayed clock advances in chunks the
    size of `poll_interval_sec`.

Intermission:
    First poll reporting `inIntermission=true` captures `(now, secondsRemaining)`
    as an anchor. The local 1Hz tick recomputes
    `remaining = initial − (now − started_at)` so the intermission clock is
    smooth without further API involvement. When the next period starts, the
    anchor is cleared and the clock snaps to the new period's API value.

Period-transition splash:
    For `period_splash_duration_sec` seconds after a PLAY -> INT transition,
    `state.show_period_splash` is True so the renderer can draw a "END OF 1ST"
    overlay before the regular intermission view.

Auto-rotate (NHL source):
    When `auto_rotate=True`, the engine watches for the active game to enter
    FINAL state and switches to the next live game in today's schedule.
    When `rotate_interval_sec > 0`, it cycles through all live games on a timer.
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

        # ---- intermission anchor ----
        self._intermission_anchor: Optional[Tuple[float, int]] = None
        self._was_intermission: bool = False

        # ---- period-transition splash window ----
        # When a period ends, the engine flags show_period_splash for the
        # configured duration so the renderer can draw an overlay.
        self._splash_until: float = 0.0
        self._last_period_label: str = ""

        # ---- auto-rotate state (NHL source only) ----
        # Currently-displayed game id (resolved either from src.game_id or via
        # find_live_game). Surfaced in /api/status for the editor UI.
        self.active_game_id: Optional[int] = None
        self._last_rotate_at: float = 0.0
        # Cache of today's live games for cycling
        self._live_game_cache: list[int] = []
        self._live_game_cache_at: float = 0.0

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
        # Reset transient tracking on any project change
        self._intermission_anchor = None
        self._was_intermission = False
        self._splash_until = 0.0
        self._last_period_label = ""
        self.active_game_id = None
        self._last_rotate_at = 0.0
        self._live_game_cache = []
        self._live_game_cache_at = 0.0
        asyncio.create_task(self.broadcast_frame())

    # ---- frame production ----
    def render_frame(self) -> bytes:
        # Pass splash flag to renderer via a transient state attr. Done this
        # way (rather than a model field) so it doesn't get serialized into
        # saved projects - it's pure runtime presentation state.
        try:
            self.state.show_period_splash = (time.time() < self._splash_until)
        except Exception:
            pass
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

    async def _refresh_live_game_cache(self) -> list[int]:
        """Cache the day's live game ids for ~30s to avoid hammering /score/now."""
        now = time.time()
        if now - self._live_game_cache_at < 30 and self._live_game_cache:
            return self._live_game_cache
        try:
            games = await asyncio.to_thread(nhl.list_today_games)
            live = [g["id"] for g in games if g.get("state") == "LIVE" and g.get("id")]
            self._live_game_cache = live
            self._live_game_cache_at = now
        except Exception:
            pass
        return self._live_game_cache

    async def _resolve_game_id(self, src: NHLSource) -> Optional[int]:
        """Pick which game to fetch this poll, accounting for auto-rotate."""
        # Explicit game_id always wins
        if src.game_id:
            self.active_game_id = src.game_id
            return src.game_id

        # Honor team filter via existing helper
        if src.team_filter:
            try:
                gid = await asyncio.to_thread(nhl.find_live_game, src.team_filter)
                if gid:
                    self.active_game_id = gid
                    return gid
            except Exception:
                pass

        if src.auto_rotate:
            now = time.time()
            live = await self._refresh_live_game_cache()
            if not live:
                # No live games - fall back to default helper (may pick last)
                try:
                    gid = await asyncio.to_thread(nhl.find_live_game, None)
                    self.active_game_id = gid
                    return gid
                except Exception:
                    return None

            # Cycle: if rotate_interval_sec > 0 and the interval has elapsed,
            # advance to the next live game.
            if (src.rotate_interval_sec > 0
                    and self.active_game_id in live
                    and now - self._last_rotate_at >= src.rotate_interval_sec):
                idx = live.index(self.active_game_id)
                self.active_game_id = live[(idx + 1) % len(live)]
                self._last_rotate_at = now
                return self.active_game_id

            # If no current selection or current is no longer live, jump to first live
            if self.active_game_id not in live:
                self.active_game_id = live[0]
                self._last_rotate_at = now
            return self.active_game_id

        # Default behavior (no auto-rotate, no filter, no explicit id)
        try:
            gid = await asyncio.to_thread(nhl.find_live_game, None)
            self.active_game_id = gid
            return gid
        except Exception:
            return None

    async def _fetch_state(self) -> GameState | None:
        src = self.project.source
        if isinstance(src, MockSource):
            return src.state
        if isinstance(src, NHLSource):
            try:
                gid = await self._resolve_game_id(src)
                if gid is None:
                    self.last_error = "no game found"
                    self.last_fetch_ok = False
                    return None
                state = await asyncio.to_thread(nhl.fetch_game, gid)
                self.last_fetch_ok = True
                self.last_error = ""

                # Auto-rotate: if this game just went FINAL, jump to next live.
                if (src.auto_rotate and (state.period_label or "").upper() == "FINAL"):
                    live = await self._refresh_live_game_cache()
                    candidates = [g for g in live if g != gid]
                    if candidates:
                        self.active_game_id = candidates[0]
                        try:
                            state = await asyncio.to_thread(nhl.fetch_game, self.active_game_id)
                            self._last_rotate_at = time.time()
                        except Exception:
                            pass
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

            if now - last_state_fetch >= interval:
                fetched = await self._fetch_state()
                last_state_fetch = now
                self.last_fetch_at = now
                if fetched is not None:
                    await self._apply_fetched(fetched, now)

            if now - last_local_tick >= 1.0:
                changed = self._tick_intermission(now)
                # Splash window expiry also requires a re-render
                splash_just_ended = (self._splash_until > 0
                                     and now >= self._splash_until
                                     and now - self._splash_until < 1.0)
                if changed or splash_just_ended:
                    await self.broadcast_frame()
                last_local_tick = now

            await asyncio.sleep(0.1)

    async def _apply_fetched(self, fetched: GameState, now: float) -> None:
        in_int = fetched.intermission

        # Detect period change to trigger splash
        if (self.project.layout.show_period_transition_splash
                and self._last_period_label
                and fetched.period_label != self._last_period_label
                and in_int
                and not self._was_intermission):
            duration = max(0, int(self.project.layout.period_splash_duration_sec))
            self._splash_until = now + duration
        self._last_period_label = fetched.period_label

        if in_int and not self._was_intermission:
            initial_sec = _parse_clock(fetched.clock)
            self._intermission_anchor = (now, initial_sec)
            self.state = fetched
            self._was_intermission = True
            await self.broadcast_frame()
            return

        if not in_int and self._was_intermission:
            self._intermission_anchor = None
            self.state = fetched
            self._was_intermission = False
            self._splash_until = 0.0
            await self.broadcast_frame()
            return

        if in_int:
            preserved_clock = self.state.clock
            self.state = fetched
            self.state.clock = preserved_clock
            return

        self.state = fetched
        await self.broadcast_frame()

    def _tick_intermission(self, now: float) -> bool:
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
