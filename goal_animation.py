"""Goal banner animation generator.

BOOMERANG BEHAVIOR
==================
The sweep enters AND exits on the SCORING TEAM'S side. It does NOT pass
through to the opposite end of the banner.

  {TEAM}_AWAY.gif   sweep enters from LEFT, retreats back to the LEFT
  {TEAM}_HOME.gif   sweep enters from RIGHT, retreats back to the RIGHT

Output goes to:  assets/animations/goal_banner/

Replacing with commissioned GIFs later
--------------------------------------
The runtime engine looks up animations by exact filename:
    assets/animations/goal_banner/{TEAM}_{SIDE}.gif
where SIDE is AWAY or HOME (uppercase). To swap in a commissioned
animation, just drop the new GIF over the existing one keeping the same
filename. Native dimensions are 700x120 (6:1 aspect, matches the banner
row at the default scoreboard resolution). Different sizes will be
resized at runtime but the closer to native the cleaner.

Usage
-----
    # Generate every team, both sides:
    python3 goal_animation.py --all

    # Generate one team, both sides:
    python3 goal_animation.py MIN

    # Generate a single team+side:
    python3 goal_animation.py MIN away
"""
from __future__ import annotations
import argparse
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO / "backend" / "src"))
from nhlsb.core import teams as teams_mod  # noqa: E402

# ---- Configuration ----
WIDTH, HEIGHT = 700, 120
FPS = 40                         # bumped from 30 -> 40 for smoother motion
# Total animation: 0.85s sweep in + 7.0s hold + 0.85s sweep out = 8.7s.
# With 2.0s pre-pulse and 0.5s tail added by renderer = ~11.2s end-to-end event.
DURATION_SEC = 8.7
N_FRAMES = int(FPS * DURATION_SEC)

FONT_PATH = REPO / "assets" / "fonts" / "Anton-Regular.ttf"
BANNER_DIR = REPO / "assets" / "banners" / "teams"
LOGO_DIR = REPO / "assets" / "logos" / "teams"
SWEEP_BG_DIR = REPO / "assets" / "animations" / "sweep_backgrounds"

ANIM_DIR = REPO / "assets" / "animations" / "goal_banner"
ANIM_DIR.mkdir(parents=True, exist_ok=True)

# Phase boundaries (fractions of total animation).
SWEEP_IN_END = 0.85 / 8.7           # ~0.098
TEXT_HOLD_END = (0.85 + 7.0) / 8.7  # ~0.902

# Speed of the GOAL! ticker in pixels per second of animation time.
TICKER_SPEED_PX_PER_SEC = 140

# Diagonal sweep edge softness (px). Larger = softer, more gradient blend.
SWEEP_SLOPE = 110

# How much the leading edge brightens (0-255 added to base color, clipped)
EDGE_HIGHLIGHT = 70


# Chroma key — every pixel in the GIF is either real content (sweep, logo,
# text) or this exact color, with no in-between values. The renderer detects
# this exact color and lets the live banner row show through. Bright magenta
# is used because no NHL team has it as a primary or secondary color.
KEY_COLOR = (255, 0, 255)


# ---- Easings ----
def ease_out_quint(t: float) -> float:
    """Aggressive deceleration — snappy arrival."""
    return 1 - (1 - t) ** 5


def ease_in_quint(t: float) -> float:
    """Aggressive acceleration — snappy departure."""
    return t ** 5


def ease_out_back(t: float, overshoot: float = 1.4) -> float:
    """Slight overshoot then settle — used for logo 'land' bounce."""
    c1 = overshoot
    c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def ease_out_cubic(t: float) -> float:
    return 1 - (1 - t) ** 3


# ---- Diagonal mask for the sweep ----
def diagonal_mask(w: int, h: int, progress: float, slope_px: int = SWEEP_SLOPE,
                  direction: str = "ltr") -> Image.Image:
    """Soft-edged diagonal alpha mask.

    direction='ltr': sweep moves left-to-right (progress=0 = empty,
                     progress=1 = fully covered).
    direction='rtl': mirrored.
    """
    sweep_total = w + slope_px * 2
    edge_x = -slope_px + sweep_total * progress
    slant = h * 0.45
    ys = np.arange(h, dtype=np.float32).reshape(h, 1)
    xs = np.arange(w, dtype=np.float32).reshape(1, w)
    row_edge = edge_x + slant * (ys / h - 0.5)
    if direction == "ltr":
        alpha = np.clip((row_edge - xs + slope_px / 2) / slope_px, 0.0, 1.0)
    else:
        alpha = np.clip((xs - (w - row_edge) + slope_px / 2) / slope_px, 0.0, 1.0)
    return Image.fromarray((alpha * 255).astype(np.uint8), mode="L")


def edge_highlight_mask(w: int, h: int, progress: float, slope_px: int = SWEEP_SLOPE,
                        direction: str = "ltr", band_px: int = 30) -> Image.Image:
    """A thin bright band along the sweep's leading edge for shimmer."""
    sweep_total = w + slope_px * 2
    edge_x = -slope_px + sweep_total * progress
    slant = h * 0.45
    ys = np.arange(h, dtype=np.float32).reshape(h, 1)
    xs = np.arange(w, dtype=np.float32).reshape(1, w)
    row_edge = edge_x + slant * (ys / h - 0.5)
    if direction == "ltr":
        d = xs - row_edge
    else:
        d = (w - row_edge) - xs
    band = np.exp(-(d * d) / (2 * (band_px / 2.5) ** 2))
    return Image.fromarray((band * 255).astype(np.uint8), mode="L")


# ---- Banner strip background ----
def build_banner_strip(team: str, side: str) -> Image.Image:
    """Return a fully chroma-keyed background. The renderer will mask out
    these pixels and let whatever's actually in the live banner row show
    through. That way both teams' banners stay visible during the whole
    animation; the GIF only contributes the colored sweep, the logo, and
    the GOAL! text on top of the live banners.
    """
    return Image.new("RGB", (WIDTH, HEIGHT), KEY_COLOR)


def load_logo(team: str, target_h: int) -> Image.Image | None:
    path = LOGO_DIR / f"{team}.png"
    if not path.exists():
        return None
    logo = Image.open(path).convert("RGBA")
    scale = target_h / logo.height
    new_w = max(1, int(logo.width * scale))
    return logo.resize((new_w, target_h), Image.Resampling.LANCZOS)


def load_sweep_background(team: str) -> Image.Image | None:
    """Look for assets/animations/sweep_backgrounds/<TEAM>.png. If found,
    return it scaled+cropped to (WIDTH, HEIGHT) as RGB. Used as the sweep
    fill instead of the solid team primary color.

    Returns None if no file exists; caller falls back to solid color.
    """
    path = SWEEP_BG_DIR / f"{team}.png"
    if not path.exists():
        return None
    img = Image.open(path).convert("RGB")
    # Cover-fit: scale so the image fills the banner, then center-crop
    target_ratio = WIDTH / HEIGHT
    src_ratio = img.width / img.height
    if src_ratio > target_ratio:
        # source is wider — scale by height, crop sides
        new_h = HEIGHT
        new_w = max(1, int(img.width * (HEIGHT / img.height)))
    else:
        # source is taller — scale by width, crop top/bottom
        new_w = WIDTH
        new_h = max(1, int(img.height * (WIDTH / img.width)))
    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    # center crop
    left = (new_w - WIDTH) // 2
    top = (new_h - HEIGHT) // 2
    return img.crop((left, top, left + WIDTH, top + HEIGHT))


def _scale_logo(logo: Image.Image, scale: float) -> Image.Image:
    if abs(scale - 1.0) < 0.005:
        return logo
    nw = max(1, int(logo.width * scale))
    nh = max(1, int(logo.height * scale))
    return logo.resize((nw, nh), Image.Resampling.LANCZOS)


# ---- Frame renderer ----
def render_frame(team: str, side: str, frame_idx: int, n_frames: int,
                 background: Image.Image, base_logo: Image.Image | None,
                 sweep_bg: Image.Image | None = None) -> Image.Image:
    """Render one frame as RGBA. Pixels OUTSIDE the sweep/logo/text are fully
    transparent so the live banner row shows through underneath.

    sweep_bg: optional RGB image at (WIDTH, HEIGHT). When provided, the sweep
    reveals this image instead of a solid team-color fill.
    """
    if side not in ("away", "home"):
        raise ValueError("side must be 'away' or 'home'")

    primary, secondary, _ = teams_mod.colors_for(team, None)
    color_main = (primary.r, primary.g, primary.b)
    color_outline = (secondary.r, secondary.g, secondary.b)
    edge_color = tuple(min(255, c + EDGE_HIGHLIGHT) for c in color_main)

    # Fully transparent canvas
    canvas = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    direction = "ltr" if side == "away" else "rtl"
    t = frame_idx / max(1, n_frames - 1)

    # ---- Stage 1: sweep band ----
    # Logo rides in WITH the sweep (no separate pop phase).
    # Boomerang behavior: sweep enters and exits on the same side.
    if t <= SWEEP_IN_END:
        # Quintic-out: snappy deceleration, matches the reference pacing
        local = t / SWEEP_IN_END
        p = 1 - (1 - local) ** 5
        mask = diagonal_mask(WIDTH, HEIGHT, p, direction=direction)
        edge_p, edge_strength = p, max(0.0, 1.0 - p)
    elif t <= TEXT_HOLD_END:
        mask = Image.new("L", (WIDTH, HEIGHT), 255)
        edge_p, edge_strength = 1.0, 0.0
    else:
        # Symmetric exit: quintic-in
        local = (t - TEXT_HOLD_END) / (1.0 - TEXT_HOLD_END)
        p = local ** 5
        mask = diagonal_mask(WIDTH, HEIGHT, 1.0 - p, direction=direction)
        edge_p, edge_strength = 1.0 - p, max(0.0, p)

    # Build sweep layer. If a per-team background image is supplied, the
    # sweep reveals THAT instead of the solid color. Either way the diagonal
    # mask becomes the layer's alpha.
    if sweep_bg is not None:
        sweep_rgba = sweep_bg.convert("RGBA")
    else:
        sweep_rgba = Image.new("RGBA", (WIDTH, HEIGHT), (*color_main, 0))
    sweep_rgba.putalpha(mask)
    canvas.alpha_composite(sweep_rgba)

    # Leading-edge shimmer (only during sweep phases, not the hold)
    if edge_strength > 0.05 and 0.0 < edge_p < 1.0:
        hi_mask = edge_highlight_mask(WIDTH, HEIGHT, edge_p, direction=direction)
        hi_mask = hi_mask.point(lambda v, s=edge_strength: int(v * s))
        hi_rgba = Image.new("RGBA", (WIDTH, HEIGHT), (*edge_color, 0))
        hi_rgba.putalpha(hi_mask)
        canvas.alpha_composite(hi_rgba)

    # ---- Stage 2: ride-along logo ----
    # Logo slides in with the sweep, settles at rest position during hold,
    # slides back out as the sweep retreats.
    logo = base_logo
    if logo is not None:
        logo_h = logo.height
        logo_w = logo.width
        if direction == "ltr":
            logo_rest_x = int(WIDTH * 0.10)
            logo_start_x = -logo_w
        else:
            logo_rest_x = WIDTH - logo_w - int(WIDTH * 0.10)
            logo_start_x = WIDTH

        if t <= SWEEP_IN_END:
            local = t / SWEEP_IN_END
            p = 1 - (1 - local) ** 5   # quintic-out, matches sweep
            logo_x = int(logo_start_x + (logo_rest_x - logo_start_x) * p)
            logo_alpha = int(255 * min(1.0, p * 1.6))
            scale = 1.0
        elif t <= TEXT_HOLD_END:
            scale = 1.0
            logo_x = logo_rest_x
            logo_alpha = 255
        else:
            local = (t - TEXT_HOLD_END) / (1.0 - TEXT_HOLD_END)
            p = local ** 5   # quintic-in, matches sweep exit
            logo_x = int(logo_rest_x + (logo_start_x - logo_rest_x) * p)
            logo_alpha = int(255 * (1.0 - p))
            scale = 1.0

        if logo_alpha > 4:
            scaled = _scale_logo(logo, scale)
            sx = logo_x - (scaled.width - logo_w) // 2
            sy = (HEIGHT - scaled.height) // 2
            if logo_alpha < 255:
                a = scaled.split()[3].point(lambda v, m=logo_alpha: int(v * m / 255))
                scaled = scaled.copy()
                scaled.putalpha(a)
            canvas.alpha_composite(scaled, (sx, sy))

    # ---- Stage 3: GOAL! ticker ----
    # Multiple "GOAL!" tokens scroll across the banner during the hold phase,
    # going the same direction as the sweep entry (LTR for AWAY, RTL for HOME).
    if t <= SWEEP_IN_END:
        # Fade in as sweep enters
        local = t / SWEEP_IN_END
        text_alpha = max(0.0, (local - 0.4) / 0.6)
    elif t <= TEXT_HOLD_END:
        text_alpha = 1.0
    else:
        p = (t - TEXT_HOLD_END) / (1.0 - TEXT_HOLD_END)
        text_alpha = max(0.0, 1.0 - p * 1.4)

    if text_alpha > 0.02:
        try:
            text_font = ImageFont.truetype(str(FONT_PATH), 84)
        except Exception:
            text_font = ImageFont.load_default()

        text = "GOAL!"
        text_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        d = ImageDraw.Draw(text_layer)
        bbox = d.textbbox((0, 0), text, font=text_font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

        # Spacing between repeating GOAL! tokens. Tight enough that there's
        # always at least one visible at any moment, loose enough to read.
        token_spacing = tw + 80  # gap between GOAL!s
        n_tokens = (WIDTH // token_spacing) + 4  # extra so we always have a
                                                  # token wrapping in/out

        # Reserve the logo area so text doesn't run over it.
        # Ticker scrolls TOWARD the logo: logo is on the left for AWAY
        # team, so ticker flows leftward; logo is on the right for HOME
        # team, so ticker flows rightward.
        if logo is not None and direction == "ltr":
            ticker_x_start = int(WIDTH * 0.10) + logo.width + 30
            ticker_x_end = WIDTH
            scroll_dir = -1  # tokens move RTL (toward left-side logo)
        elif logo is not None and direction == "rtl":
            ticker_x_start = 0
            ticker_x_end = WIDTH - int(WIDTH * 0.10) - logo.width - 30
            scroll_dir = 1   # tokens move LTR (toward right-side logo)
        else:
            ticker_x_start = 0
            ticker_x_end = WIDTH
            scroll_dir = -1 if direction == "ltr" else 1

        ticker_w = max(1, ticker_x_end - ticker_x_start)

        # Position is driven by elapsed seconds since animation started.
        elapsed_hold = t * (n_frames / FPS)
        offset = (elapsed_hold * TICKER_SPEED_PX_PER_SEC) % token_spacing

        a = int(255 * text_alpha)

        # Draw each token in the visible window. We render to a wide temp
        # layer then mask it down to the ticker region, so tokens that exit
        # one side cleanly fade off the edge instead of wrapping mid-text.
        ticker_layer = Image.new("RGBA", (ticker_w, HEIGHT), (0, 0, 0, 0))
        td = ImageDraw.Draw(ticker_layer)
        y = (HEIGHT - th) // 2 - bbox[1]

        for i in range(-2, n_tokens):
            if scroll_dir > 0:
                # LTR: tokens slide from left to right; offset moves them right
                base_x = i * token_spacing - offset
            else:
                # RTL: tokens slide from right to left
                base_x = ticker_w - tw - (i * token_spacing - offset)

            x = int(base_x)
            # Skip tokens entirely off-screen
            if x + tw < -20 or x > ticker_w + 20:
                continue

            # Drop shadow
            for dx, dy, sa in [(3, 3, 180), (2, 2, 200)]:
                td.text((x + dx, y + dy), text, font=text_font,
                        fill=(0, 0, 0, int(sa * text_alpha)))
            # Outline
            for ox, oy in [(-2, 0), (2, 0), (0, -2), (0, 2),
                           (-2, -2), (2, -2), (-2, 2), (2, 2)]:
                td.text((x + ox, y + oy), text, font=text_font,
                        fill=(*color_outline, a))
            # Fill
            td.text((x, y), text, font=text_font, fill=(255, 255, 255, a))

        text_layer.alpha_composite(ticker_layer, (ticker_x_start, 0))
        canvas.alpha_composite(text_layer)

    return canvas  # RGBA


# ---- GIF writer ----
def _flatten_to_key(rgba: Image.Image) -> Image.Image:
    """Hard-threshold alpha and composite onto KEY_COLOR. Result is RGB with
    every pixel either real content (alpha was >= 128) or exact KEY_COLOR
    (alpha was < 128). No in-between values, so chroma keying is reliable."""
    alpha = rgba.split()[3].point(lambda v: 255 if v >= 128 else 0)
    rgb = rgba.convert("RGB")
    bg = Image.new("RGB", rgba.size, KEY_COLOR)
    return Image.composite(rgb, bg, alpha)


def make_gif(team: str, side: str, out_dir: Path) -> Path:
    bg = build_banner_strip(team, side)
    base_logo = load_logo(team, int(HEIGHT * 0.78))
    sweep_bg = load_sweep_background(team)
    rgba_frames = [render_frame(team, side, i, N_FRAMES,
                                background=bg, base_logo=base_logo,
                                sweep_bg=sweep_bg)
                   for i in range(N_FRAMES)]
    # Final hold on a fully transparent (= fully keyed) frame so the live
    # banners are clean and unobstructed at the end of the loop.
    blank = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    for _ in range(int(FPS * 0.5)):
        rgba_frames.append(blank)

    # Flatten to RGB with hard chroma-key edges
    rgb_frames = [_flatten_to_key(f) for f in rgba_frames]

    out_path = out_dir / f"{team}_{side.upper()}.gif"
    duration_ms = int(1000 / FPS)
    rgb_frames[0].save(
        out_path, save_all=True, append_images=rgb_frames[1:],
        duration=duration_ms, optimize=True,
        # No loop=0 — we want the GIF to play once and stop. The live engine
        # plays it through its own elapsed-time gate (also one-shot), so this
        # only affects standalone GIF previews in browsers / file viewers.
    )
    return out_path


# ---- 32-team list (drives --all) ----
ALL_TEAMS = [
    "ANA", "BOS", "BUF", "CAR", "CBJ", "CGY", "CHI", "COL",
    "DAL", "DET", "EDM", "FLA", "LAK", "MIN", "MTL", "NJD",
    "NSH", "NYI", "NYR", "OTT", "PHI", "PIT", "SEA", "SJS",
    "STL", "TBL", "TOR", "UTA", "VAN", "VGK", "WPG", "WSH",
]


def write_readme(out_dir: Path):
    """Drop a README in the animations folder explaining how to swap files."""
    readme = out_dir / "README.txt"
    readme.write_text(
        "Goal banner animations\n"
        "======================\n\n"
        "Files in this folder play when a goal is detected via the NHL API.\n"
        "Naming: {TEAM}_{SIDE}.gif  (e.g. MIN_AWAY.gif, EDM_HOME.gif)\n"
        "  TEAM = 3-letter abbreviation\n"
        "  SIDE = AWAY when away team scores, HOME when home team scores\n\n"
        "Direction (BOOMERANG):\n"
        "  AWAY goal: sweep enters from LEFT, exits LEFT (scoring team's side)\n"
        "  HOME goal: sweep enters from RIGHT, exits RIGHT (scoring team's side)\n\n"
        "To replace any animation with a commissioned one, drop a GIF with\n"
        "the SAME filename here. Default size is 700x120 (6:1 aspect); other\n"
        "sizes will be resized at runtime.\n\n"
        "Re-generating the defaults:\n"
        "  python3 goal_animation.py --all\n"
        "Single team:\n"
        "  python3 goal_animation.py MIN\n"
        "Single team+side:\n"
        "  python3 goal_animation.py MIN away\n"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("team", nargs="?", help="3-letter team abbrev (or omit + use --all)")
    parser.add_argument("side", nargs="?", choices=["away", "home"],
                        help="Optional: only generate this side")
    parser.add_argument("--all", action="store_true",
                        help="Generate all 32 teams x both sides (64 GIFs)")
    parser.add_argument("--out", type=Path, default=ANIM_DIR,
                        help="Output directory (default: assets/animations/goal_banner/)")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    write_readme(args.out)

    targets: list[tuple[str, str]] = []
    if args.all:
        for t in ALL_TEAMS:
            targets.append((t, "away"))
            targets.append((t, "home"))
    elif args.team:
        sides = [args.side] if args.side else ["away", "home"]
        for s in sides:
            targets.append((args.team.upper(), s))
    else:
        parser.error("provide a team, or use --all")

    for i, (team, side) in enumerate(targets, 1):
        try:
            out = make_gif(team, side, args.out)
            sz = out.stat().st_size
            print(f"  [{i:2}/{len(targets)}] {out.name}  ({sz // 1024} KB)")
        except Exception as e:
            print(f"  [{i:2}/{len(targets)}] FAILED {team}_{side.upper()}: {e}")

    print(f"\nDone. {len(targets)} animations written to {args.out}")


if __name__ == "__main__":
    main()
