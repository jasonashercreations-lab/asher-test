import { useProjectStore } from '@/store/project';
import { Section, Field, Slider, Switch, Input, Button, Select } from '@/components/ui/primitives';

// Bug 7: Quick-test presets grouped by aspect ratio
const PRESET_GROUPS: { label: string; presets: { name: string; w: number; h: number }[] }[] = [
  { label: '4:5 (portrait, default)', presets: [
    { name: '800×1000', w: 800, h: 1000 },
    { name: '1080×1350', w: 1080, h: 1350 },
    { name: '1200×1500', w: 1200, h: 1500 },
  ]},
  { label: '1:1 (square)', presets: [
    { name: '32', w: 32, h: 32 },
    { name: '64', w: 64, h: 64 },
    { name: '128', w: 128, h: 128 },
    { name: '256', w: 256, h: 256 },
    { name: '320', w: 320, h: 320 },
    { name: '512', w: 512, h: 512 },
  ]},
  { label: '16:9 (HD)', presets: [
    { name: '320×180', w: 320, h: 180 },
    { name: '640×360', w: 640, h: 360 },
    { name: '1280×720', w: 1280, h: 720 },
    { name: '1920×1080', w: 1920, h: 1080 },
  ]},
  { label: '4:3', presets: [
    { name: '320×240', w: 320, h: 240 },
    { name: '640×480', w: 640, h: 480 },
  ]},
  { label: '2:1 (LED)', presets: [
    { name: '128×64', w: 128, h: 64 },
    { name: '256×128', w: 256, h: 128 },
    { name: '512×256', w: 512, h: 256 },
  ]},
  { label: '9:16 (tall phone)', presets: [
    { name: '180×320', w: 180, h: 320 },
    { name: '360×640', w: 360, h: 640 },
  ]},
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
      <Section title="Render style">
        <Field label="Style">
          <Select
            value={(L as any).render_style ?? 'premium'}
            onChange={(e) => update((p) => { (p.layout as any).render_style = e.target.value; })}
          >
            <option value="premium">Premium (broadcast / smooth)</option>
            <option value="dot">Dot (LED / pixel art)</option>
          </Select>
        </Field>
        <p className="text-[10px] text-muted">
          Premium uses Bebas Neue, hairlines, and clean spacing — best for
          TVs and streaming. Dot uses bitmap fonts and blocky digits — best
          for LED panels and retro look.
        </p>
      </Section>

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
            {PRESET_GROUPS.flatMap((g) =>
              g.presets.map((p) => (
                <option key={`${g.label}-${p.name}`} value={`${p.w}x${p.h}`}>
                  {g.label}: {p.name}
                </option>
              ))
            )}
          </Select>
        </Field>
        <Field label="Width">
          <Input type="number" min={32} max={4096} value={L.width} className="w-20 text-right"
            onChange={(e) => update((p) => { p.layout.width = parseInt(e.target.value) || 1080; })} />
        </Field>
        <Field label="Height">
          <Input type="number" min={32} max={4096} value={L.height} className="w-20 text-right"
            onChange={(e) => update((p) => { p.layout.height = parseInt(e.target.value) || 1350; })} />
        </Field>
      </Section>

      <Section title="Quick test (by aspect)">
        {PRESET_GROUPS.map((g) => (
          <div key={g.label}>
            <div className="text-[10px] uppercase text-muted mb-1">{g.label}</div>
            <div className="flex flex-wrap gap-1 mb-2">
              {g.presets.map((p) => (
                <button
                  key={p.name}
                  onClick={() => update((proj) => { proj.layout.width = p.w; proj.layout.height = p.h; })}
                  className={`px-2 py-1 text-[10px] font-mono rounded border ${
                    L.width === p.w && L.height === p.h
                      ? 'bg-accent text-black border-accent'
                      : 'bg-panel-2 border-border hover:bg-border'
                  }`}
                >
                  {p.name}
                </button>
              ))}
            </div>
          </div>
        ))}
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
        <div className="text-[10px] text-muted mb-2">
          Use ▲▼ to reorder. The order here is the top-to-bottom order in the
          stats grid.
        </div>
        {L.stats.map((row, i) => (
          <div key={row.field} className="flex items-center gap-1">
            <Switch
              checked={row.enabled}
              onChange={(b) => update((p) => { p.layout.stats[i].enabled = b; })}
            />
            <button
              disabled={i === 0}
              onClick={() => update((p) => {
                const arr = p.layout.stats;
                [arr[i - 1], arr[i]] = [arr[i], arr[i - 1]];
              })}
              className="px-1.5 py-0.5 text-xs rounded border border-border bg-panel-2 hover:bg-border disabled:opacity-30 disabled:cursor-not-allowed"
              title="Move up"
            >
              ▲
            </button>
            <button
              disabled={i === L.stats.length - 1}
              onClick={() => update((p) => {
                const arr = p.layout.stats;
                [arr[i], arr[i + 1]] = [arr[i + 1], arr[i]];
              })}
              className="px-1.5 py-0.5 text-xs rounded border border-border bg-panel-2 hover:bg-border disabled:opacity-30 disabled:cursor-not-allowed"
              title="Move down"
            >
              ▼
            </button>
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
