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
        "start_time_utc": g.get("startTimeUTC"),
    } for g in data.get("games", [])]


def list_games_for_date(date_yyyy_mm_dd: str) -> list[dict]:
    """Fetch games for a single date (YYYY-MM-DD).

    NHL endpoint: /schedule/<date> returns up to a week of upcoming games
    starting from <date>. Filter to just the requested day so we have day-level
    granularity for the UI's day picker."""
    try:
        data = _get(f"/schedule/{date_yyyy_mm_dd}")
    except Exception:
        return []
    out = []
    for week in data.get("gameWeek", []) or []:
        if week.get("date") != date_yyyy_mm_dd:
            continue
        for g in week.get("games", []) or []:
            out.append({
                "id": g.get("id"),
                "away": g.get("awayTeam", {}).get("abbrev"),
                "home": g.get("homeTeam", {}).get("abbrev"),
                "state": g.get("gameState"),
                "start_time_utc": g.get("startTimeUTC"),
                "date": date_yyyy_mm_dd,
            })
    return out


def list_games_range(start_date_yyyy_mm_dd: str, days: int = 7) -> dict[str, list[dict]]:
    """Fetch games for `days` consecutive days starting at `start_date`.

    Returns {date_str: [game_dict, ...]} so the frontend can show a day
    picker with per-day game lists. The /schedule/<date> endpoint returns
    a whole week at a time, so a single request usually covers the full
    7-day window."""
    from datetime import datetime, timedelta
    out: dict[str, list[dict]] = {}
    try:
        start = datetime.strptime(start_date_yyyy_mm_dd, "%Y-%m-%d")
    except Exception:
        return out
    # Initialize all days as empty so the frontend always sees the full window
    for i in range(days):
        d = (start + timedelta(days=i)).strftime("%Y-%m-%d")
        out[d] = []

    # The NHL schedule endpoint conveniently returns a week of data per call.
    # Make one call for the start date; if our window extends past that week,
    # make additional calls for each subsequent week.
    cursor = start
    end = start + timedelta(days=days)
    while cursor < end:
        cursor_str = cursor.strftime("%Y-%m-%d")
        try:
            data = _get(f"/schedule/{cursor_str}")
        except Exception:
            cursor += timedelta(days=7)
            continue
        for week in data.get("gameWeek", []) or []:
            day_str = week.get("date")
            if day_str not in out:
                continue
            for g in week.get("games", []) or []:
                out[day_str].append({
                    "id": g.get("id"),
                    "away": g.get("awayTeam", {}).get("abbrev"),
                    "home": g.get("homeTeam", {}).get("abbrev"),
                    "state": g.get("gameState"),
                    "start_time_utc": g.get("startTimeUTC"),
                    "date": day_str,
                })
        # Advance to the next week (NHL weeks start on Mondays in the API
        # response, but we don't care — just step by 7 days from cursor).
        cursor += timedelta(days=7)
    return out


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
    # Always render clock as zero-padded MM:SS so its width never changes
    # mid-period (the API returns "9:59" then "10:00" otherwise, which makes
    # the renderer re-fit and visibly resize text).
    raw_secs = clock.get("secondsRemaining")
    if raw_secs is None:
        # Fall back to parsing timeRemaining if secondsRemaining is missing
        tr = clock.get("timeRemaining") or "0:00"
        try:
            m, ss = tr.split(":")
            raw_secs = int(m) * 60 + int(ss)
        except Exception:
            raw_secs = 0
    clock_str = _format_clock(raw_secs)
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

        away_id = away_meta.get("id")
        home_id = home_meta.get("id")
        # Collect remaining-seconds for every active skater-affecting penalty.
        away_actives: list[int] = []
        home_actives: list[int] = []

        # NHL feed gives penalty duration in minutes ("duration": 2/4/5).
        # Misconducts (10 min) and game misconducts don't reduce skater count;
        # filter them out by typeCode/descKey when present.
        for p in plays:
            if p.get("typeDescKey") != "penalty":
                continue
            details = p.get("details", {}) or {}

            type_code = (details.get("typeCode") or "").upper()
            desc_key = (details.get("descKey") or "").lower()
            if type_code in ("MIS", "GAM") or "misconduct" in desc_key:
                continue

            duration_min = details.get("duration", 2)
            try:
                duration_sec = int(duration_min) * 60
            except (TypeError, ValueError):
                duration_sec = 120

            # Period of the penalty event vs current period
            pen_period = (p.get("periodDescriptor", {}) or {}).get("number", period_num)
            pen_period_type = (p.get("periodDescriptor", {}) or {}).get("periodType", "REG")
            pen_clock = p.get("timeInPeriod", "0:00")
            # timeInPeriod is the clock when penalty was assessed (counting up
            # in some feeds, down in others). NHL Web API uses MM:SS elapsed.
            try:
                m, ss = pen_clock.split(":")
                elapsed_at_pen = int(m) * 60 + int(ss)
            except Exception:
                elapsed_at_pen = 0

            # Period length depends on whether we're in regulation or OT, and
            # in regular season vs playoffs. Detect playoffs by gameType from
            # the parent payload (3 = playoffs, 2 = regular).
            game_type = pbp.get("gameType", 2)
            def _period_len(pn: int, ptype: str) -> int:
                if pn <= 3 or ptype == "REG":
                    return 20 * 60
                # OT - playoffs are continuous 20-min OT periods, regular
                # season is a single 5-min OT.
                if game_type == 3:
                    return 20 * 60
                return 5 * 60

            cur_period_len = _period_len(period_num, period_type)
            # Sum elapsed time across all completed periods up to (but not
            # including) the current period - each may have its own length.
            def _elapsed_through(p_no: int, ptype: str, in_period_elapsed: int) -> int:
                total = 0
                for k in range(1, p_no):
                    # Approximation: assume periods 1-3 are 20-min regulation;
                    # period >= 4 uses ptype-based length. Good enough for the
                    # penalty arithmetic since penalties don't carry across many
                    # OTs in practice.
                    total += _period_len(k, "REG" if k <= 3 else ptype)
                return total + in_period_elapsed

            pen_total_elapsed = _elapsed_through(pen_period, pen_period_type, elapsed_at_pen)
            cur_total_elapsed = _elapsed_through(period_num, period_type,
                                                 cur_period_len - clock_sec)
            remaining = (pen_total_elapsed + duration_sec) - cur_total_elapsed
            if remaining <= 0:
                continue   # already expired

            tid = details.get("eventOwnerTeamId")
            if tid == away_id:
                away_actives.append(int(remaining))
            elif tid == home_id:
                home_actives.append(int(remaining))

        # Displayed timer = soonest-expiring; count = how many are stacked.
        if away_actives:
            away.penalty_remaining_sec = min(away_actives)
            away.active_penalty_count = len(away_actives)
        if home_actives:
            home.penalty_remaining_sec = min(home_actives)
            home.active_penalty_count = len(home_actives)

    return GameState(
        away=away, home=home,
        period_label=period_label,
        clock=clock_str,
        intermission=in_int,
    )
