"""Color theme presets for the scoreboard renderer.

API:
    resolve(theme_name, assets_root, away_abbrev, home_abbrev,
            away_team_primary, away_team_secondary,
            home_team_primary, home_team_secondary)
        -> RenderColors

Each theme returns a `RenderColors` struct populated for the current matchup.

Theme philosophy:
  - csv_default        - reads curated colors per matchup from the CSV.
                         Chrome (period/clock/stats) is white, distinct from
                         team accents.
  - All other themes   - SELF-CONTAINED palettes that ignore team colors.
                         NYR side and BUF side use the same theme palette.
                         Heritage means parchment-brown EVERYWHERE regardless
                         of which teams are playing.
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
    background: RGB
    away_accent: RGB
    home_accent: RGB
    chrome: RGB                 # period/clock/stats borders + dividers
    score_text: RGB
    label_text: RGB             # SHOTS, HITS, etc. label text
    period_value_text: RGB
    clock_text: RGB
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
    """When both team primaries are similar, swap one to its secondary so
    the two sides read distinctly. Used by classic_bordered only."""
    if _color_dist(away_pri, home_pri) < threshold:
        return (away_pri, home_sec)
    return (away_pri, home_pri)


# ---------- theme implementations ----------

def _csv_default(assets_root, away_abbrev, home_abbrev,
                 away_pri, away_sec, home_pri, home_sec) -> RenderColors:
    """Curated colors per matchup from the CSV.
    Chrome is plain WHITE so period/clock/stats stay visually distinct from
    the team-color accents on the score and penalty cells.
    """
    mc = matchup.matchup_colors(assets_root, away_abbrev, home_abbrev)
    if mc is not None:
        return RenderColors(
            background=mc.background,
            away_accent=_ensure_contrast(mc.away_accent, 80),
            home_accent=_ensure_contrast(mc.home_accent, 80),
            chrome=(255, 255, 255),    # plain white, distinct from team colors
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
        chrome=(255, 255, 255),
        score_text=(255, 255, 255),
        label_text=(255, 255, 255),
        period_value_text=(255, 255, 255),
        clock_text=(220, 40, 40),
        cell_bg=(4, 4, 6),
    )


def _classic_bordered(assets_root, away_abbrev, home_abbrev,
                      away_pri, away_sec, home_pri, home_sec) -> RenderColors:
    """The ONLY non-CSV theme that still uses team colors.
    Bright team primaries with auto-swap when they collide.
    """
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


# ---------- self-contained themes (ignore team colors) ----------

def _midnight(assets_root, away_abbrev, home_abbrev,
              away_pri, away_sec, home_pri, home_sec) -> RenderColors:
    """Deep navy bg, gold accents EVERYWHERE. No team color tinting.
    Premium award-show aesthetic.
    """
    GOLD = (212, 175, 55)
    DEEP_NAVY = (8, 14, 32)
    return RenderColors(
        background=DEEP_NAVY,
        away_accent=GOLD,
        home_accent=GOLD,
        chrome=(60, 80, 120),         # deep blue-gray, distinct from gold
        score_text=GOLD,
        label_text=GOLD,
        period_value_text=GOLD,
        clock_text=(255, 100, 100),
        cell_bg=(4, 8, 20),
    )


def _ice_rink(assets_root, away_abbrev, home_abbrev,
              away_pri, away_sec, home_pri, home_sec) -> RenderColors:
    """Frozen-rink look. Cold blues throughout. No team colors."""
    ICE_BG = (12, 22, 38)
    ICE_BLUE = (140, 200, 240)
    DEEP_ICE = (60, 120, 180)
    return RenderColors(
        background=ICE_BG,
        away_accent=DEEP_ICE,
        home_accent=ICE_BLUE,
        chrome=(220, 230, 240),
        score_text=(240, 248, 255),
        label_text=(220, 230, 240),
        period_value_text=(240, 248, 255),
        clock_text=(80, 200, 255),
        cell_bg=(20, 32, 52),
    )


def _heritage(assets_root, away_abbrev, home_abbrev,
              away_pri, away_sec, home_pri, home_sec) -> RenderColors:
    """Sepia/parchment vintage. Brown/cream EVERYWHERE. No team colors."""
    PARCHMENT = (28, 22, 16)
    WARM_BORDER = (180, 140, 80)
    OLD_BRASS = (158, 120, 60)
    DARK_BRASS = (110, 80, 40)
    return RenderColors(
        background=PARCHMENT,
        away_accent=OLD_BRASS,
        home_accent=DARK_BRASS,
        chrome=WARM_BORDER,
        score_text=(245, 230, 200),
        label_text=(220, 195, 150),
        period_value_text=(245, 230, 200),
        clock_text=(200, 90, 60),
        cell_bg=(40, 30, 22),
    )


def _neon(assets_root, away_abbrev, home_abbrev,
          away_pri, away_sec, home_pri, home_sec) -> RenderColors:
    """Pure black bg, electric brights. Magenta/cyan, no team colors."""
    HOT_MAGENTA = (255, 50, 200)
    ELECTRIC_CYAN = (50, 230, 255)
    return RenderColors(
        background=(0, 0, 0),
        away_accent=HOT_MAGENTA,
        home_accent=ELECTRIC_CYAN,
        chrome=(0, 255, 200),
        score_text=(255, 255, 255),
        label_text=(0, 255, 200),
        period_value_text=(255, 255, 255),
        clock_text=(255, 50, 100),
        cell_bg=(0, 0, 0),
    )


def _stealth(assets_root, away_abbrev, home_abbrev,
             away_pri, away_sec, home_pri, home_sec) -> RenderColors:
    """Graphite gray, monochrome. Two shades of light gray, no team colors."""
    GRAPHITE = (24, 26, 30)
    LIGHT_STEEL = (210, 215, 225)
    DIM_STEEL = (140, 145, 155)
    return RenderColors(
        background=GRAPHITE,
        away_accent=LIGHT_STEEL,
        home_accent=DIM_STEEL,
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
    fn = _THEME_FNS.get(theme_name) or _csv_default
    return fn(assets_root, away_abbrev, home_abbrev,
              away_pri, away_sec, home_pri, home_sec)
