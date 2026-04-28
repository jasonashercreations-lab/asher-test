"""All data models. Anything serialized to JSON / saved in projects lives here."""
from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field, ConfigDict


# -------- Color --------
class RGB(BaseModel):
    """RGB color, 0-255. Stored as object for clarity in JSON projects."""
    r: int = Field(ge=0, le=255)
    g: int = Field(ge=0, le=255)
    b: int = Field(ge=0, le=255)

    def tuple(self) -> tuple[int, int, int]:
        return (self.r, self.g, self.b)

    @classmethod
    def from_hex(cls, h: str) -> "RGB":
        h = h.lstrip("#")
        return cls(r=int(h[0:2], 16), g=int(h[2:4], 16), b=int(h[4:6], 16))

    def to_hex(self) -> str:
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}"


# -------- Game state --------
class TeamState(BaseModel):
    abbrev: str = "---"
    score: int = 0
    shots: int = 0
    hits: int = 0
    blocks: int = 0
    pim: int = 0
    takeaways: int = 0
    giveaways: int = 0
    # Face-off win percentage (0-100, integer for clean display)
    faceoff_win_pct: int = 0
    # Penalty time remaining for this team's active power-play OPPONENT.
    # 0 = no active penalty. Seconds remaining for the renderer to format M:SS.
    penalty_remaining_sec: int = 0


class GameState(BaseModel):
    away: TeamState = Field(default_factory=lambda: TeamState(abbrev="---"))
    home: TeamState = Field(default_factory=lambda: TeamState(abbrev="---"))
    period_label: str = "1ST"
    clock: str = "20:00"
    intermission: bool = False


# -------- Theme --------
class FontSpec(BaseModel):
    """A font reference. Renderer picks the loader based on `kind`."""
    kind: Literal["bitmap", "bdf", "ttf"] = "bitmap"
    name: str = "default-5x7"            # built-in name, or asset path for bdf/ttf
    size: int = 7                         # px height for bitmap; pt for ttf


class Theme(BaseModel):
    bg: RGB = RGB(r=0, g=0, b=0)
    grid: RGB = RGB(r=255, g=255, b=255)
    grid_score: RGB = RGB(r=255, g=200, b=0)
    score_color: RGB = RGB(r=255, g=200, b=0)
    team_color: RGB = RGB(r=255, g=255, b=255)
    period_color: RGB = RGB(r=255, g=255, b=255)
    clock_color: RGB = RGB(r=255, g=200, b=0)
    stat_value_color: RGB = RGB(r=255, g=200, b=0)
    stat_label_color: RGB = RGB(r=255, g=255, b=255)
    penalty_active_color: RGB = RGB(r=255, g=90, b=0)

    label_font: FontSpec = FontSpec()
    team_font: FontSpec = FontSpec()


# -------- Layout --------
class StatRow(BaseModel):
    field: str          # "shots", "hits", etc.
    label: str          # "SHOTS"
    enabled: bool = True


class Layout(BaseModel):
    """Resolution-agnostic. All region heights are fractions of total height."""
    width: int = 320
    height: int = 320

    # Vertical region split (must sum <=1.0). Anything left over is bottom stats.
    score_h: float = 0.24
    team_h: float = 0.16
    pen_label_h: float = 0.07
    pen_box_h: float = 0.07
    clock_h: float = 0.13
    # remainder -> stats area

    # Horizontal: width fraction reserved for sprites on each side
    sprite_w: float = 0.18

    # Show/hide regions
    show_sprites: bool = True
    show_pen_indicators: bool = True

    # Stats rows (order is render order)
    stats: list[StatRow] = Field(default_factory=lambda: [
        StatRow(field="shots",            label="SHOTS"),
        StatRow(field="hits",             label="HITS"),
        StatRow(field="blocks",           label="BLOCKS"),
        StatRow(field="pim",              label="PIM"),
        StatRow(field="takeaways",        label="T.AWAYS"),
        StatRow(field="giveaways",        label="G.AWAYS"),
        StatRow(field="faceoff_win_pct",  label="FO%",      enabled=False),
    ])


# -------- Team overrides --------
class TeamOverride(BaseModel):
    primary: Optional[RGB] = None
    secondary: Optional[RGB] = None
    emblem: Optional[RGB] = None
    sprite_asset: Optional[str] = None    # path under assets/sprites/, or null


# -------- Sprites --------
class SpriteSpec(BaseModel):
    """Default procedural sprite. Per-team can override via TeamOverride."""
    pixels: list[str] = Field(default_factory=list)   # ASCII pixel art rows
    palette: dict[str, str] = Field(default_factory=dict)   # 'P' -> 'primary' etc.


# -------- Game source --------
class NHLSource(BaseModel):
    kind: Literal["nhl"] = "nhl"
    team_filter: Optional[str] = None
    game_id: Optional[int] = None
    poll_interval_sec: float = 10.0


class MockSource(BaseModel):
    kind: Literal["mock"] = "mock"
    state: GameState = Field(default_factory=lambda: GameState(
        away=TeamState(abbrev="WSH", score=0, shots=15, hits=33,
                       blocks=14, pim=4, takeaways=2, giveaways=1),
        home=TeamState(abbrev="CAR", score=2, shots=25, hits=28,
                       blocks=8, pim=8, takeaways=3, giveaways=7),
        period_label="INT.",
        clock="04:40",
    ))


GameSource = NHLSource | MockSource


# -------- Output device --------
class WindowOutput(BaseModel):
    kind: Literal["window"] = "window"
    monitor: int = 0
    fullscreen: bool = False
    upscale: int = 2


class MatrixOutput(BaseModel):
    kind: Literal["matrix"] = "matrix"
    rows: int = 64
    cols: int = 64
    chain_length: int = 1
    parallel: int = 1
    hardware_mapping: str = "regular"
    brightness: int = Field(default=80, ge=0, le=100)


class StreamOutput(BaseModel):
    """Send PNG frames over WebSocket to anyone listening at /ws/preview."""
    kind: Literal["stream"] = "stream"
    enabled: bool = True


OutputDevice = WindowOutput | MatrixOutput | StreamOutput


# -------- Project (the .nhlsb file) --------
class Project(BaseModel):
    model_config = ConfigDict(extra="ignore")

    schema_version: int = 1
    name: str = "Untitled Scoreboard"
    theme: Theme = Field(default_factory=Theme)
    layout: Layout = Field(default_factory=Layout)
    team_overrides: dict[str, TeamOverride] = Field(default_factory=dict)
    sprite: SpriteSpec = Field(default_factory=SpriteSpec)
    source: GameSource = Field(default_factory=NHLSource)
    outputs: list[OutputDevice] = Field(default_factory=lambda: [StreamOutput()])
