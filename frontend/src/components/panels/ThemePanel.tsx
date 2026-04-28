import { useProjectStore } from '@/store/project';
import { Section, Field, ColorField, Select } from '@/components/ui/primitives';
import type { Theme } from '@/types/project';

const COLOR_THEMES: { id: ColorThemeName; label: string; description: string }[] = [
  { id: 'csv_default',      label: 'CSV Default',      description: 'Curated colors per matchup (recommended)' },
  { id: 'classic_bordered', label: 'Classic Bordered', description: 'Bright team primaries, classic look' },
  { id: 'midnight',         label: 'Midnight',         description: 'Deep navy + gold premium look' },
  { id: 'ice_rink',         label: 'Ice Rink',         description: 'Light arctic palette' },
  { id: 'heritage',         label: 'Heritage',         description: 'Sepia/warm vintage' },
  { id: 'neon',             label: 'Neon',             description: 'Electric arcade brights' },
  { id: 'stealth',          label: 'Stealth',          description: 'Graphite monochrome with team accents' },
];

type ColorThemeName =
  | 'csv_default' | 'classic_bordered' | 'midnight'
  | 'ice_rink' | 'heritage' | 'neon' | 'stealth';

const COLOR_FIELDS: { key: keyof Theme; label: string }[] = [
  { key: 'bg',                   label: 'Background' },
  { key: 'grid',                 label: 'Grid lines' },
  { key: 'grid_score',           label: 'Score border' },
  { key: 'score_color',          label: 'Score' },
  { key: 'team_color',           label: 'Team labels' },
  { key: 'period_color',         label: 'Period' },
  { key: 'clock_color',          label: 'Clock' },
  { key: 'stat_value_color',     label: 'Stat values' },
  { key: 'stat_label_color',     label: 'Stat labels' },
  { key: 'penalty_active_color', label: 'Penalty' },
];

export function ThemePanel() {
  const project = useProjectStore((s) => s.project);
  const update = useProjectStore((s) => s.updateProject);
  if (!project) return null;
  const t = project.theme;
  const currentTheme = (project as any).color_theme ?? 'csv_default';

  return (
    <div>
      <Section title="Color Theme">
        <div className="text-xs text-muted-foreground mb-2">
          Pick a color preset. CSV Default uses per-matchup curated colors.
          The others apply a fixed palette regardless of teams.
        </div>
        <div className="grid grid-cols-1 gap-1.5">
          {COLOR_THEMES.map((theme) => (
            <button
              key={theme.id}
              onClick={() => update((p) => { (p as any).color_theme = theme.id; })}
              className={`px-3 py-2 text-left rounded-md border ${
                currentTheme === theme.id
                  ? 'border-blue-500 bg-blue-500/10'
                  : 'border-border bg-panel-2 hover:bg-border'
              }`}
            >
              <div className="text-sm font-medium">{theme.label}</div>
              <div className="text-xs text-muted-foreground">{theme.description}</div>
            </button>
          ))}
        </div>
      </Section>

      <Section title="Detail Colors (advanced)">
        <div className="text-xs text-muted-foreground mb-2">
          These per-element overrides apply on top of the selected theme.
          Most users should leave these alone.
        </div>
        {COLOR_FIELDS.map(({ key, label }) => (
          <Field key={key} label={label}>
            <ColorField
              value={t[key] as { r: number; g: number; b: number }}
              onChange={(rgb) => update((p) => { (p.theme as any)[key] = rgb; })}
            />
          </Field>
        ))}
      </Section>

      <Section title="Fonts">
        <Field label="Label font">
          <Select
            value={t.label_font.kind}
            onChange={(e) => update((p) => { p.theme.label_font.kind = e.target.value as any; })}
          >
            <option value="bitmap">Built-in 5×7</option>
            <option value="bdf" disabled>BDF (coming)</option>
            <option value="ttf" disabled>TTF (coming)</option>
          </Select>
        </Field>
        <Field label="Team font">
          <Select
            value={t.team_font.kind}
            onChange={(e) => update((p) => { p.theme.team_font.kind = e.target.value as any; })}
          >
            <option value="bitmap">Built-in 5×7</option>
            <option value="bdf" disabled>BDF (coming)</option>
            <option value="ttf" disabled>TTF (coming)</option>
          </Select>
        </Field>
      </Section>
    </div>
  );
}
