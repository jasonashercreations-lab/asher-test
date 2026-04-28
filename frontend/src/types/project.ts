// Mirror of backend Pydantic models. Keep in sync.

export interface RGB { r: number; g: number; b: number; }

export interface TeamState {
  abbrev: string;
  score: number;
  shots: number;
  hits: number;
  blocks: number;
  pim: number;
  takeaways: number;
  giveaways: number;
  faceoff_win_pct: number;
  penalty_remaining_sec: number;
}

export interface GameState {
  away: TeamState;
  home: TeamState;
  period_label: string;
  clock: string;
  intermission: boolean;
}

export interface FontSpec {
  kind: 'bitmap' | 'bdf' | 'ttf';
  name: string;
  size: number;
}

export interface Theme {
  bg: RGB;
  grid: RGB;
  grid_score: RGB;
  score_color: RGB;
  team_color: RGB;
  period_color: RGB;
  clock_color: RGB;
  stat_value_color: RGB;
  stat_label_color: RGB;
  penalty_active_color: RGB;
  label_font: FontSpec;
  team_font: FontSpec;
}

export interface StatRow {
  field: string;
  label: string;
  enabled: boolean;
}

export interface Layout {
  width: number;
  height: number;
  render_style: 'premium' | 'dot';
  score_h: number;
  team_h: number;
  pen_label_h: number;
  pen_box_h: number;
  clock_h: number;
  sprite_w: number;
  show_sprites: boolean;
  show_pen_indicators: boolean;
  stats: StatRow[];
}

export interface TeamOverride {
  primary?: RGB | null;
  secondary?: RGB | null;
  emblem?: RGB | null;
  sprite_asset?: string | null;
}

export interface SpriteSpec {
  pixels: string[];
  palette: Record<string, string>;
}

export type GameSource =
  | { kind: 'nhl'; team_filter?: string | null; game_id?: number | null; poll_interval_sec: number }
  | { kind: 'mock'; state: GameState };

export type OutputDevice =
  | { kind: 'window'; monitor: number; fullscreen: boolean; upscale: number }
  | { kind: 'matrix'; rows: number; cols: number; chain_length: number; parallel: number; hardware_mapping: string; brightness: number }
  | { kind: 'stream'; enabled: boolean };

export type ColorThemeName =
  | 'csv_default'
  | 'classic_bordered'
  | 'midnight'
  | 'ice_rink'
  | 'heritage'
  | 'neon'
  | 'stealth';

export interface Project {
  schema_version: number;
  name: string;
  theme: Theme;
  layout: Layout;
  color_theme?: ColorThemeName;
  team_overrides: Record<string, TeamOverride>;
  sprite: SpriteSpec;
  source: GameSource;
  outputs: OutputDevice[];
}

export interface GameSummary {
  id: number;
  away: string;
  home: string;
  state: string;
}

export interface BackendStatus {
  last_fetch_ok: boolean;
  last_fetch_at: number;
  last_error: string;
  current_state: GameState;
}
