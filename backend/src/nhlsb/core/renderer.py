"""Scoreboard renderer matching the user's bordered NYR vs BUF reference.

Design:
  - Bold colored borders around every panel (team color where appropriate, gray
    where neutral).
  - Single typeface (Anton) for ALL text - score, names, labels, values, times.
    Unified type system, no font mixing. Clock is the only red text.
  - 4-row layout matching the reference image exactly.
  - Banner row uses real team-banner PNGs (logo + abbreviation in one image).
  - Sprite columns use real player-figure PNGs.

Layout (4:5 portrait by default):
  ROW 1 - SCORE      Two halves with team-color borders, big white score
  ROW 2 - BANNER     Two banner halves side by side, team-color borders
                     (banner PNGs supply the logo + abbreviation graphics)
  ROW 3 - STATUS     [PENALTY | PERIOD | CLOCK | PENALTY] all bordered
  ROW 4 - SPRITES + STATS
                     Left sprite (team-color border) | stats grid (gray
                     border) | right sprite (team-color border)
"""
from __future__ import annotations
from PIL import Image, ImageDraw
from pathlib import Path

from . import sprites, teams, themes
from .fonts import get_named_ttf
from .models import GameState, Project, Layout, Theme


F_ANTON = "Anton-Regular.ttf"


# ---------- Drawing primitives ----------

def _hline(img, x0, x1, y, color, thickness=1):
    px = img.load(); W, H = img.size
    for t in range(thickness):
        yy = y + t
        if not (0 <= yy < H):
            continue
        for x in range(max(0, x0), min(W, x1)):
            px[x, yy] = color


def _vline(img, x, y0, y1, color, thickness=1):
    px = img.load(); W, H = img.size
    for t in range(thickness):
        xx = x + t
        if not (0 <= xx < W):
            continue
        for y in range(max(0, y0), min(H, y1)):
            px[xx, y] = color


def _rect_outline(img, x0, y0, x1, y1, color, thickness=1):
    _hline(img, x0, x1, y0, color, thickness)
    _hline(img, x0, x1, y1 - thickness, color, thickness)
    _vline(img, x0, y0, y1, color, thickness)
    _vline(img, x1 - thickness, y0, y1, color, thickness)


def _rect_fill(img, x0, y0, x1, y1, color):
    d = ImageDraw.Draw(img)
    d.rectangle([x0, y0, x1 - 1, y1 - 1], fill=color)


<<<<<<< HEAD
# ---------- Color helpers ----------

def _ensure_contrast(color, min_lum=120):
    r, g, b = color[:3]
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    if lum >= min_lum:
        return (r, g, b)
    factor = min_lum / max(1, lum)
    return (min(255, int(r * factor + 30)),
            min(255, int(g * factor + 30)),
            min(255, int(b * factor + 30)))


def _darken(color, factor=0.6):
    """Multiply RGB by factor (0..1). Used for darker shade of team colors."""
    r, g, b = color[:3]
    return (int(r * factor), int(g * factor), int(b * factor))


# ---------- Auto-fit ----------

def _auto_fit_scale(font, text, max_w, max_h, max_scale=400):
    if not text:
        return 1
    for s in range(max_scale, 0, -1):
=======
def _auto_fit_scale(font, text, max_w, max_h, max_scale=None):
    """Bug 7: Pick the largest integer scale where `text` fits in (max_w, max_h).
    Returns scale >= 1. If even scale=1 overflows, returns 1 anyway (caller
    decides whether to clip).
    """
    if not text:
        return 1
    cap = max_scale if max_scale is not None else 64
    for s in range(cap, 0, -1):
>>>>>>> 97a7d31b3014b69ccd02255d28512ad96215a0f3
        w, h = font.measure(text, scale=s)
        if w <= max_w and h <= max_h:
            return s
    return 1


<<<<<<< HEAD
# ---------- Sprite/banner helpers ----------

def _strip_bg(img: Image.Image) -> Image.Image:
    """Make the background transparent by detecting the corner pixel color
    (assumed to be the bg) and zero-alphaing all near-matching pixels.
    Works for sprites saved as RGB with either white or black backgrounds.
    """
    img = img.convert("RGBA")
    px = img.load()
    W, H = img.size
    # Sample the 4 corners, use the most common as "background"
    corners = [px[0, 0], px[W-1, 0], px[0, H-1], px[W-1, H-1]]
    bg_r, bg_g, bg_b = corners[0][0], corners[0][1], corners[0][2]

    # Decide threshold based on bg darkness
    is_dark_bg = (bg_r + bg_g + bg_b) < 60
    threshold = 30 if is_dark_bg else 240

    for y in range(H):
        for x in range(W):
            r, g, b, a = px[x, y]
            if is_dark_bg:
                if r <= threshold and g <= threshold and b <= threshold:
                    px[x, y] = (r, g, b, 0)
            else:
                if r >= threshold and g >= threshold and b >= threshold:
                    px[x, y] = (r, g, b, 0)
    return img


def _resolve_sprite(project, assets_root, abbrev, override, colors):
    asset_img = None
    if override and override.sprite_asset and assets_root:
        p = assets_root / "sprites" / override.sprite_asset
        asset_img = sprites.load_sprite_asset(p)
    if asset_img is None and assets_root:
        asset_img = sprites.load_team_sprite(assets_root, abbrev)
    if asset_img is None:
        pixels = project.sprite.pixels or sprites.DEFAULT_PIXELS
        p_, s_, e_ = colors
        asset_img = sprites.render_procedural(
            pixels, p_.tuple(), s_.tuple(), e_.tuple(), scale=1)
        return sprites.pad_to_canvas(asset_img)
    # Real PNG sprites: strip bg if RGB, use native aspect
    if asset_img.mode != "RGBA":
        return _strip_bg(asset_img)
    return asset_img


def _pick_distinct_colors(away_main, away_sec, home_main, home_sec):
    """Pick visually distinct frame colors for each team. If both teams' mains
    are too similar (e.g. both blue), swap one to its secondary.
    """
    def _color_dist(c1, c2):
        return ((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2 +
                (c1[2] - c2[2]) ** 2) ** 0.5

    if _color_dist(away_main, home_main) < 100:
        # Too similar - use home's secondary
        return away_main, home_sec
    return away_main, home_main


def _resolve_banner(assets_root, abbrev, fallback_color, side=None):
    if assets_root:
        b = sprites.load_team_banner(assets_root, abbrev, side=side)
        if b is not None:
            return b
    fb = Image.new("RGBA", (800, 200), fallback_color + (255,))
    return fb


def _paste_fit(img, asset, x0, y0, x1, y1):
    box_w = max(1, x1 - x0)
    box_h = max(1, y1 - y0)
    fitted = sprites.fit_sprite(asset, box_w, box_h)
    ox = x0 + (box_w - fitted.width) // 2
    oy = y0 + (box_h - fitted.height) // 2
    img.paste(fitted, (ox, oy), fitted if fitted.mode == "RGBA" else None)


def _paste_banner_fill(img, banner, x0, y0, x1, y1):
    """Fit banner inside the box, preserving aspect ratio. Pads with the
    banner's own corner color if aspect doesn't match (no cropping)."""
    box_w = max(1, x1 - x0)
    box_h = max(1, y1 - y0)
    src_ratio = banner.width / banner.height
    dst_ratio = box_w / box_h
    if src_ratio > dst_ratio:
        # Banner wider than slot - fit by width, leaves vertical room
        new_w = box_w
        new_h = max(1, int(banner.height * (box_w / banner.width)))
    else:
        # Banner taller/same - fit by height, leaves horizontal room
        new_h = box_h
        new_w = max(1, int(banner.width * (box_h / banner.height)))
    resized = banner.resize((new_w, new_h), Image.LANCZOS)
    # Center inside the slot. If there's empty space, fill it with the banner's
    # corner color so the row still looks unified.
    if new_w < box_w or new_h < box_h:
        try:
            corner_color = banner.getpixel((0, 0))
            if isinstance(corner_color, int):
                corner_color = (corner_color, corner_color, corner_color)
            corner_color = corner_color[:3]
        except Exception:
            corner_color = (0, 0, 0)
        d = ImageDraw.Draw(img)
        d.rectangle([x0, y0, x1 - 1, y1 - 1], fill=corner_color)
    ox = x0 + (box_w - new_w) // 2
    oy = y0 + (box_h - new_h) // 2
    img.paste(resized, (ox, oy), resized if resized.mode == "RGBA" else None)


# ---------- Main renderer ----------

=======
def _fit_segment_size(text, max_w, max_h):
    """Bug 7: Pick (digit_w, digit_h, gap) for 7-segment digits that fits in
    the given box. Maintains the digit's natural aspect ratio (~0.62 w/h).
    Returns (digit_w, digit_h, gap, thickness)."""
    if not text:
        return (max_w, max_h, 1, 1)
    # Try heights from max down to a minimum, find the largest where width fits.
    for digit_h in range(max_h, 4, -1):
        digit_w = max(3, int(digit_h * 0.62))
        gap = max(1, digit_w // 5)
        # measure: same logic as seg.measure
        total_w = 0
        for ch in text:
            if ch == ":":
                total_w += max(1, digit_w // 8) + gap
            else:
                total_w += digit_w + gap
        total_w = max(0, total_w - gap)
        if total_w <= max_w:
            thickness = max(1, digit_h // 7)
            return (digit_w, digit_h, gap, thickness)
    return (3, 5, 1, 1)


>>>>>>> 97a7d31b3014b69ccd02255d28512ad96215a0f3
def render(project: Project, state: GameState,
           assets_root: Path | None = None) -> Image.Image:
    L: Layout = project.layout
    T: Theme = project.theme
    W, H = L.width, L.height
<<<<<<< HEAD
=======
    img = Image.new("RGB", (W, H), T.bg.tuple())

    # Bug 7: Aspect-aware proportion adjustment.
    # The default proportions assume ~1:1. At wide or tall aspects, we
    # rebalance the vertical regions so content stays readable.
    aspect = W / max(1, H)
    score_h_frac = L.score_h
    team_h_frac = L.team_h
    pen_lbl_frac = L.pen_label_h
    pen_box_frac = L.pen_box_h
    clock_h_frac = L.clock_h
    if aspect >= 1.5:
        # Wide: shrink the top sections proportionally so stats get more room
        s = 1.0 / aspect * 1.5    # at 1.5 -> 1.0, at 3.0 -> 0.5
        score_h_frac *= s
        team_h_frac  *= s
        pen_lbl_frac *= s
        pen_box_frac *= s
        clock_h_frac *= s
    elif aspect <= 0.7:
        # Tall: stretch the top sections so they don't look tiny relative to stats
        s = min(1.5, 0.7 / aspect)
        score_h_frac = min(0.32, score_h_frac * s)
        team_h_frac  = min(0.20, team_h_frac * s)

    # Compute vertical region boundaries
    y0 = 0
    y_score_top = y0 + 2
    y_score_bot = y0 + max(8, int(H * score_h_frac))
    y_team_top  = y_score_bot + 2
    y_team_bot  = y_team_top + max(6, int(H * team_h_frac))
    y_pen_top   = y_team_bot + 1
    y_pen_lbl_b = y_pen_top + max(4, int(H * pen_lbl_frac))
    y_pen_box_b = y_pen_lbl_b + max(4, int(H * pen_box_frac))
    y_clock_top = y_pen_box_b + 2
    y_clock_bot = y_clock_top + max(6, int(H * clock_h_frac))
    y_stats_top = y_clock_bot + 2
    y_stats_bot = H - 1

    x_mid          = W // 2
    sprite_w_px    = int(W * L.sprite_w) if L.show_sprites else 0
    x_stats_left   = sprite_w_px
    x_stats_right  = W - sprite_w_px
>>>>>>> 97a7d31b3014b69ccd02255d28512ad96215a0f3

    # ===== Game state (needed early for theme) =====
    away_t = state.away
    home_t = state.home
    away_colors = teams.colors_for(away_t.abbrev,
                                   project.team_overrides.get(away_t.abbrev))
    home_colors = teams.colors_for(home_t.abbrev,
                                   project.team_overrides.get(home_t.abbrev))

    # Resolve all colors via the selected theme.
    rc = themes.resolve(
        getattr(project, "color_theme", "csv_default"),
        assets_root,
        away_t.abbrev, home_t.abbrev,
        away_colors[0].tuple(), away_colors[1].tuple(),
        home_colors[0].tuple(), home_colors[1].tuple(),
    )

<<<<<<< HEAD
    img = Image.new("RGB", (W, H), rc.background)
=======
    # ===== Score row =====
    score_h = max(0, y_score_bot - y_score_top)
    score_color = T.score_color.tuple()
    half_w = (W // 2) - 4   # margin per side
>>>>>>> 97a7d31b3014b69ccd02255d28512ad96215a0f3

    # ===== Spacing scale =====
    base = min(W, H)
    border_w  = max(3, base // 100)
    grid_w    = max(2, base // 200)
    pad       = max(4, base // 60)
    inner_pad = max(2, base // 80)
    gap       = max(3, base // 120)

    # ===== Region heights =====
    score_h_frac   = 0.18
    status_h_frac  = 0.13
    # Banner row: derive height from actual banner artwork aspect so the
    # border hugs the banner exactly with no empty padding above/below.
    inner_w_for_banner = (W - 2 * pad - 2 * border_w) // 2

    # Try to read the actual banner aspect from a real PNG; fall back to 3:1
    banner_ratio = 3.0
    if assets_root:
        for ab, sd in ((state.away.abbrev, "away"), (state.home.abbrev, "home")):
            probe = sprites.load_team_banner(assets_root, ab, side=sd)
            if probe is not None and probe.height > 0:
                banner_ratio = probe.width / probe.height
                break

    natural_banner_h = int(inner_w_for_banner / banner_ratio) + 2 * border_w
    banner_h_frac = natural_banner_h / H
    # Bottom row fills the rest

    y_score_top   = pad
    y_score_bot   = pad + max(20, int(H * score_h_frac))
    y_banner_top  = y_score_bot + gap
    y_banner_bot  = y_banner_top + max(16, int(H * banner_h_frac))
    y_status_top  = y_banner_bot + gap
    y_status_bot  = y_status_top + max(20, int(H * status_h_frac))
    y_bottom_top  = y_status_bot + gap
    y_bottom_bot  = H - pad

    # ===== Color role mapping =====
    # All team-color roles use accents from the resolved theme.
    away_score_border  = rc.away_accent
    home_score_border  = rc.home_accent
    away_banner_border = rc.chrome
    home_banner_border = rc.chrome
    away_pen_border    = rc.away_accent
    home_pen_border    = rc.home_accent
    away_label_color   = rc.away_accent
    home_label_color   = rc.home_accent
    away_stat_color    = rc.away_accent
    home_stat_color    = rc.home_accent

    # Single font for everything
    font = get_named_ttf(F_ANTON)

    NEUTRAL_WHITE = rc.label_text
    NEUTRAL_GRAY  = rc.chrome
    BG_DEEP       = rc.cell_bg
    CLOCK_RED     = rc.clock_text
    SCORE_TXT     = rc.score_text
    PERIOD_TXT    = rc.period_value_text

    is_final = state.period_label.strip().upper() == "FINAL"
    x_mid = W // 2

    # ============================================================
    #  ROW 1 - SCORE
    # ============================================================
    score_h = max(0, y_score_bot - y_score_top)

    for x0, x1, score_val, frame_color in [
        (pad, x_mid - gap // 2, away_t.score, away_score_border),
        (x_mid + gap // 2, W - pad, home_t.score, home_score_border),
    ]:
        _rect_fill(img, x0, y_score_top, x1, y_score_bot, BG_DEEP)
        _rect_outline(img, x0, y_score_top, x1, y_score_bot, frame_color, border_w)

        s = f"{score_val:02d}"
<<<<<<< HEAD
        cell_w = (x1 - x0) - 2 * inner_pad - 2 * border_w
        cell_h = score_h - 2 * inner_pad - 2 * border_w
        # Score takes ~92% of cell height — really big like the reference
        target_h = int(cell_h * 0.92)
        scale = _auto_fit_scale(font, s, cell_w, target_h)
        sw, sh = font.measure(s, scale=scale)
        font.draw(img,
                  x0 + (x1 - x0 - sw) // 2,
                  y_score_top + (score_h - sh) // 2,
                  s, SCORE_TXT, scale=scale)
=======
        cell_w = (half_x_end - half_x_start) - 6
        digit_w, digit_h, gap, thickness = _fit_segment_size(s, cell_w, score_h - 4)
        total_w = len(s) * digit_w + (len(s) - 1) * gap
        x_o = half_x_start + (half_x_end - half_x_start - total_w) // 2
        y_o = y_score_top + (score_h - digit_h) // 2
        seg.draw_number(img, x_o, y_o, s, digit_w, digit_h, score_color,
                        gap=gap, thickness=thickness)
>>>>>>> 97a7d31b3014b69ccd02255d28512ad96215a0f3

    # ============================================================
    #  ROW 2 - SINGLE STITCHED BANNER (both teams, no break in middle)
    # ============================================================
    banner_h = max(0, y_banner_bot - y_banner_top)

<<<<<<< HEAD
    # Outer rectangle for the whole banner row, single border
    bx0, bx1 = pad, W - pad
    by0, by1 = y_banner_top, y_banner_bot
=======
    # ===== Team labels =====
    team_h_px = max(0, y_team_bot - y_team_top)
    team_color = T.team_color.tuple()
    abbr_cell_w = (x_mid - 4)
    abbr_scale_a = _auto_fit_scale(team_font, away_t.abbrev, abbr_cell_w, team_h_px - 2)
    abbr_scale_h = _auto_fit_scale(team_font, home_t.abbrev, abbr_cell_w, team_h_px - 2)
    aw, ah = team_font.measure(away_t.abbrev, scale=abbr_scale_a)
    hw, hh = team_font.measure(home_t.abbrev, scale=abbr_scale_h)
    team_font.draw(img, (x_mid - aw) // 2, y_team_top + (team_h_px - ah) // 2,
                   away_t.abbrev, team_color, scale=abbr_scale_a)
    team_font.draw(img, x_mid + (W - x_mid - hw) // 2,
                   y_team_top + (team_h_px - hh) // 2,
                   home_t.abbrev, team_color, scale=abbr_scale_h)
>>>>>>> 97a7d31b3014b69ccd02255d28512ad96215a0f3

    # Inner area inside the border
    inner_x0 = bx0 + border_w
    inner_x1 = bx1 - border_w
    inner_y0 = by0 + border_w
    inner_y1 = by1 - border_w
    inner_w = inner_x1 - inner_x0
    inner_h = inner_y1 - inner_y0

<<<<<<< HEAD
    # Each half of the inner area gets one team's banner
    half_w = inner_w // 2
    away_x0 = inner_x0
    away_x1 = inner_x0 + half_w
    home_x0 = away_x1
    home_x1 = inner_x1
=======
    # ===== PEN. | period | PEN. =====
    pen_h_px = max(0, y_pen_lbl_b - y_pen_top)
    period_color = T.period_color.tuple()
>>>>>>> 97a7d31b3014b69ccd02255d28512ad96215a0f3

    away_banner = _resolve_banner(assets_root, away_t.abbrev, rc.away_accent, side="away")
    home_banner = _resolve_banner(assets_root, home_t.abbrev, rc.home_accent, side="home")
    away_is_real = (assets_root is not None and
                    sprites.load_team_banner(assets_root, away_t.abbrev, side="away") is not None)
    home_is_real = (assets_root is not None and
                    sprites.load_team_banner(assets_root, home_t.abbrev, side="home") is not None)

    if away_is_real:
        _paste_banner_fill(img, away_banner, away_x0, inner_y0, away_x1, inner_y1)
    else:
        _rect_fill(img, away_x0, inner_y0, away_x1, inner_y1, rc.away_accent)
        cw = (away_x1 - away_x0) - 2 * inner_pad
        ch = inner_h - 2 * inner_pad
        scale = _auto_fit_scale(font, away_t.abbrev, cw, int(ch * 0.85))
        tw, th = font.measure(away_t.abbrev, scale=scale)
        font.draw(img, (away_x0 + away_x1) // 2 - tw // 2,
                  (inner_y0 + inner_y1) // 2 - th // 2,
                  away_t.abbrev, NEUTRAL_WHITE, scale=scale)

<<<<<<< HEAD
    if home_is_real:
        _paste_banner_fill(img, home_banner, home_x0, inner_y0, home_x1, inner_y1)
    else:
        _rect_fill(img, home_x0, inner_y0, home_x1, inner_y1, rc.home_accent)
        cw = (home_x1 - home_x0) - 2 * inner_pad
        ch = inner_h - 2 * inner_pad
        scale = _auto_fit_scale(font, home_t.abbrev, cw, int(ch * 0.85))
        tw, th = font.measure(home_t.abbrev, scale=scale)
        font.draw(img, (home_x0 + home_x1) // 2 - tw // 2,
                  (inner_y0 + inner_y1) // 2 - th // 2,
                  home_t.abbrev, NEUTRAL_WHITE, scale=scale)

    # Single outer border around the whole banner row.
    # Use a gradient effect: away color on left half, home color on right half
    # of the border (gives both teams identity even though banner is unbroken).
    # If frame colors are similar (auto-distinct picked them apart), this still
    # looks intentional.
    _hline(img, bx0, x_mid, by0, away_banner_border, border_w)
    _hline(img, x_mid, bx1, by0, home_banner_border, border_w)
    _hline(img, bx0, x_mid, by1 - border_w, away_banner_border, border_w)
    _hline(img, x_mid, bx1, by1 - border_w, home_banner_border, border_w)
    _vline(img, bx0, by0, by1, away_banner_border, border_w)
    _vline(img, bx1 - border_w, by0, by1, home_banner_border, border_w)

    # ============================================================
    #  ROW 3 - STATUS (4 cells with gaps, all with bold borders)
    # ============================================================
    status_h = max(0, y_status_bot - y_status_top)
    avail_w = W - 2 * pad - 3 * gap
    cell_w = avail_w // 4

    cells = []
    cur_x = pad
    for _ in range(4):
        cells.append((cur_x, cur_x + cell_w))
        cur_x += cell_w + gap

    away_pen = (f"{away_t.penalty_remaining_sec // 60:02d}:{away_t.penalty_remaining_sec % 60:02d}"
                if away_t.penalty_remaining_sec > 0 and not is_final else "")
    home_pen = (f"{home_t.penalty_remaining_sec // 60:02d}:{home_t.penalty_remaining_sec % 60:02d}"
                if home_t.penalty_remaining_sec > 0 and not is_final else "")
    # specs: (label, value, value_color, label_color, border_color)
    # label_color stays vivid for readability; border_color is darker.
    specs = [
        ("PENALTY", away_pen,             NEUTRAL_WHITE,  away_label_color, away_pen_border),
        ("PERIOD",  state.period_label,   NEUTRAL_WHITE,  NEUTRAL_GRAY,     NEUTRAL_GRAY),
        ("CLOCK",   state.clock if not is_final else "", CLOCK_RED, NEUTRAL_GRAY, NEUTRAL_GRAY),
        ("PENALTY", home_pen,             NEUTRAL_WHITE,  home_label_color, home_pen_border),
    ]

    label_h = max(8, int(status_h * 0.28))   # smaller label
    value_h = status_h - label_h - inner_pad - 2 * border_w   # most for value

    # Match text sizes across all 4 cells: find the largest label scale that
    # fits ALL labels in their cell width, and same for values. This ensures
    # every cell looks visually consistent.
    cell_inner_w_min = min(x1 - x0 for (x0, x1) in cells) - 2 * inner_pad - 2 * border_w
    cell_inner_w_min = max(1, cell_inner_w_min)

    all_labels = [s[0] for s in specs]
    label_scale_unified = min(
        _auto_fit_scale(font, lbl, cell_inner_w_min, int(label_h * 0.85))
        for lbl in all_labels
    )

    # Values: only consider non-empty values
    all_values = [s[1] for s in specs if s[1]]
    if all_values:
        value_scale_unified = min(
            _auto_fit_scale(font, v, cell_inner_w_min, int(value_h * 0.95))
            for v in all_values
        )
    else:
        value_scale_unified = 1

    for (x0, x1), (label, value, val_color, label_color, border_color) in zip(cells, specs):
        _rect_fill(img, x0, y_status_top, x1, y_status_bot, BG_DEEP)
        _rect_outline(img, x0, y_status_top, x1, y_status_bot,
                      border_color, border_w)

        # Label (top of cell) - unified scale, in vivid label_color (not border)
        lw, lh = font.measure(label, scale=label_scale_unified)
        font.draw(img,
                  (x0 + x1) // 2 - lw // 2,
                  y_status_top + border_w + inner_pad,
                  label, label_color, scale=label_scale_unified)

        if not value:
            continue
        # Value (bottom of cell) - unified scale, vertically centered in value zone
        vw, vh = font.measure(value, scale=value_scale_unified)
        value_zone_top = y_status_top + border_w + inner_pad + label_h
        font.draw(img,
                  (x0 + x1) // 2 - vw // 2,
                  value_zone_top + (value_h - vh) // 2,
                  value, val_color, scale=value_scale_unified)

    # ============================================================
    #  ROW 4 - SPRITES + STATS
    # ============================================================
    bottom_h = max(0, y_bottom_bot - y_bottom_top)
    sprite_w_px = int(W * L.sprite_w) if L.show_sprites else 0

    left_x0  = pad
    left_x1  = left_x0 + sprite_w_px
    right_x1 = W - pad
    right_x0 = right_x1 - sprite_w_px
    stats_x0 = left_x1 + gap
    stats_x1 = right_x0 - gap

    # Sprite columns - NO BORDER, sprite fills proportionally
    if L.show_sprites and sprite_w_px > 0:
        for x0, x1, abbrev, override, colors_t in [
            (left_x0, left_x1, away_t.abbrev,
             project.team_overrides.get(away_t.abbrev), away_colors),
            (right_x0, right_x1, home_t.abbrev,
             project.team_overrides.get(home_t.abbrev), home_colors),
        ]:
            sprite = _resolve_sprite(project, assets_root, abbrev, override, colors_t)
            # Paste directly on page bg, no surrounding box, fill the column
            _paste_fit(img, sprite,
                       x0, y_bottom_top,
                       x1, y_bottom_bot)

    # Stats grid (middle)
=======
    if L.show_pen_indicators:
        pen_label_cell_w = max(0, x_pen_l_end - 4)
        pen_lbl_scale = _auto_fit_scale(label_font, "PEN.", pen_label_cell_w, pen_h_px - 2)
        for x_center, label in [
            (x_pen_l_end // 2, "PEN."),
            ((x_pen_r_start + W) // 2, "PEN."),
        ]:
            tw, th = label_font.measure(label, scale=pen_lbl_scale)
            label_font.draw(img, x_center - tw // 2,
                            y_pen_top + (pen_h_px - th) // 2,
                            label, team_color, scale=pen_lbl_scale)

    period_cell_w = max(0, x_pen_r_start - x_pen_l_end - 4)
    period_scale = _auto_fit_scale(label_font, state.period_label, period_cell_w, pen_h_px - 2)
    pcw, pch = label_font.measure(state.period_label, scale=period_scale)
    label_font.draw(img, (x_pen_l_end + x_pen_r_start) // 2 - pcw // 2,
                    y_pen_top + (pen_h_px - pch) // 2,
                    state.period_label, period_color, scale=period_scale)

    _hline(img, 0, W, y_pen_lbl_b, grid)
    if L.show_pen_indicators:
        _vline(img, x_pen_l_end, y_team_bot, y_pen_box_b, grid)
        _vline(img, x_pen_r_start, y_team_bot, y_pen_box_b, grid)
    _vline(img, 0, y_team_bot, y_pen_box_b, grid)
    _vline(img, W - 1, y_team_bot, y_pen_box_b, grid)

    if L.show_pen_indicators:
        # Bug 2: Show "M:SS" countdown text in the penalty box instead of a
        # solid bar. Blank when no penalty active.
        def _fmt_pen(secs: int) -> str:
            if secs <= 0:
                return ""
            return f"{secs // 60}:{secs % 60:02d}"

        pen_box_h = max(0, y_pen_box_b - y_pen_lbl_b)
        pen_color = T.penalty_active_color.tuple()

        for x0, x1, secs in [
            (2, x_pen_l_end - 1, away_t.penalty_remaining_sec),
            (x_pen_r_start + 1, W - 2, home_t.penalty_remaining_sec),
        ]:
            txt = _fmt_pen(secs)
            if not txt:
                continue
            cell_w = max(0, x1 - x0 - 2)
            ts = _auto_fit_scale(label_font, txt, cell_w, pen_box_h - 2)
            tw, th = label_font.measure(txt, scale=ts)
            cx = (x0 + x1) // 2
            cy = y_pen_lbl_b + (pen_box_h - th) // 2
            label_font.draw(img, cx - tw // 2, cy, txt, pen_color, scale=ts)

    # ===== Clock =====
    clock_h_px = max(0, y_clock_bot - y_clock_top)
    cdw, cdh, cgap, cthick = _fit_segment_size(state.clock, W - 8, clock_h_px - 4)
    cw = seg.measure(state.clock, cdw, gap=cgap)
    cx = (W - cw) // 2
    cy = y_clock_top + (clock_h_px - cdh) // 2
    seg.draw_number(img, cx, cy, state.clock, cdw, cdh,
                    T.clock_color.tuple(), gap=cgap, thickness=cthick)

    _hline(img, 0, W, y_pen_box_b, grid)
    _hline(img, 0, W, y_clock_bot, grid)

    # ===== Stats grid =====
>>>>>>> 97a7d31b3014b69ccd02255d28512ad96215a0f3
    visible_stats = [s for s in L.stats if s.enabled]
    if visible_stats and stats_x1 > stats_x0:
        _rect_fill(img, stats_x0, y_bottom_top, stats_x1, y_bottom_bot, BG_DEEP)

        row_h = bottom_h // len(visible_stats)
        inner_w = stats_x1 - stats_x0
        label_col_w = int(inner_w * 0.50)
        val_col_w = (inner_w - label_col_w) // 2
        x_aval = stats_x0
        x_lbl  = x_aval + val_col_w
        x_hval = x_lbl + label_col_w

<<<<<<< HEAD
        # Outer border (gray)
        _rect_outline(img, stats_x0, y_bottom_top, stats_x1, y_bottom_bot,
                      NEUTRAL_GRAY, border_w)
        # Internal vertical dividers
        _vline(img, x_lbl, y_bottom_top, y_bottom_bot, NEUTRAL_GRAY, grid_w)
        _vline(img, x_hval, y_bottom_top, y_bottom_bot, NEUTRAL_GRAY, grid_w)
        # Internal horizontal dividers
        for i in range(1, len(visible_stats)):
            ry = y_bottom_top + i * row_h
            _hline(img, stats_x0, stats_x1, ry, NEUTRAL_GRAY, grid_w)

        def _fmt_stat(field, raw):
            if field == "faceoff_win_pct":
                try: return f"{int(raw)}%"
                except (TypeError, ValueError): return str(raw)
            return str(raw)
=======
        val_color = T.stat_value_color.tuple()
        lbl_color = T.stat_label_color.tuple()
>>>>>>> 97a7d31b3014b69ccd02255d28512ad96215a0f3

        # Helper: format value with % suffix for percentage-style fields
        def _fmt_stat(field, raw):
            if field.endswith("_pct") or field == "faceoff_win_pct":
                try:
                    return f"{int(raw)}%"
                except (TypeError, ValueError):
                    return str(raw)
            return str(raw)

        for i, row in enumerate(visible_stats):
            ry0 = y_bottom_top + i * row_h
            a_val = _fmt_stat(row.field, getattr(away_t, row.field, ""))
            h_val = _fmt_stat(row.field, getattr(home_t, row.field, ""))

<<<<<<< HEAD
            cw_v = val_col_w - 2 * inner_pad
            cw_l = label_col_w - 2 * inner_pad
            ch = row_h - 2 * inner_pad
            target_h = int(ch * 0.65)

            # Away value (in away secondary color)
            fs = _auto_fit_scale(font, a_val, max(1, cw_v), target_h)
            tw, th = font.measure(a_val, scale=fs)
            font.draw(img,
                      x_aval + (val_col_w - tw) // 2,
                      ry0 + (row_h - th) // 2,
                      a_val, away_stat_color, scale=fs)
            # Home value (in home secondary color)
            fs = _auto_fit_scale(font, h_val, max(1, cw_v), target_h)
            tw, th = font.measure(h_val, scale=fs)
            font.draw(img,
                      x_hval + (val_col_w - tw) // 2,
                      ry0 + (row_h - th) // 2,
                      h_val, home_stat_color, scale=fs)
            # Label (white)
            target_lh = int(ch * 0.55)
            fs = _auto_fit_scale(font, row.label, max(1, cw_l), target_lh)
            tw, th = font.measure(row.label, scale=fs)
            font.draw(img,
                      x_lbl + (label_col_w - tw) // 2,
                      ry0 + (row_h - th) // 2,
                      row.label, NEUTRAL_WHITE, scale=fs)
=======
            a_val = _fmt_stat(row.field, getattr(away_t, row.field, ""))
            h_val = _fmt_stat(row.field, getattr(home_t, row.field, ""))

            cells = [
                ((x_stat_a + x_stat_label) // 2, a_val, val_color, val_col_w - 4),
                ((x_stat_label + x_stat_h) // 2, row.label, lbl_color, label_col_w - 4),
                ((x_stat_h + x_stats_right) // 2, h_val, val_color, val_col_w - 4),
            ]
            for x_center, val, color, cell_w in cells:
                s = _auto_fit_scale(label_font, val, max(1, cell_w), max(1, row_h - 2))
                tw, th = label_font.measure(val, scale=s)
                text_y = ry0 + (row_h - th) // 2
                label_font.draw(img, x_center - tw // 2, text_y,
                                val, color, scale=s)

    # ===== Sprites =====
    if L.show_sprites and sprite_w_px > 0:
        stats_h_px = y_stats_bot - y_stats_top

        def _draw_team_sprite(x_origin: int, abbr: str, colors, override, is_away: bool):
            asset_img = None
            # Tier 1: user-uploaded override via Teams panel
            if override and override.sprite_asset and assets_root:
                p = assets_root / "sprites" / override.sprite_asset
                asset_img = sprites.load_sprite_asset(p)
            # Tier 2: bundled per-team PNG at assets/sprites/teams/<ABBREV>.png
            if asset_img is None and assets_root:
                asset_img = sprites.load_team_sprite(assets_root, abbr)
            # Tier 3: procedural pixel art tinted to team colors
            if asset_img is None:
                pixels = project.sprite.pixels or sprites.DEFAULT_PIXELS
                p_, s_, e_ = colors
                asset_img = sprites.render_procedural(
                    pixels, p_.tuple(), s_.tuple(), e_.tuple(), scale=1)

            # Feature 1: standardize all sprites to a fixed canvas (130x200)
            # so every team renders at the same visual size regardless of
            # upload dimensions or aspect ratio.
            asset_img = sprites.pad_to_canvas(asset_img)

            # Feature 2: away-side gets a lighter (away-jersey) tint
            if is_away:
                asset_img = sprites.tint_for_away(asset_img)

            fitted = sprites.fit_sprite(asset_img, sprite_w_px - 4, stats_h_px - 4)
            ox = x_origin + (sprite_w_px - fitted.width) // 2
            oy = y_stats_top + (stats_h_px - fitted.height) // 2
            img.paste(fitted, (ox, oy), fitted if fitted.mode == "RGBA" else None)

        _draw_team_sprite(0, away_t.abbrev, away_colors,
                          project.team_overrides.get(away_t.abbrev),
                          is_away=True)
        _draw_team_sprite(x_stats_right, home_t.abbrev, home_colors,
                          project.team_overrides.get(home_t.abbrev),
                          is_away=False)
>>>>>>> 97a7d31b3014b69ccd02255d28512ad96215a0f3

    return img
