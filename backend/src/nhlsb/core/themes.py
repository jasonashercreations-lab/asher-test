"""Color theme presets for the scoreboard renderer.

Each theme returns a `RenderColors` struct populated for the current matchup.
Some themes use the matchup CSV (away_accent / home_accent / banner curated
per pairing). Others ignore the CSV and return a fixed palette.

API:
    resolve(theme_name, assets_root, away_abbrev, home_abbrev,
            away_team_primary, away_team_secondary,
            home_team_primary, home_team_secondary)
        -> RenderColors

The renderer always consumes RenderColors and never has to know which
theme produced them.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

from . import matchup


RGB = tuple[int, int, int]

THEME_NAMES = [
    "csv_default",
    "classic_bordered",
    "midnight",
    "ice_rink",
    "heritage",
    "neon",
    "stealth",
]
ThemeName = Literal[
    "csv_default", "classic_bordered", "midnight", "ice_rink",
    "heritage", "neon", "stealth",
]

THEME_DISPLAY_NAMES = {
    "csv_default":      "CSV Default",
    "classic_bordered": "Classic Bordered",
    "midnight":         "Midnight",
    "ice_rink":         "Ice Rink",
    "heritage":         "Heritage",
    "neon":             "Neon",
    "stealth":          "Stealth",
}


@dataclass(frozen=True)
class RenderColors:
    """All colors the renderer needs for one frame."""
    # Page
    background: RGB

    # Per-side accents (used for score border, penalty border + label, stats values)
    away_accent: RGB
    home_accent: RGB

    # Neutral chrome (banner outline, period/clock borders, stats grid lines)
    chrome: RGB

    # Score numerals and stat labels
    score_text: RGB     # the big "01" / "00"
    label_text: RGB     # SHOTS / HITS / PENALTY / PERIOD / CLOCK
    period_value_text: RGB   # "2ND", "FINAL", etc.
    clock_text: RGB          # the time digits

    # Cell backgrounds (fill behind score/banner/status/stats)
    cell_bg: RGB


# ---------- helpers ----------

def _ensure_contrast(color: RGB, min_lum: int = 120) -> RGB:
    r, g, b = color[:3]
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    if lum >= min_lum:
        return (r, g, b)
    factor = min_lum / max(1, lum)
    return (min(255, int(r * factor + 30)),
            min(255, int(g * factor + 30)),
            min(255, int(b * factor + 30)))


def _darken(color: RGB, factor: float = 0.6) -> RGB:
    r, g, b = color[:3]
    return (int(r * factor), int(g * factor), int(b * factor))


def _lighten(color: RGB, factor: float = 0.3) -> RGB:
    r, g, b = color[:3]
    return (min(255, int(r + (255 - r) * factor)),
            min(255, int(g + (255 - g) * factor)),
            min(255, int(b + (255 - b) * factor)))


def _color_dist(c1: RGB, c2: RGB) -> float:
    return abs(c1[0] - c2[0]) + abs(c1[1] - c2[1]) + abs(c1[2] - c2[2])


def _distinct_pair(away_pri: RGB, away_sec: RGB,
                   home_pri: RGB, home_sec: RGB,
                   threshold: int = 180) -> tuple[RGB, RGB]:
    """If away and home primaries are too similar, swap one to its secondary
    so the two sides read as visually distinct. Used by themes that don't
    rely on the curated CSV.

    Threshold is generous (180 vs strict 100) because dark colors converge
    after the renderer's contrast-brightening pass — two distinct-looking
    dark navies can become indistinguishable mid-blues once brightened.
    """
    if _color_dist(away_pri, home_pri) < threshold:
        return (away_pri, home_sec)
    return (away_pri, home_pri)


# ---------- theme implementations ----------

def _csv_default(assets_root, away_abbrev, home_abbrev,
                 away_pri, away_sec, home_pri, home_sec) -> RenderColors:
    """Use the curated CSV. Falls back to team primaries if no row found."""
    mc = matchup.matchup_colors(assets_root, away_abbrev, home_abbrev)
    if mc is not None:
        return RenderColors(
            background=mc.background,
            away_accent=_ensure_contrast(mc.away_accent, 80),
            home_accent=_ensure_contrast(mc.home_accent, 80),
            chrome=_ensure_contrast(mc.banner, 80),
            score_text=(255, 255, 255),
            label_text=(255, 255, 255),
            period_value_text=(255, 255, 255),
            clock_text=(220, 40, 40),
            cell_bg=(4, 4, 6),
        )
    # Fallback when CSV doesn't have this matchup
    return RenderColors(
        background=(8, 8, 10),
        away_accent=_ensure_contrast(away_pri, 80),
        home_accent=_ensure_contrast(home_pri, 80),
        chrome=(130, 134, 144),
        score_text=(255, 255, 255),
        label_text=(255, 255, 255),
        period_value_text=(255, 255, 255),
        clock_text=(220, 40, 40),
        cell_bg=(4, 4, 6),
    )


def _classic_bordered(assets_root, away_abbrev, home_abbrev,
                      away_pri, away_sec, home_pri, home_sec) -> RenderColors:
    """Original bright bordered look. Auto-swaps when team primaries match."""
    a, h = _distinct_pair(away_pri, away_sec, home_pri, home_sec)
    return RenderColors(
        background=(8, 8, 10),
        away_accent=_ensure_contrast(a, 80),
        home_accent=_ensure_contrast(h, 80),
        chrome=(130, 134, 144),
        score_text=(255, 255, 255),
        label_text=(255, 255, 255),
        period_value_text=(255, 255, 255),
        clock_text=(220, 40, 40),
        cell_bg=(4, 4, 6),
    )


def _midnight(assets_root, away_abbrev, home_abbrev,
              away_pri, away_sec, home_pri, home_sec) -> RenderColors:
    """Deep navy bg, gold accents everywhere. Premium award-show aesthetic."""
    GOLD = (212, 175, 55)
    DEEP_NAVY = (8, 14, 32)
    return RenderColors(
        background=DEEP_NAVY,
        away_accent=GOLD,
        home_accent=GOLD,
        chrome=(60, 80, 120),
        score_text=GOLD,
        label_text=GOLD,
        period_value_text=GOLD,
        clock_text=(255, 100, 100),
        cell_bg=(4, 8, 20),
    )


def _ice_rink(assets_root, away_abbrev, home_abbrev,
              away_pri, away_sec, home_pri, home_sec) -> RenderColors:
    """Light blue tinted bg, white borders, team colors only on stats."""
    ICE_BG = (12, 22, 38)
    a, h = _distinct_pair(away_pri, away_sec, home_pri, home_sec)
    return RenderColors(
        background=ICE_BG,
        away_accent=_ensure_contrast(a, 100),
        home_accent=_ensure_contrast(h, 100),
        chrome=(220, 230, 240),
        score_text=(240, 248, 255),
        label_text=(220, 230, 240),
        period_value_text=(240, 248, 255),
        clock_text=(80, 200, 255),
        cell_bg=(20, 32, 52),
    )


def _heritage(assets_root, away_abbrev, home_abbrev,
              away_pri, away_sec, home_pri, home_sec) -> RenderColors:
    """Sepia/warm vintage look. Aged-paper bg, brown accents, team colors muted."""
    PARCHMENT = (28, 22, 16)
    WARM_BORDER = (180, 140, 80)
    a, h = _distinct_pair(away_pri, away_sec, home_pri, home_sec)
    return RenderColors(
        background=PARCHMENT,
        away_accent=_darken(_ensure_contrast(a, 100), 0.85),
        home_accent=_darken(_ensure_contrast(h, 100), 0.85),
        chrome=WARM_BORDER,
        score_text=(245, 230, 200),
        label_text=(220, 195, 150),
        period_value_text=(245, 230, 200),
        clock_text=(220, 80, 60),
        cell_bg=(40, 30, 22),
    )


def _neon(assets_root, away_abbrev, home_abbrev,
          away_pri, away_sec, home_pri, home_sec) -> RenderColors:
    """Pure black bg, electric brights at full saturation. Arcade vibe."""
    a, h = _distinct_pair(away_pri, away_sec, home_pri, home_sec)
    return RenderColors(
        background=(0, 0, 0),
        away_accent=_lighten(_ensure_contrast(a, 140), 0.15),
        home_accent=_lighten(_ensure_contrast(h, 140), 0.15),
        chrome=(0, 255, 200),
        score_text=(255, 255, 255),
        label_text=(0, 255, 200),
        period_value_text=(255, 255, 255),
        clock_text=(255, 50, 100),
        cell_bg=(0, 0, 0),
    )


def _stealth(assets_root, away_abbrev, home_abbrev,
             away_pri, away_sec, home_pri, home_sec) -> RenderColors:
    """Graphite gray, monochrome chrome, team colors ONLY on score+stats values."""
    GRAPHITE = (24, 26, 30)
    a, h = _distinct_pair(away_pri, away_sec, home_pri, home_sec)
    return RenderColors(
        background=GRAPHITE,
        away_accent=_ensure_contrast(a, 130),
        home_accent=_ensure_contrast(h, 130),
        chrome=(90, 95, 105),
        score_text=(245, 245, 250),
        label_text=(170, 175, 185),
        period_value_text=(245, 245, 250),
        clock_text=(255, 80, 80),
        cell_bg=(34, 36, 42),
    )


_THEME_FNS = {
    "csv_default":      _csv_default,
    "classic_bordered": _classic_bordered,
    "midnight":         _midnight,
    "ice_rink":         _ice_rink,
    "heritage":         _heritage,
    "neon":             _neon,
    "stealth":          _stealth,
}


def resolve(theme_name: str,
            assets_root: Optional[Path],
            away_abbrev: str, home_abbrev: str,
            away_pri: RGB, away_sec: RGB,
            home_pri: RGB, home_sec: RGB) -> RenderColors:
    """Return the resolved RenderColors for the given theme + matchup."""
    fn = _THEME_FNS.get(theme_name) or _csv_default
    return fn(assets_root, away_abbrev, home_abbrev,
              away_pri, away_sec, home_pri, home_sec)
