"""Font support: built-in 5x7 bitmap, plus TTF via PIL.ImageFont.

Two font kinds are exposed via a unified API:

    BitmapFont:   pixelated 5x7 grid scaled by integer factor
    TTFFont:      smooth Pillow truetype rendering

Both expose the same interface:
    .measure(text, scale=1)  -> (w, h)
    .draw(image, x, y, text, color, scale=1)

For TTF, "scale" is interpreted as a target pixel-height multiplier:
    actual_pt_size = max(8, scale * 4)

This lets the renderer's _auto_fit_scale() helper find the largest fitting
size with the same algorithm regardless of font kind.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path
from typing import Protocol
from PIL import ImageFont, ImageDraw, Image


class Font(Protocol):
    def measure(self, text: str, scale: int = 1, spacing: int = 1) -> tuple[int, int]: ...
    def draw(self, image, x: int, y: int, text: str, color, scale: int = 1, spacing: int = 1) -> int: ...


# ---------- Built-in 5x7 ----------
_BUILTIN_5X7: dict[str, tuple] = {
    " ": (0, 0, 0, 0, 0, 0, 0),
    ".": (0, 0, 0, 0, 0, 0, 0b00100),
    ":": (0, 0, 0b00100, 0, 0b00100, 0, 0),
    "/": (0b00001, 0b00001, 0b00010, 0b00100, 0b01000, 0b10000, 0b10000),
    "-": (0, 0, 0, 0b01110, 0, 0, 0),
    "%": (0b11001, 0b11010, 0b00100, 0b00100, 0b01011, 0b10011, 0),
    "0": (0b01110, 0b10001, 0b10011, 0b10101, 0b11001, 0b10001, 0b01110),
    "1": (0b00100, 0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110),
    "2": (0b01110, 0b10001, 0b00001, 0b00010, 0b00100, 0b01000, 0b11111),
    "3": (0b11111, 0b00010, 0b00100, 0b00010, 0b00001, 0b10001, 0b01110),
    "4": (0b00010, 0b00110, 0b01010, 0b10010, 0b11111, 0b00010, 0b00010),
    "5": (0b11111, 0b10000, 0b11110, 0b00001, 0b00001, 0b10001, 0b01110),
    "6": (0b00110, 0b01000, 0b10000, 0b11110, 0b10001, 0b10001, 0b01110),
    "7": (0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b01000, 0b01000),
    "8": (0b01110, 0b10001, 0b10001, 0b01110, 0b10001, 0b10001, 0b01110),
    "9": (0b01110, 0b10001, 0b10001, 0b01111, 0b00001, 0b00010, 0b01100),
    "A": (0b01110, 0b10001, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001),
    "B": (0b11110, 0b10001, 0b10001, 0b11110, 0b10001, 0b10001, 0b11110),
    "C": (0b01110, 0b10001, 0b10000, 0b10000, 0b10000, 0b10001, 0b01110),
    "D": (0b11110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b11110),
    "E": (0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b11111),
    "F": (0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b10000),
    "G": (0b01110, 0b10001, 0b10000, 0b10111, 0b10001, 0b10001, 0b01111),
    "H": (0b10001, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001),
    "I": (0b01110, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110),
    "J": (0b00111, 0b00010, 0b00010, 0b00010, 0b00010, 0b10010, 0b01100),
    "K": (0b10001, 0b10010, 0b10100, 0b11000, 0b10100, 0b10010, 0b10001),
    "L": (0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b11111),
    "M": (0b10001, 0b11011, 0b10101, 0b10101, 0b10001, 0b10001, 0b10001),
    "N": (0b10001, 0b10001, 0b11001, 0b10101, 0b10011, 0b10001, 0b10001),
    "O": (0b01110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110),
    "P": (0b11110, 0b10001, 0b10001, 0b11110, 0b10000, 0b10000, 0b10000),
    "Q": (0b01110, 0b10001, 0b10001, 0b10001, 0b10101, 0b10010, 0b01101),
    "R": (0b11110, 0b10001, 0b10001, 0b11110, 0b10100, 0b10010, 0b10001),
    "S": (0b01111, 0b10000, 0b10000, 0b01110, 0b00001, 0b00001, 0b11110),
    "T": (0b11111, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100),
    "U": (0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110),
    "V": (0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01010, 0b00100),
    "W": (0b10001, 0b10001, 0b10001, 0b10101, 0b10101, 0b10101, 0b01010),
    "X": (0b10001, 0b10001, 0b01010, 0b00100, 0b01010, 0b10001, 0b10001),
    "Y": (0b10001, 0b10001, 0b10001, 0b01010, 0b00100, 0b00100, 0b00100),
    "Z": (0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b10000, 0b11111),
}
_GW, _GH = 5, 7


class BuiltinBitmapFont:
    name = "default-5x7"
    kind = "bitmap"

    def measure(self, text, scale=1, spacing=1):
        text = text.upper()
        chars = [c for c in text if c in _BUILTIN_5X7]
        if not chars:
            return (0, _GH * scale)
        w = (_GW * len(chars) + spacing * (len(chars) - 1)) * scale
        return (w, _GH * scale)

    def draw(self, image, x, y, text, color, scale=1, spacing=1):
        text = text.upper()
        px = image.load()
        W, H = image.size
        cx = x
        for ch in text:
            glyph = _BUILTIN_5X7.get(ch, _BUILTIN_5X7[" "])
            for row in range(_GH):
                bits = glyph[row]
                for col in range(_GW):
                    if bits & (1 << (_GW - 1 - col)):
                        for dy in range(scale):
                            for dx in range(scale):
                                xx = cx + col * scale + dx
                                yy = y + row * scale + dy
                                if 0 <= xx < W and 0 <= yy < H:
                                    px[xx, yy] = color
            cx += (_GW + spacing) * scale
        return cx


# ---------- TTF ----------

def _resolve_ttf_path(name: str) -> Path | None:
    """Find a bundled TTF in assets/fonts/. Works in source mode and
    PyInstaller frozen mode.
    """
    if not name:
        return None
    # PyInstaller bundle
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        candidate = Path(sys._MEIPASS) / "assets" / "fonts" / name
        if candidate.exists():
            return candidate
    # Source mode: fonts.py is at backend/src/nhlsb/core/fonts.py
    # Need to go up 4 levels to reach repo root (where assets/ lives)
    here = Path(__file__).resolve().parent
    repo_root = here.parent.parent.parent.parent
    candidate = repo_root / "assets" / "fonts" / name
    if candidate.exists():
        return candidate
    return None


# Cache of (path, pixel_size) -> ImageFont
_TTF_CACHE: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def _load_ttf(path: Path, pixel_size: int) -> ImageFont.FreeTypeFont:
    key = (str(path), pixel_size)
    cached = _TTF_CACHE.get(key)
    if cached is not None:
        return cached
    font = ImageFont.truetype(str(path), pixel_size)
    _TTF_CACHE[key] = font
    return font


class TTFFont:
    """Wraps a PIL truetype font behind the bitmap-style interface.

    `scale` here is interpreted as a height multiplier so that the renderer's
    _auto_fit_scale() helper works the same way as for bitmap fonts. A scale
    of 1 = ~7px tall (matches the bitmap default), scale 10 = ~70px, etc.
    """
    kind = "ttf"

    def __init__(self, path: Path, name: str):
        self.path = path
        self.name = name

    def _font_for_scale(self, scale: int) -> ImageFont.FreeTypeFont:
        # Map "scale" to pixel-size. Bitmap font is 7px tall at scale=1,
        # so we match that progression: scale*7 ≈ pixel size.
        pixel_size = max(8, scale * 7)
        return _load_ttf(self.path, pixel_size)

    def measure(self, text, scale=1, spacing=1):
        if not text:
            return (0, 0)
        f = self._font_for_scale(scale)
        # getbbox returns (left, top, right, bottom) of the inked glyph
        bbox = f.getbbox(text)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        return (w, h)

    def draw(self, image, x, y, text, color, scale=1, spacing=1):
        if not text:
            return x
        f = self._font_for_scale(scale)
        bbox = f.getbbox(text)
        # Adjust y so the inked top aligns to `y` (PIL draws from baseline-ish)
        draw_y = y - bbox[1]
        # Adjust x so the inked left aligns to `x`
        draw_x = x - bbox[0]
        d = ImageDraw.Draw(image)
        d.text((draw_x, draw_y), text, fill=color, font=f)
        return x + (bbox[2] - bbox[0])


# ---------- Loader registry ----------
_FONT_CACHE: dict[str, Font] = {}


def get_font(spec) -> Font:
    """Return a Font for a FontSpec. Cached. Falls back to built-in on error."""
    key = f"{spec.kind}:{spec.name}:{spec.size}"
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]

    if spec.kind == "ttf" and spec.name:
        path = _resolve_ttf_path(spec.name)
        if path is not None:
            try:
                font = TTFFont(path, spec.name)
            except Exception:
                font = BuiltinBitmapFont()
        else:
            font = BuiltinBitmapFont()
    else:
        font = BuiltinBitmapFont()

    _FONT_CACHE[key] = font
    return font


def get_named_ttf(name: str) -> Font:
    """Direct accessor for a bundled TTF by filename. Used by renderer to
    grab Bebas Neue without going through Theme/FontSpec.
    """
    cache_key = f"ttf:{name}"
    if cache_key in _FONT_CACHE:
        return _FONT_CACHE[cache_key]
    path = _resolve_ttf_path(name)
    if path is None:
        return BuiltinBitmapFont()
    try:
        font = TTFFont(path, name)
    except Exception:
        font = BuiltinBitmapFont()
    _FONT_CACHE[cache_key] = font
    return font
