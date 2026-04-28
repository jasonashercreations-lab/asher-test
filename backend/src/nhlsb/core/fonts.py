"""Bitmap font support: built-in 5x7, plus loaders for BDF and TTF (lazy).

A loaded `BitmapFont` exposes `.draw(image, x, y, text, color, scale)` and
`.measure(text, scale) -> (w, h)`. The renderer uses this single interface
regardless of font kind.
"""
from __future__ import annotations
from typing import Protocol


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


# ---------- Loader registry ----------
_FONT_CACHE: dict[str, Font] = {}


def get_font(spec) -> Font:
    """Return a Font for a FontSpec. Cached. Falls back to built-in on error."""
    key = f"{spec.kind}:{spec.name}:{spec.size}"
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]

    if spec.kind == "bitmap":
        font = BuiltinBitmapFont()
    elif spec.kind == "bdf":
        # Stubbed - real impl would parse BDF format. Falls back for now.
        font = BuiltinBitmapFont()
    elif spec.kind == "ttf":
        font = BuiltinBitmapFont()    # TODO: PIL.ImageFont wrapper
    else:
        font = BuiltinBitmapFont()

    _FONT_CACHE[key] = font
    return font
