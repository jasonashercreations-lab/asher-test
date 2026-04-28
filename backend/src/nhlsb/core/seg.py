"""7-segment style digit renderer (clean rewrite for the data-driven renderer)."""
from __future__ import annotations

_SEGMENTS = {
    "0": 0b0111111, "1": 0b0000110, "2": 0b1011011, "3": 0b1001111,
    "4": 0b1100110, "5": 0b1101101, "6": 0b1111101, "7": 0b0000111,
    "8": 0b1111111, "9": 0b1101111, "-": 0b1000000, " ": 0,
}


def draw_digit(image, x, y, ch, w, h, color, thickness=None):
    if thickness is None:
        thickness = max(1, min(w, h) // 8)
    t = thickness
    px = image.load()
    W, H = image.size
    segs = _SEGMENTS.get(ch, 0)
    mid = h // 2

    def hbar(xs, ys, length):
        for dy in range(t):
            for dx in range(length):
                xx, yy = xs + dx, ys + dy
                if 0 <= xx < W and 0 <= yy < H: px[xx, yy] = color

    def vbar(xs, ys, length):
        for dx in range(t):
            for dy in range(length):
                xx, yy = xs + dx, ys + dy
                if 0 <= xx < W and 0 <= yy < H: px[xx, yy] = color

    if segs & 0b0000001: hbar(x + t, y, w - 2 * t)                       # a
    if segs & 0b0000010: vbar(x + w - t, y + t, mid - t)                  # b
    if segs & 0b0000100: vbar(x + w - t, y + mid, h - mid - t)            # c
    if segs & 0b0001000: hbar(x + t, y + h - t, w - 2 * t)                # d
    if segs & 0b0010000: vbar(x, y + mid, h - mid - t)                    # e
    if segs & 0b0100000: vbar(x, y + t, mid - t)                          # f
    if segs & 0b1000000: hbar(x + t, y + mid - t // 2, w - 2 * t)         # g


def measure(text, w, gap=None):
    if gap is None: gap = max(1, w // 6)
    total = 0
    for ch in text:
        if ch == ":":
            total += max(1, w // 8) + gap
        else:
            total += w + gap
    return max(0, total - gap)


def draw_number(image, x, y, text, w, h, color, gap=None, thickness=None):
    if gap is None: gap = max(1, w // 6)
    cx = x
    for ch in text:
        if ch == ":":
            t = thickness or max(1, min(w, h) // 8)
            colon_w = max(1, t)
            mid_y = y + h // 3
            mid_y2 = y + 2 * h // 3
            px = image.load()
            for dy in range(t):
                for dx in range(colon_w):
                    px[cx + dx, mid_y + dy] = color
                    px[cx + dx, mid_y2 + dy] = color
            cx += colon_w + gap
        else:
            draw_digit(image, cx, y, ch, w, h, color, thickness=thickness)
            cx += w + gap
