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
        w, h = font.measure(text, scale=s)
        if w <= max_w and h <= max_h:
            return s
    return 1


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

def render(project: Project, state: GameState,
           assets_root: Path | None = None) -> Image.Image:
    L: Layout = project.layout
    T: Theme = project.theme
    W, H = L.width, L.height

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

    img = Image.new("RGB", (W, H), rc.background)

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

    # ============================================================
    #  ROW 2 - SINGLE STITCHED BANNER (both teams, no break in middle)
    # ============================================================
    banner_h = max(0, y_banner_bot - y_banner_top)

    # Outer rectangle for the whole banner row, single border
    bx0, bx1 = pad, W - pad
    by0, by1 = y_banner_top, y_banner_bot

    # Inner area inside the border
    inner_x0 = bx0 + border_w
    inner_x1 = bx1 - border_w
    inner_y0 = by0 + border_w
    inner_y1 = by1 - border_w
    inner_w = inner_x1 - inner_x0
    inner_h = inner_y1 - inner_y0

    # Each half of the inner area gets one team's banner
    half_w = inner_w // 2
    away_x0 = inner_x0
    away_x1 = inner_x0 + half_w
    home_x0 = away_x1
    home_x1 = inner_x1

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

        for i, row in enumerate(visible_stats):
            ry0 = y_bottom_top + i * row_h
            a_val = _fmt_stat(row.field, getattr(away_t, row.field, ""))
            h_val = _fmt_stat(row.field, getattr(home_t, row.field, ""))

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

    return img
