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

    plays = pbp.get("plays", [])
    for p in reversed(plays[-20:]):
        if p.get("typeDescKey") == "penalty":
            tid = p.get("details", {}).get("eventOwnerTeamId")
            if tid == away_meta.get("id"):   away.penalty_active = True
            elif tid == home_meta.get("id"): home.penalty_active = True
            break

    return GameState(
        away=away, home=home,
        period_label=period_label,
        clock=clock_str,
        intermission=in_int,
    )
