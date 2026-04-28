import { useProjectStore } from '@/store/project';
import { Section, Field, Slider, Switch, Input, Button, Select } from '@/components/ui/primitives';

const PRESETS = [
  { name: '64×64',     w: 64,  h: 64 },
  { name: '128×128',   w: 128, h: 128 },
  { name: '192×192',   w: 192, h: 192 },
  { name: '256×256',   w: 256, h: 256 },
  { name: '320×320',   w: 320, h: 320 },
  { name: '512×512',   w: 512, h: 512 },
  { name: '256×128',   w: 256, h: 128 },
  { name: '128×64',    w: 128, h: 64 },
];

export function LayoutPanel() {
  const project = useProjectStore((s) => s.project);
  const update = useProjectStore((s) => s.updateProject);
  if (!project) return null;
  const L = project.layout;

  const total = L.score_h + L.team_h + L.pen_label_h + L.pen_box_h + L.clock_h;
  const statsRemain = Math.max(0, 1 - total);

  return (
    <div>
      <Section title="Resolution">
        <Field label="Preset">
          <Select
            value={`${L.width}x${L.height}`}
            onChange={(e) => {
              const [w, h] = e.target.value.split('x').map(Number);
              update((p) => { p.layout.width = w; p.layout.height = h; });
            }}
          >
            <option value={`${L.width}x${L.height}`}>{L.width}×{L.height} (custom)</option>
            {PRESETS.map((p) => (
              <option key={p.name} value={`${p.w}x${p.h}`}>{p.name}</option>
            ))}
          </Select>
        </Field>
        <Field label="Width">
          <Input type="number" min={32} max={2048} value={L.width} className="w-20 text-right"
            onChange={(e) => update((p) => { p.layout.width = parseInt(e.target.value) || 320; })} />
        </Field>
        <Field label="Height">
          <Input type="number" min={32} max={2048} value={L.height} className="w-20 text-right"
            onChange={(e) => update((p) => { p.layout.height = parseInt(e.target.value) || 320; })} />
        </Field>
      </Section>

      <Section title="Regions (% of height)">
        <RegionSlider label="Score row"   value={L.score_h}     onChange={(v) => update((p) => { p.layout.score_h = v; })} />
        <RegionSlider label="Team row"    value={L.team_h}      onChange={(v) => update((p) => { p.layout.team_h = v; })} />
        <RegionSlider label="Period lbl"  value={L.pen_label_h} onChange={(v) => update((p) => { p.layout.pen_label_h = v; })} />
        <RegionSlider label="Period box"  value={L.pen_box_h}   onChange={(v) => update((p) => { p.layout.pen_box_h = v; })} />
        <RegionSlider label="Clock row"   value={L.clock_h}     onChange={(v) => update((p) => { p.layout.clock_h = v; })} />
        <Field label="Stats (auto)">
          <span className="text-xs font-mono text-muted">{Math.round(statsRemain * 100)}%</span>
        </Field>
      </Section>

      <Section title="Sprite columns">
        <Field label="Show sprites">
          <Switch checked={L.show_sprites} onChange={(b) => update((p) => { p.layout.show_sprites = b; })} />
        </Field>
        <RegionSlider label="Width" value={L.sprite_w} max={0.4} onChange={(v) => update((p) => { p.layout.sprite_w = v; })} />
      </Section>

      <Section title="Penalty indicators">
        <Field label="Show">
          <Switch checked={L.show_pen_indicators} onChange={(b) => update((p) => { p.layout.show_pen_indicators = b; })} />
        </Field>
      </Section>

      <Section title="Stat rows">
        {L.stats.map((row, i) => (
          <div key={row.field} className="flex items-center gap-2">
            <Switch
              checked={row.enabled}
              onChange={(b) => update((p) => { p.layout.stats[i].enabled = b; })}
            />
            <Input
              value={row.label}
              className="flex-1"
              onChange={(e) => update((p) => { p.layout.stats[i].label = e.target.value; })}
            />
            <span className="text-[10px] text-muted font-mono w-16 text-right">{row.field}</span>
          </div>
        ))}
      </Section>
    </div>
  );
}

function RegionSlider({ label, value, onChange, max = 0.5 }: {
  label: string; value: number; onChange: (v: number) => void; max?: number;
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-muted">{label}</span>
        <span className="text-xs font-mono text-muted">{Math.round(value * 100)}%</span>
      </div>
      <Slider value={value} min={0} max={max} step={0.005} onChange={onChange} />
    </div>
  );
}
