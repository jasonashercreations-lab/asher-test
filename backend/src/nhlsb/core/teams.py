"""Built-in NHL team color palette aligned with the user's design spec.

Each team has:
  - main color    (dominant identity color)
  - secondary     (accent / highlight)
  - emblem        (kept for backward compatibility, defaults to white)

Colors below match the official NHL team color guide.
"""
from __future__ import annotations
from .models import RGB


def _c(r, g, b): return RGB(r=r, g=g, b=b)


# Reusable named colors
WHITE  = _c(255, 255, 255)
BLACK  = _c(10, 10, 10)
SILVER = _c(168, 169, 173)


# (main, secondary, emblem)
TEAMS = {
    # Pacific
    "ANA": (_c(252, 76, 2),    BLACK,             WHITE),    # Orange / Black
    "CGY": (_c(200, 16, 46),   _c(241, 190, 72),  WHITE),    # Red / Yellow
    "EDM": (_c(252, 76, 2),    _c(4, 30, 66),     WHITE),    # Orange / Royal Blue
    "LAK": (BLACK,             SILVER,            WHITE),    # Black / Silver
    "SEA": (_c(0, 22, 40),     _c(153, 217, 217), WHITE),    # Deep Sea Blue / Ice Blue
    "SJS": (_c(0, 109, 117),   BLACK,             WHITE),    # Teal / Black
    "VAN": (_c(0, 32, 91),     _c(0, 132, 61),    WHITE),    # Blue / Green
    "VGK": (_c(185, 151, 91),  BLACK,             WHITE),    # Gold / Black

    # Central
    "CHI": (_c(207, 10, 44),   BLACK,             WHITE),    # Red / Black
    "COL": (_c(111, 38, 61),   _c(35, 97, 146),   WHITE),    # Burgundy / Blue
    "DAL": (_c(0, 104, 71),    BLACK,             WHITE),    # Green / Black
    "MIN": (_c(21, 71, 52),    _c(175, 35, 36),   WHITE),    # Green / Red
    "NSH": (_c(255, 184, 28),  _c(4, 30, 66),     WHITE),    # Gold / Navy Blue
    "STL": (_c(0, 47, 135),    _c(252, 181, 20),  WHITE),    # Blue / Yellow
    "UTA": (BLACK,             _c(105, 179, 231), WHITE),    # Black / Mountain Blue
    "WPG": (_c(4, 30, 66),     _c(140, 200, 230), WHITE),    # Navy Blue / Light Blue

    # Atlantic
    "BOS": (BLACK,             _c(252, 181, 20),  WHITE),    # Black / Gold
    "BUF": (_c(0, 38, 84),     _c(252, 181, 20),  WHITE),    # Royal Blue / Gold
    "DET": (_c(206, 17, 38),   WHITE,             WHITE),    # Red / White
    "FLA": (_c(206, 17, 38),   _c(4, 30, 66),     WHITE),    # Red / Navy Blue
    "MTL": (_c(175, 30, 45),   _c(25, 33, 104),   WHITE),    # Red / Blue
    "OTT": (BLACK,             _c(218, 26, 50),   WHITE),    # Black / Red
    "TBL": (_c(0, 40, 104),    WHITE,             WHITE),    # Blue / White
    "TOR": (_c(0, 32, 91),     WHITE,             WHITE),    # Blue / White

    # Metropolitan
    "CAR": (_c(206, 17, 38),   BLACK,             WHITE),    # Red / Black
    "CBJ": (_c(0, 38, 84),     _c(206, 17, 38),   WHITE),    # Navy Blue / Red
    "NJD": (_c(206, 17, 38),   BLACK,             WHITE),    # Red / Black
    "NYI": (_c(0, 83, 155),    _c(244, 125, 48),  WHITE),    # Royal Blue / Orange
    "NYR": (_c(0, 56, 168),    _c(206, 17, 38),   WHITE),    # Blue / Red
    "PHI": (_c(247, 73, 2),    BLACK,             WHITE),    # Orange / Black
    "PIT": (BLACK,             _c(252, 181, 20),  WHITE),    # Black / Gold
    "WSH": (_c(206, 17, 38),   _c(4, 30, 66),     WHITE),    # Red / Navy Blue
}

DEFAULT = (_c(128, 128, 128), _c(200, 200, 200), WHITE)


def colors_for(abbrev: str, override=None) -> tuple[RGB, RGB, RGB]:
    """Resolve final colors. Override fields take precedence over base palette."""
    base = TEAMS.get(abbrev.upper(), DEFAULT)
    if override is None:
        return base
    p, s, e = base
    if override.primary:   p = override.primary
    if override.secondary: s = override.secondary
    if override.emblem:    e = override.emblem
    return (p, s, e)
