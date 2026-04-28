"""Data-driven scoreboard renderer.

Pure function: (Project, GameState) -> PIL.Image
All visual decisions come from project.theme and project.layout.
"""
from __future__ import annotations
from PIL import Image
from pathlib import Path

from . import seg, sprites, teams
from .fonts import get_font
from .models import GameState, Project, Layout, Theme


def _hline(img, x0, x1, y, color):
    px = img.load(); W, H = img.size
    if not (0 <= y < H): return
    for x in range(max(0, x0), min(W, x1)): px[x, y] = color


def _vline(img, x, y0, y1, color):
    px = img.load(); W, H = img.size
    if not (0 <= x < W): return
    for y in range(max(0, y0), min(H, y1)): px[x, y] = color


def _rect_fill(img, x0, y0, x1, y1, color):
    px = img.load(); W, H = img.size
    for y in range(max(0, y0), min(H, y1)):
        for x in range(max(0, x0), min(W, x1)):
            px[x, y] = color


def _auto_fit_scale(font, text, max_w, max_h, max_scale=None):
    """Bug 7: Pick the largest integer scale where `text` fits in (max_w, max_h).
    Returns scale >= 1. If even scale=1 overflows, returns 1 anyway (caller
    decides whether to clip).
    """
    if not text:
        return 1
    cap = max_scale if max_scale is not None else 64
    for s in range(cap, 0, -1):
        w, h = font.measure(text, scale=s)
        if w <= max_w and h <= max_h:
            return s
    return 1


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


def render(project: Project, state: GameState,
           assets_root: Path | None = None) -> Image.Image:
    L: Layout = project.layout
    T: Theme = project.theme
    W, H = L.width, L.height
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

    away_t = state.away
    home_t = state.home
    away_colors = teams.colors_for(away_t.abbrev,
                                   project.team_overrides.get(away_t.abbrev))
    home_colors = teams.colors_for(home_t.abbrev,
                                   project.team_overrides.get(home_t.abbrev))

    label_font = get_font(T.label_font)
    team_font = get_font(T.team_font)

    # ===== Score row =====
    score_h = max(0, y_score_bot - y_score_top)
    score_color = T.score_color.tuple()
    half_w = (W // 2) - 4   # margin per side

    for half_x_start, half_x_end, score_val in [
        (0, x_mid, away_t.score),
        (x_mid, W, home_t.score),
    ]:
        s = f"{score_val:02d}"
        cell_w = (half_x_end - half_x_start) - 6
        digit_w, digit_h, gap, thickness = _fit_segment_size(s, cell_w, score_h - 4)
        total_w = len(s) * digit_w + (len(s) - 1) * gap
        x_o = half_x_start + (half_x_end - half_x_start - total_w) // 2
        y_o = y_score_top + (score_h - digit_h) // 2
        seg.draw_number(img, x_o, y_o, s, digit_w, digit_h, score_color,
                        gap=gap, thickness=thickness)

    grid_score = T.grid_score.tuple()
    _hline(img, 0, W, y_score_top - 2, grid_score)
    _hline(img, 0, W, y_score_bot, grid_score)
    _vline(img, 0, y_score_top - 2, y_score_bot + 1, grid_score)
    _vline(img, W - 1, y_score_top - 2, y_score_bot + 1, grid_score)
    _vline(img, x_mid, y_score_top - 2, y_score_bot + 1, grid_score)

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

    grid = T.grid.tuple()
    _hline(img, 0, W, y_team_bot, grid)
    _vline(img, x_mid, y_team_top, y_team_bot, grid)
    _vline(img, 0, y_team_top, y_team_bot, grid)
    _vline(img, W - 1, y_team_top, y_team_bot, grid)

    # ===== PEN. | period | PEN. =====
    pen_h_px = max(0, y_pen_lbl_b - y_pen_top)
    period_color = T.period_color.tuple()

    if L.show_pen_indicators:
        x_pen_l_end = sprite_w_px + (W - 2 * sprite_w_px) // 4
        x_pen_r_start = W - sprite_w_px - (W - 2 * sprite_w_px) // 4
    else:
        x_pen_l_end = 0
        x_pen_r_start = W

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
    visible_stats = [s for s in L.stats if s.enabled]
    if visible_stats:
        stats_h_px = y_stats_bot - y_stats_top
        row_h = stats_h_px // len(visible_stats)
        label_col_w = int((x_stats_right - x_stats_left) * 0.55)
        val_col_w = (x_stats_right - x_stats_left - label_col_w) // 2
        x_stat_a     = x_stats_left
        x_stat_label = x_stat_a + val_col_w
        x_stat_h     = x_stat_label + label_col_w

        _vline(img, x_stats_left, y_stats_top, y_stats_bot + 1, grid)
        _vline(img, x_stats_right, y_stats_top, y_stats_bot + 1, grid)
        _vline(img, x_stat_label, y_stats_top, y_stats_bot + 1, grid)
        _vline(img, x_stat_h, y_stats_top, y_stats_bot + 1, grid)
        _vline(img, 0, y_stats_top, y_stats_bot + 1, grid)
        _vline(img, W - 1, y_stats_top, y_stats_bot + 1, grid)

        val_color = T.stat_value_color.tuple()
        lbl_color = T.stat_label_color.tuple()

        # Helper: format value with % suffix for percentage-style fields
        def _fmt_stat(field, raw):
            if field.endswith("_pct") or field == "faceoff_win_pct":
                try:
                    return f"{int(raw)}%"
                except (TypeError, ValueError):
                    return str(raw)
            return str(raw)

        for i, row in enumerate(visible_stats):
            ry0 = y_stats_top + i * row_h
            if i > 0:
                _hline(img, x_stats_left, x_stats_right, ry0, grid)

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

    return img
