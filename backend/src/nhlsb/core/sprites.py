"""Sprite renderer. Supports procedural pixel-art sprites and PNG overrides.
Per-team overrides come from Project.team_overrides[abbrev].sprite_asset.
"""
from __future__ import annotations
from pathlib import Path
from PIL import Image

# Default 13x20 sprite
DEFAULT_PIXELS = [
    "....FFFFF....",
    "....FFFFF....",
    "....FF.FF....",
    "....FFFFF....",
    "....FFFFF....",
    "...PPPPPPP...",
    "..PPPPPPPPP..",
    ".PPPPEEEPPPP.",
    ".PPPPEEEPPPP.",
    ".PPPPEEEPPPP.",
    ".PPPPPPPPPPP.",
    ".PPPPPPPPPPP.",
    "..PPPPPPPPP..",
    "..SSSSSSSSS..",
    "...PPPPPPP...",
    "...PPP.PPP...",
    "...PPP.PPP...",
    "...SSS.SSS...",
    "...PPP.PPP...",
    "...KKK.KKK...",
]


def _palette(primary, secondary, emblem):
    return {
        "P": primary,
        "S": secondary,
        "E": emblem,
        "F": (240, 240, 240),
        "K": (10, 10, 10),
        ".": None,
    }


def render_procedural(pixels: list[str], primary, secondary, emblem,
                      scale: int = 1) -> Image.Image:
    h = len(pixels)
    w = len(pixels[0]) if pixels else 0
    img = Image.new("RGBA", (w * scale, h * scale), (0, 0, 0, 0))
    px = img.load()
    pal = _palette(primary, secondary, emblem)
    for ry, row in enumerate(pixels):
        for rx, ch in enumerate(row):
            color = pal.get(ch)
            if color is None:
                continue
            for dy in range(scale):
                for dx in range(scale):
                    px[rx * scale + dx, ry * scale + dy] = (*color, 255)
    return img


def load_sprite_asset(asset_path: Path) -> Image.Image | None:
    if not asset_path or not asset_path.exists():
        return None
    try:
        return Image.open(asset_path).convert("RGBA")
    except Exception:
        return None


def fit_sprite(sprite: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Integer-scale a sprite to fit inside (target_w, target_h) preserving aspect."""
    if sprite.width == 0 or sprite.height == 0:
        return sprite
    sx = max(1, target_w // sprite.width)
    sy = max(1, target_h // sprite.height)
    s = min(sx, sy)
    if s == 1 and sprite.width <= target_w and sprite.height <= target_h:
        return sprite
    return sprite.resize((sprite.width * s, sprite.height * s), Image.NEAREST)
