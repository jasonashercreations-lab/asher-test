"""Matchup-specific team color lookup.

Reads assets/data/matchup_colors.csv on first use. The CSV provides four
colors per matchup, curated to be visually distinct and on-brand:

    away_accent_hex   color for the away team's score/penalty/stats
    home_accent_hex   color for the home team's score/penalty/stats
    banner_hex        color for the banner outline + neutral elements
                      (period cell, clock cell, stats grid borders)
    background_hex    page background

API:
    matchup_colors(assets_root, away_abbrev, home_abbrev) -> MatchupColors

MatchupColors is a dataclass with fields away_accent, home_accent, banner,
background. All as (r, g, b) tuples in 0-255 range. Returns None for the
struct entirely if no row found (caller falls back to team primary).
"""
from __future__ import annotations
import csv
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


RGB = tuple[int, int, int]


@dataclass(frozen=True)
class MatchupColors:
    away_accent: RGB
    home_accent: RGB
    banner: RGB
    background: RGB


_CACHE: dict[tuple[str, str], MatchupColors] = {}
_LOADED_FROM: Optional[Path] = None


def _hex_to_rgb(h: str) -> RGB:
    h = h.strip().lstrip("#")
    if len(h) != 6:
        return (128, 128, 128)
    try:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    except ValueError:
        return (128, 128, 128)


def _resolve_csv_path(assets_root: Path | None) -> Path | None:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        candidate = Path(sys._MEIPASS) / "assets" / "data" / "matchup_colors.csv"
        if candidate.exists():
            return candidate
    if assets_root is not None:
        candidate = assets_root / "data" / "matchup_colors.csv"
        if candidate.exists():
            return candidate
    here = Path(__file__).resolve().parent
    repo_root = here.parent.parent.parent.parent
    candidate = repo_root / "assets" / "data" / "matchup_colors.csv"
    if candidate.exists():
        return candidate
    return None


def _load(assets_root: Path | None) -> None:
    global _LOADED_FROM
    path = _resolve_csv_path(assets_root)
    if path is None or path == _LOADED_FROM:
        return
    _CACHE.clear()
    try:
        with path.open(newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                home = (row.get("home_code") or "").strip().upper()
                away = (row.get("away_code") or "").strip().upper()
                if not (home and away):
                    continue
                _CACHE[(away, home)] = MatchupColors(
                    away_accent=_hex_to_rgb(row.get("away_accent_hex", "")),
                    home_accent=_hex_to_rgb(row.get("home_accent_hex", "")),
                    banner=_hex_to_rgb(row.get("banner_hex", "")),
                    background=_hex_to_rgb(row.get("background_hex", "")),
                )
        _LOADED_FROM = path
    except Exception:
        pass


def matchup_colors(assets_root: Path | None,
                   away_abbrev: str,
                   home_abbrev: str
                   ) -> Optional[MatchupColors]:
    """Look up the curated colors for this exact matchup. Returns None if
    no row exists for this pairing."""
    _load(assets_root)
    if not _CACHE:
        return None
    away = (away_abbrev or "").strip().upper()
    home = (home_abbrev or "").strip().upper()
    return _CACHE.get((away, home))
