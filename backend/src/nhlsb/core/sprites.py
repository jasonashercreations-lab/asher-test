"""Sprite renderer. Supports procedural pixel-art sprites and PNG overrides.

Sprite resolution order (highest priority first):
  1. Project team override (team_overrides[abbrev].sprite_asset)
     - Uploaded by user via Teams panel; lives in assets/sprites/<filename>
  2. Bundled per-team PNG (assets/sprites/teams/<ABBREV>.png)
     - Shipped with the app; ABBREV must match the official 3-letter code
  3. Procedural pixel-art default (DEFAULT_PIXELS), tinted to team colors

All loaded sprites are normalized to a standard 13:20 canvas via pad_to_canvas
so they render at identical visual size regardless of upload dimensions.
"""
from __future__ import annotations
from pathlib import Path
from PIL import Image

# Standard sprite canvas (matches the procedural sprite's 13:20 aspect)
CANVAS_W = 13
CANVAS_H = 20
CANVAS_RATIO = CANVAS_W / CANVAS_H  # 0.65

# Default 13x20 sprite, hand-drawn pixel art
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


def load_team_sprite(assets_root: Path, abbrev: str) -> Image.Image | None:
    """Bug 10: Look for a bundled per-team PNG at assets/sprites/teams/<ABBREV>.png."""
    if not assets_root or not abbrev:
        return None
    candidate = assets_root / "sprites" / "teams" / f"{abbrev.upper()}.png"
    return load_sprite_asset(candidate)


def load_team_logo(assets_root: Path, abbrev: str) -> Image.Image | None:
    """Look for a bundled per-team logo at assets/logos/teams/<ABBREV>.png.
    Logos are the small team crest shown in the 'NYR vs BUF' row.
    """
    if not assets_root or not abbrev:
        return None
    candidate = assets_root / "logos" / "teams" / f"{abbrev.upper()}.png"
    return load_sprite_asset(candidate)


def load_team_banner(assets_root: Path, abbrev: str,
                     side: str | None = None) -> Image.Image | None:
    """Look for a bundled per-team banner at assets/banners/teams/<ABBREV>.png.

    If `side` is "home" or "away", looks first for <ABBR>_HOME.png /
    <ABBR>_AWAY.png so each team can have separate banners for the side
    they're playing on. Falls back to <ABBR>.png if no side-specific file
    exists, so legacy single-banner setups keep working.
    """
    if not assets_root or not abbrev:
        return None
    base = assets_root / "banners" / "teams"
    abbr_up = abbrev.upper()
    # Try side-specific first
    if side in ("home", "away"):
        side_candidate = base / f"{abbr_up}_{side.upper()}.png"
        img = load_sprite_asset(side_candidate)
        if img is not None:
            return img
    # Fallback: generic banner
    return load_sprite_asset(base / f"{abbr_up}.png")


def pad_to_canvas(sprite: Image.Image,
                  canvas_w: int = CANVAS_W * 10,
                  canvas_h: int = CANVAS_H * 10) -> Image.Image:
    """Feature 1: Resize a sprite of any dimensions to fit inside a standard
    canvas (default 130x200, the 13:20 reference size), centered on transparent
    padding. Preserves aspect ratio. Output is always exactly canvas_w x canvas_h.

    This guarantees every team's sprite renders at the same visual size on the
    scoreboard regardless of upload dimensions or aspect ratio.
    """
    if sprite is None or sprite.width == 0 or sprite.height == 0:
        return Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

    # Calculate the largest size that fits inside the canvas while preserving aspect
    src_ratio = sprite.width / sprite.height
    canvas_ratio = canvas_w / canvas_h
    if src_ratio > canvas_ratio:
        # Source is wider than canvas - fit by width
        new_w = canvas_w
        new_h = max(1, int(canvas_w / src_ratio))
    else:
        # Source is taller or same aspect - fit by height
        new_h = canvas_h
        new_w = max(1, int(canvas_h * src_ratio))

    # Use NEAREST for crisp pixel art on small/integer scales,
    # LANCZOS for smoother downscale on photo-like sources.
    if new_w >= sprite.width and new_h >= sprite.height:
        # Upscaling - keep crisp
        resized = sprite.resize((new_w, new_h), Image.NEAREST)
    else:
        # Downscaling - LANCZOS gives much better results for photographic logos
        # while still looking fine for pixel art at this small target size.
        resized = sprite.resize((new_w, new_h), Image.LANCZOS)

    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    ox = (canvas_w - new_w) // 2
    oy = (canvas_h - new_h) // 2
    canvas.paste(resized, (ox, oy), resized)
    return canvas


def tint_for_away(sprite: Image.Image, strength: float = 0.55) -> Image.Image:
    """Feature 2: Lighten a sprite for use as the away-jersey variant.
    Blends each pixel toward white by `strength` (0=no change, 1=fully white).
    Preserves alpha (transparent stays transparent).
    """
    if sprite is None or strength <= 0:
        return sprite
    strength = min(1.0, max(0.0, strength))
    out = sprite.copy().convert("RGBA")
    px = out.load()
    W, H = out.size
    for y in range(H):
        for x in range(W):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            r = int(r + (255 - r) * strength)
            g = int(g + (255 - g) * strength)
            b = int(b + (255 - b) * strength)
            px[x, y] = (r, g, b, a)
    return out


def fit_sprite(sprite: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Fit a sprite inside (target_w, target_h) preserving aspect ratio.
    - If smaller than target: integer upscale (keeps pixel art crisp).
    - If larger than target: downscale to fit (nearest-neighbor for pixel art).

    NOTE: With pad_to_canvas() now standardizing all sprites to 130x200, this
    function effectively just integer-scales them down to whatever box the
    renderer is allocating for sprites at the current resolution.
    """
    if sprite.width == 0 or sprite.height == 0 or target_w <= 0 or target_h <= 0:
        return sprite

    if sprite.width <= target_w and sprite.height <= target_h:
        sx = max(1, target_w // sprite.width)
        sy = max(1, target_h // sprite.height)
        s = min(sx, sy)
        if s == 1:
            return sprite
        return sprite.resize((sprite.width * s, sprite.height * s), Image.NEAREST)

    ratio = min(target_w / sprite.width, target_h / sprite.height)
    new_w = max(1, int(sprite.width * ratio))
    new_h = max(1, int(sprite.height * ratio))
    return sprite.resize((new_w, new_h), Image.NEAREST)