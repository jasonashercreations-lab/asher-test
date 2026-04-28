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


def render(project: Project, state: GameState,
           assets_root: Path | None = None) -> Image.Image:
    L: Layout = project.layout
    T: Theme = project.theme
    W, H = L.width, L.height
    img = Image.new("RGB", (W, H), T.bg.tuple())

    # Compute vertical region boundaries from layout fractions
    y0 = 0
    y_score_top = y0 + 2
    y_score_bot = y0 + int(H * L.score_h)
    y_team_top  = y_score_bot + 2
    y_team_bot  = y_team_top + int(H * L.team_h)
    y_pen_top   = y_team_bot + 1
    y_pen_lbl_b = y_pen_top + int(H * L.pen_label_h)
    y_pen_box_b = y_pen_lbl_b + int(H * L.pen_box_h)
    y_clock_top = y_pen_box_b + 2
    y_clock_bot = y_clock_top + int(H * L.clock_h)
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
    score_h = y_score_bot - y_score_top
    digit_h = int(score_h * 0.92)
    digit_w = int(digit_h * 0.62)
    thickness = max(2, digit_h // 7)
    score_color = T.score_color.tuple()

    for half_x_start, half_x_end, score_val in [
        (0, x_mid, away_t.score),
        (x_mid, W, home_t.score),
    ]:
        s = f"{score_val:02d}"
        gap = max(2, digit_w // 5)
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
    team_h_px = y_team_bot - y_team_top
    abbr_scale = max(1, team_h_px // 9)
    team_color = T.team_color.tuple()
    aw, ah = team_font.measure(away_t.abbrev, scale=abbr_scale)
    hw, hh = team_font.measure(home_t.abbrev, scale=abbr_scale)
    team_font.draw(img, (x_mid - aw) // 2, y_team_top + (team_h_px - ah) // 2,
                   away_t.abbrev, team_color, scale=abbr_scale)
    team_font.draw(img, x_mid + (W - x_mid - hw) // 2,
                   y_team_top + (team_h_px - hh) // 2,
                   home_t.abbrev, team_color, scale=abbr_scale)

    grid = T.grid.tuple()
    _hline(img, 0, W, y_team_bot, grid)
    _vline(img, x_mid, y_team_top, y_team_bot, grid)
    _vline(img, 0, y_team_top, y_team_bot, grid)
    _vline(img, W - 1, y_team_top, y_team_bot, grid)

    # ===== PEN. | period | PEN. =====
    pen_h_px = y_pen_lbl_b - y_pen_top
    lbl_scale = max(1, pen_h_px // 9)
    period_color = T.period_color.tuple()

    if L.show_pen_indicators:
        x_pen_l_end = sprite_w_px + (W - 2 * sprite_w_px) // 4
        x_pen_r_start = W - sprite_w_px - (W - 2 * sprite_w_px) // 4
    else:
        x_pen_l_end = 0
        x_pen_r_start = W

    if L.show_pen_indicators:
        for x_center, label in [
            (x_pen_l_end // 2, "PEN."),
            ((x_pen_r_start + W) // 2, "PEN."),
        ]:
            tw, th = label_font.measure(label, scale=lbl_scale)
            label_font.draw(img, x_center - tw // 2,
                            y_pen_top + (pen_h_px - th) // 2,
                            label, team_color, scale=lbl_scale)

    pcw, pch = label_font.measure(state.period_label, scale=lbl_scale)
    label_font.draw(img, (x_pen_l_end + x_pen_r_start) // 2 - pcw // 2,
                    y_pen_top + (pen_h_px - pch) // 2,
                    state.period_label, period_color, scale=lbl_scale)

    _hline(img, 0, W, y_pen_lbl_b, grid)
    if L.show_pen_indicators:
        _vline(img, x_pen_l_end, y_team_bot, y_pen_box_b, grid)
        _vline(img, x_pen_r_start, y_team_bot, y_pen_box_b, grid)
    _vline(img, 0, y_team_bot, y_pen_box_b, grid)
    _vline(img, W - 1, y_team_bot, y_pen_box_b, grid)

    if L.show_pen_indicators:
        if away_t.penalty_active:
            _rect_fill(img, 2, y_pen_lbl_b + 2, x_pen_l_end - 1,
                       y_pen_box_b - 1, T.penalty_active_color.tuple())
        if home_t.penalty_active:
            _rect_fill(img, x_pen_r_start + 1, y_pen_lbl_b + 2, W - 2,
                       y_pen_box_b - 1, T.penalty_active_color.tuple())

    # ===== Clock =====
    clock_h_px = y_clock_bot - y_clock_top
    cdh = int(clock_h_px * 0.92)
    cdw = int(cdh * 0.55)
    cthick = max(2, cdh // 7)
    cgap = max(2, cdw // 5)
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

        val_scale = max(1, row_h // 9)
        val_color = T.stat_value_color.tuple()
        lbl_color = T.stat_label_color.tuple()

        for i, row in enumerate(visible_stats):
            ry0 = y_stats_top + i * row_h
            if i > 0:
                _hline(img, x_stats_left, x_stats_right, ry0, grid)

            text_y = ry0 + (row_h - val_scale * 7) // 2
            a_val = str(getattr(away_t, row.field, ""))
            h_val = str(getattr(home_t, row.field, ""))

            for x_center, val, color in [
                ((x_stat_a + x_stat_label) // 2, a_val, val_color),
                ((x_stat_label + x_stat_h) // 2, row.label, lbl_color),
                ((x_stat_h + x_stats_right) // 2, h_val, val_color),
            ]:
                tw, th = label_font.measure(val, scale=val_scale)
                label_font.draw(img, x_center - tw // 2, text_y,
                                val, color, scale=val_scale)

    # ===== Sprites =====
    if L.show_sprites and sprite_w_px > 0:
        stats_h_px = y_stats_bot - y_stats_top

        def _draw_team_sprite(x_origin: int, abbr: str, colors, override):
            asset_img = None
            if override and override.sprite_asset and assets_root:
                p = assets_root / "sprites" / override.sprite_asset
                asset_img = sprites.load_sprite_asset(p)
            if asset_img is None:
                pixels = project.sprite.pixels or sprites.DEFAULT_PIXELS
                p_, s_, e_ = colors
                asset_img = sprites.render_procedural(
                    pixels, p_.tuple(), s_.tuple(), e_.tuple(), scale=1)
            fitted = sprites.fit_sprite(asset_img, sprite_w_px - 4, stats_h_px - 4)
            ox = x_origin + (sprite_w_px - fitted.width) // 2
            oy = y_stats_top + (stats_h_px - fitted.height) // 2
            img.paste(fitted, (ox, oy), fitted if fitted.mode == "RGBA" else None)

        _draw_team_sprite(0, away_t.abbrev, away_colors,
                          project.team_overrides.get(away_t.abbrev))
        _draw_team_sprite(x_stats_right, home_t.abbrev, home_colors,
                          project.team_overrides.get(home_t.abbrev))

    return img
