import { useProjectStore } from '@/store/project';
import { Section, Field, ColorField, Select } from '@/components/ui/primitives';
import type { Theme } from '@/types/project';

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

  return (
    <div>
      <Section title="Colors">
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

      <Section title="Presets">
        <div className="grid grid-cols-2 gap-1.5">
          <PresetButton name="Classic" onClick={() => update((p) => Object.assign(p.theme, CLASSIC))} />
          <PresetButton name="Neon" onClick={() => update((p) => Object.assign(p.theme, NEON))} />
          <PresetButton name="Mono" onClick={() => update((p) => Object.assign(p.theme, MONO))} />
          <PresetButton name="Retro" onClick={() => update((p) => Object.assign(p.theme, RETRO))} />
        </div>
      </Section>
    </div>
  );
}

function PresetButton({ name, onClick }: { name: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="px-2 py-1.5 text-xs rounded-md border border-border bg-panel-2 hover:bg-border"
    >
      {name}
    </button>
  );
}

const rgb = (r: number, g: number, b: number) => ({ r, g, b });

const CLASSIC: Partial<Theme> = {
  bg: rgb(0, 0, 0), grid: rgb(255, 255, 255), grid_score: rgb(255, 200, 0),
  score_color: rgb(255, 200, 0), team_color: rgb(255, 255, 255),
  period_color: rgb(255, 255, 255), clock_color: rgb(255, 200, 0),
  stat_value_color: rgb(255, 200, 0), stat_label_color: rgb(255, 255, 255),
  penalty_active_color: rgb(255, 90, 0),
};
const NEON: Partial<Theme> = {
  bg: rgb(8, 0, 30), grid: rgb(0, 255, 200), grid_score: rgb(255, 0, 200),
  score_color: rgb(255, 0, 200), team_color: rgb(0, 255, 200),
  period_color: rgb(180, 255, 255), clock_color: rgb(0, 255, 200),
  stat_value_color: rgb(255, 0, 200), stat_label_color: rgb(0, 255, 200),
  penalty_active_color: rgb(255, 60, 60),
};
const MONO: Partial<Theme> = {
  bg: rgb(0, 0, 0), grid: rgb(180, 180, 180), grid_score: rgb(255, 255, 255),
  score_color: rgb(255, 255, 255), team_color: rgb(255, 255, 255),
  period_color: rgb(220, 220, 220), clock_color: rgb(255, 255, 255),
  stat_value_color: rgb(255, 255, 255), stat_label_color: rgb(180, 180, 180),
  penalty_active_color: rgb(255, 80, 80),
};
const RETRO: Partial<Theme> = {
  bg: rgb(15, 35, 25), grid: rgb(150, 220, 90), grid_score: rgb(220, 250, 100),
  score_color: rgb(220, 250, 100), team_color: rgb(150, 220, 90),
  period_color: rgb(180, 220, 120), clock_color: rgb(220, 250, 100),
  stat_value_color: rgb(220, 250, 100), stat_label_color: rgb(150, 220, 90),
  penalty_active_color: rgb(255, 120, 0),
};
