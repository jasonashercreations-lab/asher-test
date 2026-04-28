"""NHL Web API client. Stateless, uses urllib (zero deps)."""
from __future__ import annotations
import json
import urllib.request
from typing import Optional

from .models import GameState, TeamState

BASE = "https://api-web.nhle.com/v1"
UA = {"User-Agent": "nhlsb/1.0"}


def _get(path: str) -> dict:
    req = urllib.request.Request(BASE + path, headers=UA)
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def list_today_games() -> list[dict]:
    data = _get("/score/now")
    return [{
        "id": g.get("id"),
        "away": g.get("awayTeam", {}).get("abbrev"),
        "home": g.get("homeTeam", {}).get("abbrev"),
        "state": g.get("gameState"),
    } for g in data.get("games", [])]


def find_live_game(prefer_team: Optional[str] = None) -> Optional[int]:
    games = list_today_games()
    if prefer_team:
        for g in games:
            if prefer_team.upper() in (g["away"], g["home"]):
                return g["id"]
    live = [g for g in games if g["state"] == "LIVE"]
    if live: return live[0]["id"]
    if games: return games[-1]["id"]
    return None


def _format_clock(secs):
    if secs is None: return "00:00"
    secs = int(secs)
    return f"{secs // 60:02d}:{secs % 60:02d}"


def fetch_game(game_id: int) -> GameState:
    pbp = _get(f"/gamecenter/{game_id}/play-by-play")
    rr = _get(f"/gamecenter/{game_id}/right-rail")

    away_meta = pbp.get("awayTeam", {})
    home_meta = pbp.get("homeTeam", {})

    away = TeamState(abbrev=away_meta.get("abbrev", "AWY"),
                     score=away_meta.get("score", 0))
    home = TeamState(abbrev=home_meta.get("abbrev", "HOM"),
                     score=home_meta.get("score", 0))

    stat_map = {
        "sog": "shots", "hits": "hits", "blockedShots": "blocks",
        "pim": "pim", "takeaways": "takeaways", "giveaways": "giveaways",
    }
    for entry in rr.get("teamGameStats", []):
        cat = entry.get("category")
        if cat in stat_map:
            attr = stat_map[cat]
            try:
                setattr(away, attr, int(entry.get("awayValue", 0)))
                setattr(home, attr, int(entry.get("homeValue", 0)))
            except (TypeError, ValueError):
                pass
        # Bug 8: Face-off win percentage is a float in the API; convert to int
        elif cat == "faceoffWinningPctg":
            try:
                away.faceoff_win_pct = int(round(float(entry.get("awayValue", 0)) * 100))
                home.faceoff_win_pct = int(round(float(entry.get("homeValue", 0)) * 100))
            except (TypeError, ValueError):
                pass

    pinfo = pbp.get("periodDescriptor", {}) or {}
    period_num = pinfo.get("number", 1)
    period_type = pinfo.get("periodType", "REG")
    clock = pbp.get("clock", {}) or {}
    clock_str = clock.get("timeRemaining") or _format_clock(clock.get("secondsRemaining"))
    in_int = bool(clock.get("inIntermission"))

    gs = pbp.get("gameState", "")
    if gs in ("FINAL", "OFF"):
        period_label = "FINAL"
    elif in_int:
        period_label = "INT."
    elif period_type == "OT":
        period_label = "OT"
    elif period_type == "SO":
        period_label = "SO"
    else:
        period_label = {1: "1ST", 2: "2ND", 3: "3RD"}.get(period_num, f"{period_num}TH")

    # Penalty detection (Bug 1: skip entirely if game is over)
    # Bug 2: compute seconds remaining instead of just a bool
    if gs not in ("FINAL", "OFF") and not in_int:
        plays = pbp.get("plays", [])
        # Convert "M:SS" period clock to seconds remaining IN PERIOD
        def _clock_to_sec(s):
            try:
                m, ss = s.split(":")
                return int(m) * 60 + int(ss)
            except Exception:
                return 0
        clock_sec = _clock_to_sec(clock_str)

        # Walk recent penalties; for each, compute when it would expire and
        # whether it's still active vs the current clock.
        # NHL feed gives penalty duration in minutes ("duration": 2/4/5).
        for p in reversed(plays[-50:]):
            if p.get("typeDescKey") != "penalty":
                continue
            details = p.get("details", {}) or {}
            duration_min = details.get("duration", 2)
            try:
                duration_sec = int(duration_min) * 60
            except (TypeError, ValueError):
                duration_sec = 120

            # Period of the penalty event vs current period
            pen_period = (p.get("periodDescriptor", {}) or {}).get("number", period_num)
            pen_clock = p.get("timeInPeriod", "0:00")
            # timeInPeriod is the clock when penalty was assessed (counting up
            # in some feeds, down in others). NHL Web API uses MM:SS elapsed.
            try:
                m, ss = pen_clock.split(":")
                elapsed_at_pen = int(m) * 60 + int(ss)
            except Exception:
                elapsed_at_pen = 0

            # Game elapsed seconds from start of game
            period_len = 20 * 60
            pen_total_elapsed = (pen_period - 1) * period_len + elapsed_at_pen
            cur_total_elapsed = (period_num - 1) * period_len + (period_len - clock_sec)
            remaining = (pen_total_elapsed + duration_sec) - cur_total_elapsed
            if remaining <= 0:
                continue   # already expired

            tid = details.get("eventOwnerTeamId")
            if tid == away_meta.get("id") and away.penalty_remaining_sec == 0:
                away.penalty_remaining_sec = int(remaining)
            elif tid == home_meta.get("id") and home.penalty_remaining_sec == 0:
                home.penalty_remaining_sec = int(remaining)
            if away.penalty_remaining_sec and home.penalty_remaining_sec:
                break

    return GameState(
        away=away, home=home,
        period_label=period_label,
        clock=clock_str,
        intermission=in_int,
    )
