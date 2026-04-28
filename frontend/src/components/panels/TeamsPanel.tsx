import { useEffect, useState } from 'react';
import { useProjectStore } from '@/store/project';
import { api } from '@/api/client';
import { Section, Field, ColorField, Button } from '@/components/ui/primitives';
import { hexToRgb } from '@/lib/utils';
import { Upload, X } from 'lucide-react';

export function TeamsPanel() {
  const project = useProjectStore((s) => s.project);
  const update = useProjectStore((s) => s.updateProject);
  const [allTeams, setAllTeams] = useState<Record<string, { primary: string; secondary: string; emblem: string }>>({});
  const [picked, setPicked] = useState<string>('WSH');

  useEffect(() => { api.teams().then(setAllTeams).catch(() => {}); }, []);
  if (!project) return null;

  const baseColors = allTeams[picked];
  const ovr = project.team_overrides[picked];

  const finalRgb = (which: 'primary' | 'secondary' | 'emblem') => {
    const o = ovr?.[which];
    if (o) return o;
    if (!baseColors) return { r: 128, g: 128, b: 128 };
    return hexToRgb(baseColors[which]);
  };

  const setOvr = (which: 'primary' | 'secondary' | 'emblem', rgb: { r: number; g: number; b: number }) => {
    update((p) => {
      const cur = p.team_overrides[picked] ?? {};
      cur[which] = rgb;
      p.team_overrides[picked] = cur;
    });
  };

  const clearOvr = (which: 'primary' | 'secondary' | 'emblem') => {
    update((p) => {
      const cur = p.team_overrides[picked];
      if (!cur) return;
      cur[which] = null;
      if (!cur.primary && !cur.secondary && !cur.emblem && !cur.sprite_asset) {
        delete p.team_overrides[picked];
      }
    });
  };

  return (
    <div>
      <Section title="Pick team">
        <div className="grid grid-cols-4 gap-1">
          {Object.keys(allTeams).sort().map((abbr) => (
            <button
              key={abbr}
              onClick={() => setPicked(abbr)}
              className={`text-xs font-mono px-1.5 py-1 rounded border ${picked === abbr ? 'bg-accent text-black border-accent' : 'bg-panel-2 border-border hover:bg-border'}`}
              style={picked === abbr ? {} : { color: allTeams[abbr]?.primary }}
            >
              {abbr}
            </button>
          ))}
        </div>
      </Section>

      <Section title={`Override ${picked}`}>
        {(['primary', 'secondary', 'emblem'] as const).map((k) => (
          <Field key={k} label={k}>
            <div className="flex items-center gap-1">
              <ColorField value={finalRgb(k)} onChange={(rgb) => setOvr(k, rgb)} />
              {ovr?.[k] && (
                <button
                  onClick={() => clearOvr(k)}
                  className="p-1 text-muted hover:text-text"
                  title="Reset to default"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>
          </Field>
        ))}
      </Section>

      <Section title="Sprite asset">
        <div className="text-xs text-muted">
          {ovr?.sprite_asset
            ? `Custom: ${ovr.sprite_asset}`
            : `Using bundled or procedural default for ${picked}`}
        </div>
        <div className="flex items-center gap-1.5">
          <UploadSprite onUploaded={(name) => update((p) => {
            const cur = p.team_overrides[picked] ?? {};
            cur.sprite_asset = name;
            p.team_overrides[picked] = cur;
          })} />
          {ovr?.sprite_asset && (
            <button
              onClick={() => update((p) => {
                const cur = p.team_overrides[picked];
                if (!cur) return;
                cur.sprite_asset = null;
                if (!cur.primary && !cur.secondary && !cur.emblem && !cur.sprite_asset) {
                  delete p.team_overrides[picked];
                }
              })}
              className="px-2 py-1.5 text-xs rounded-md border border-border bg-panel-2 hover:bg-border text-text"
              title="Reset sprite to default"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </div>
        <p className="text-[10px] text-muted">
          Recommended: 130×200 PNG (13:20 ratio), no antialiasing.
          The renderer auto-fits any size to the sprite box.
        </p>
      </Section>
    </div>
  );
}

function UploadSprite({ onUploaded }: { onUploaded: (name: string) => void }) {
  const [busy, setBusy] = useState(false);
  return (
    <label className="inline-flex items-center justify-center gap-2 rounded-md border bg-panel-2 border-border hover:bg-border text-text text-sm font-medium px-3 py-1.5 cursor-pointer">
      <Upload className="w-3 h-3" /> {busy ? 'Uploading…' : 'Upload PNG'}
      <input
        type="file"
        accept="image/png"
        className="hidden"
        onChange={async (e) => {
          const f = e.target.files?.[0];
          if (!f) return;
          setBusy(true);
          try {
            await api.uploadSprite(f);
            onUploaded(f.name);
          } finally { setBusy(false); }
        }}
      />
    </label>
  );
}
