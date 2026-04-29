"""Goal banner animation generator (banner-strip overlay only).

For each team, generates two GIFs:
   {TEAM}_AWAY.gif   - sweep enters from LEFT, exits LEFT  (away goal)
   {TEAM}_HOME.gif   - sweep enters from RIGHT, exits RIGHT (home goal)

Output goes to:  assets/animations/goal_banner/

Replacing with commissioned GIFs later
--------------------------------------
The runtime engine looks up animations by exact filename:
    assets/animations/goal_banner/{TEAM}_{SIDE}.gif
where SIDE is AWAY or HOME (uppercase). To swap in a commissioned
animation, just drop the new GIF over the existing one keeping the same
filename. The dimensions should be 700x120 (6:1 aspect, matches the
banner row at the default scoreboard resolution). Different sizes will be
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
from PIL import Image, ImageDraw, ImageFont


REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO / "backend" / "src"))
from nhlsb.core import teams as teams_mod  # noqa: E402

# ---- Configuration ----
WIDTH, HEIGHT = 700, 120
FPS = 30
DURATION_SEC = 2.5
N_FRAMES = int(FPS * DURATION_SEC)

FONT_PATH = REPO / "assets" / "fonts" / "Anton-Regular.ttf"
BANNER_DIR = REPO / "assets" / "banners" / "teams"
LOGO_DIR = REPO / "assets" / "logos" / "teams"

# Animations live alongside the other assets so they ship with the project
# and customers / you can drop replacement GIFs into the same folder.
ANIM_DIR = REPO / "assets" / "animations" / "goal_banner"
ANIM_DIR.mkdir(parents=True, exist_ok=True)

# Phase boundaries (fractions of total animation)
SWEEP_IN_END = 0.30
TEXT_HOLD_END = 0.65


# ---- Easings ----
def ease_out_cubic(t: float) -> float:
    return 1 - (1 - t) ** 3


def ease_in_cubic(t: float) -> float:
    return t ** 3


# ---- Diagonal mask for the sweep ----
def diagonal_mask(w: int, h: int, progress: float, slope_px: int = 80,
                  direction: str = "ltr") -> Image.Image:
    """Soft-edged diagonal alpha mask.

    direction='ltr': sweep moves left-to-right (progress=0 = empty,
                     progress=1 = fully covered).
    direction='rtl': mirrored.
    """
    sweep_total = w + slope_px * 2
    edge_x = -slope_px + sweep_total * progress
    slant = h * 0.4
    ys = np.arange(h, dtype=np.float32).reshape(h, 1)
    xs = np.arange(w, dtype=np.float32).reshape(1, w)
    row_edge = edge_x + slant * (ys / h - 0.5)
    if direction == "ltr":
        alpha = np.clip((row_edge - xs + slope_px / 2) / slope_px, 0.0, 1.0)
    else:
        alpha = np.clip((xs - (w - row_edge) + slope_px / 2) / slope_px, 0.0, 1.0)
    return Image.fromarray((alpha * 255).astype(np.uint8), mode="L")


# ---- Banner strip background ----
def build_banner_strip(team: str, side: str) -> Image.Image:
    """Compose a banner row using both teams' actual banners. The team
    on its own side (left for away, right for home) sits on the side it
    would in the live scoreboard. The OTHER side is filled with a neutral
    teammate (we use the league logo or a generic dark fill if no real
    opponent context is supplied for the GIF preview).

    For the GIF previews we use a dark neutral on the non-scoring side so
    the focus is on the team that scored. Live integration just paints
    the sweep over whatever's actually in the banner row at goal time.
    """
    bg = Image.new("RGB", (WIDTH, HEIGHT), (10, 10, 12))
    half = WIDTH // 2

    # Locate the banner. Banners are HOME variant when the team is home,
    # AWAY when away.
    banner_filename = f"{team}_{'HOME' if side == 'home' else 'AWAY'}.png"
    banner_path = BANNER_DIR / banner_filename
    if not banner_path.exists():
        # Fall back to the other variant
        banner_path = BANNER_DIR / f"{team}_HOME.png"
    if banner_path.exists():
        banner = Image.open(banner_path).convert("RGB")
        scaled = banner.resize((half, HEIGHT), Image.Resampling.LANCZOS)
        if side == "away":
            # Scoring team (away) sits on the left
            bg.paste(scaled, (0, 0))
            # Right side: neutral dark
            ImageDraw.Draw(bg).rectangle([half, 0, WIDTH, HEIGHT],
                                         fill=(18, 18, 20))
        else:
            # Scoring team (home) sits on the right
            bg.paste(scaled, (half, 0))
            ImageDraw.Draw(bg).rectangle([0, 0, half, HEIGHT],
                                         fill=(18, 18, 20))
    return bg


def load_logo(team: str, target_h: int) -> Image.Image | None:
    path = LOGO_DIR / f"{team}.png"
    if not path.exists():
        return None
    logo = Image.open(path).convert("RGBA")
    scale = target_h / logo.height
    new_w = max(1, int(logo.width * scale))
    return logo.resize((new_w, target_h), Image.Resampling.LANCZOS)


# ---- Frame renderer ----
def render_frame(team: str, side: str, frame_idx: int, n_frames: int,
                 background: Image.Image) -> Image.Image:
    """Render one frame of the goal animation."""
    if side not in ("away", "home"):
        raise ValueError("side must be 'away' or 'home'")

    primary, secondary, _ = teams_mod.colors_for(team, None)
    color_main = (primary.r, primary.g, primary.b)
    color_outline = (secondary.r, secondary.g, secondary.b)

    canvas = background.copy()
    direction = "ltr" if side == "away" else "rtl"
    t = frame_idx / max(1, n_frames - 1)

    # ---- Stage 1: sweep band ----
    if t <= SWEEP_IN_END:
        p = ease_out_cubic(t / SWEEP_IN_END)
        mask = diagonal_mask(WIDTH, HEIGHT, p, slope_px=80, direction=direction)
    elif t <= TEXT_HOLD_END:
        mask = Image.new("L", (WIDTH, HEIGHT), 255)
    else:
        p = ease_in_cubic((t - TEXT_HOLD_END) / (1.0 - TEXT_HOLD_END))
        mask = diagonal_mask(WIDTH, HEIGHT, 1.0 - p, slope_px=80, direction=direction)

    color_layer = Image.new("RGB", (WIDTH, HEIGHT), color_main)
    canvas.paste(color_layer, (0, 0), mask)

    # ---- Stage 2: ride-along logo ----
    logo_h = int(HEIGHT * 0.78)
    logo = load_logo(team, logo_h)
    if logo is not None:
        if direction == "ltr":
            logo_rest_x = int(WIDTH * 0.10)
            logo_start_x = -logo.width
        else:
            logo_rest_x = WIDTH - logo.width - int(WIDTH * 0.10)
            logo_start_x = WIDTH

        if t <= SWEEP_IN_END:
            p = ease_out_cubic(t / SWEEP_IN_END)
            logo_x = int(logo_start_x + (logo_rest_x - logo_start_x) * p)
            logo_alpha = int(255 * min(1.0, p * 1.5))
        elif t <= TEXT_HOLD_END:
            logo_x = logo_rest_x
            logo_alpha = 255
        else:
            p = ease_in_cubic((t - TEXT_HOLD_END) / (1.0 - TEXT_HOLD_END))
            logo_x = int(logo_rest_x + (logo_start_x - logo_rest_x) * p)
            logo_alpha = int(255 * (1.0 - p))

        if logo_alpha > 4:
            logo_layer = logo.copy()
            if logo_alpha < 255:
                a = logo_layer.split()[3]
                a = a.point(lambda v, m=logo_alpha: int(v * m / 255))
                logo_layer.putalpha(a)
            logo_y = (HEIGHT - logo.height) // 2
            canvas_rgba = canvas.convert("RGBA")
            canvas_rgba.alpha_composite(logo_layer, (logo_x, logo_y))
            canvas = canvas_rgba.convert("RGB")

    # ---- Stage 3: GOAL! text ----
    if t <= SWEEP_IN_END:
        text_alpha = max(0.0, (t / SWEEP_IN_END - 0.6) / 0.4)
    elif t <= TEXT_HOLD_END:
        text_alpha = 1.0
    else:
        p = (t - TEXT_HOLD_END) / (1.0 - TEXT_HOLD_END)
        text_alpha = max(0.0, 1.0 - p * 1.4)

    if text_alpha > 0.02:
        try:
            text_font = ImageFont.truetype(str(FONT_PATH), 96)
        except Exception:
            text_font = ImageFont.load_default()

        text = "GOAL!"
        text_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        d = ImageDraw.Draw(text_layer)
        bbox = d.textbbox((0, 0), text, font=text_font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

        # Brief shake on text entry
        shake = 0
        if SWEEP_IN_END < t < TEXT_HOLD_END:
            local = (t - SWEEP_IN_END) / (TEXT_HOLD_END - SWEEP_IN_END)
            intensity = max(0.0, 1.0 - local * 2.5)
            shake = int(intensity * 4 * math.sin(frame_idx * 1.7))

        # Position text on opposite side of logo
        if logo is not None and direction == "ltr":
            text_center_x = WIDTH - (WIDTH - logo.width) // 2 + 20
        elif logo is not None and direction == "rtl":
            text_center_x = (WIDTH - logo.width) // 2 - 20
        else:
            text_center_x = WIDTH // 2

        x = text_center_x - tw // 2 - bbox[0] + shake
        y = (HEIGHT - th) // 2 - bbox[1]
        a = int(255 * text_alpha)

        # Drop shadow
        for dx, dy, sa in [(3, 3, 180), (2, 2, 200)]:
            d.text((x + dx, y + dy), text, font=text_font,
                   fill=(0, 0, 0, int(sa * text_alpha)))
        # Outline (team secondary)
        for ox, oy in [(-2, 0), (2, 0), (0, -2), (0, 2),
                       (-2, -2), (2, -2), (-2, 2), (2, 2)]:
            d.text((x + ox, y + oy), text, font=text_font,
                   fill=(*color_outline, a))
        # Fill (white)
        d.text((x, y), text, font=text_font, fill=(255, 255, 255, a))

        canvas_rgba = canvas.convert("RGBA")
        canvas_rgba.alpha_composite(text_layer)
        canvas = canvas_rgba.convert("RGB")

    return canvas


# ---- GIF writer ----
def make_gif(team: str, side: str, out_dir: Path) -> Path:
    bg = build_banner_strip(team, side)
    frames = [render_frame(team, side, i, N_FRAMES, background=bg)
              for i in range(N_FRAMES)]
    # Final hold on resting state for half a second before looping
    for _ in range(int(FPS * 0.5)):
        frames.append(bg)

    out_path = out_dir / f"{team}_{side.upper()}.gif"
    duration_ms = int(1000 / FPS)
    frames[0].save(
        out_path, save_all=True, append_images=frames[1:],
        duration=duration_ms, loop=0, optimize=True,
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
