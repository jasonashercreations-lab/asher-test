import { useEffect, useState } from 'react';
import { useProjectStore } from '@/store/project';
import { Section, Field, Switch, Input, Slider, Button, Select } from '@/components/ui/primitives';
import type { OutputDevice } from '@/types/project';
import { Trash2, Monitor, Cpu, Globe, Maximize2, Power } from 'lucide-react';
import { isTauri, listMonitors, openScoreboardWindow, type MonitorInfo } from '@/lib/tauri';

const SCOREBOARD_URL = 'http://127.0.0.1:8765/#/scoreboard';

/** Browser fallback (non-Tauri). Best-effort fullscreen via requestFullscreen,
 *  which may be blocked by the popup not having a user gesture. */
function openScoreboardBrowserFallback(opts: { fullscreen?: boolean } = {}) {
  const features = ['menubar=no', 'toolbar=no', 'location=no', 'status=no',
                    'width=1280', 'height=720'];
  const win = window.open(SCOREBOARD_URL, '_blank', features.join(','));
  if (!win) {
    window.open(SCOREBOARD_URL, '_blank');
    return;
  }
  if (opts.fullscreen) {
    setTimeout(() => {
      try { win.document?.documentElement?.requestFullscreen?.(); }
      catch { /* user gesture required */ }
    }, 800);
  }
}

export function OutputPanel() {
  const project = useProjectStore((s) => s.project);
  const update = useProjectStore((s) => s.updateProject);
  if (!project) return null;

  const addOutput = (kind: 'window' | 'matrix' | 'stream') => {
    update((p) => {
      if (kind === 'window') p.outputs.push({ kind: 'window', monitor: 0, fullscreen: true, upscale: 4 });
      else if (kind === 'matrix') p.outputs.push({ kind: 'matrix', rows: 64, cols: 64, chain_length: 1, parallel: 1, hardware_mapping: 'regular', brightness: 80 });
      else p.outputs.push({ kind: 'stream', enabled: true });
    });
  };

  return (
    <div>
      <Section title="Add output">
        <p className="text-xs text-muted">
          Each output is independent — configure it and use its own button to launch.
        </p>
        <div className="grid grid-cols-3 gap-1.5">
          <Button onClick={() => addOutput('stream')} className="flex-col h-auto py-2">
            <Globe className="w-3.5 h-3.5" /><span className="text-[10px]">Stream</span>
          </Button>
          <Button onClick={() => addOutput('window')} className="flex-col h-auto py-2">
            <Monitor className="w-3.5 h-3.5" /><span className="text-[10px]">Window</span>
          </Button>
          <Button onClick={() => addOutput('matrix')} className="flex-col h-auto py-2">
            <Cpu className="w-3.5 h-3.5" /><span className="text-[10px]">LED</span>
          </Button>
        </div>
      </Section>

      {project.outputs.map((out, i) => (
        <Section
          key={i}
          title={`#${i + 1} — ${out.kind}`}
          action={
            <button
              onClick={() => update((p) => { p.outputs.splice(i, 1); })}
              className="text-muted hover:text-red-400"
              title="Remove output"
            >
              <Trash2 className="w-3 h-3" />
            </button>
          }
        >
          <OutputEditor
            output={out}
            onChange={(next) => update((p) => { p.outputs[i] = next; })}
          />
        </Section>
      ))}

      {project.outputs.length === 0 && (
        <div className="px-3 py-6 text-xs text-muted text-center">
          No outputs configured. Add one above.
        </div>
      )}
    </div>
  );
}

function OutputEditor({ output, onChange }: { output: OutputDevice; onChange: (o: OutputDevice) => void }) {
  if (output.kind === 'stream') {
    return (
      <>
        <Field label="Enabled">
          <Switch checked={output.enabled} onChange={(b) => onChange({ ...output, enabled: b })} />
        </Field>
        <p className="text-[10px] text-muted">
          Stream powers the editor preview and any browser pointing at /#/scoreboard.
        </p>
      </>
    );
  }

  if (output.kind === 'window') {
    return <WindowOutputEditor output={output} onChange={onChange} />;
  }

  // matrix
  return (
    <>
      <Field label="Rows / Cols">
        <div className="flex items-center gap-1">
          <Input type="number" className="w-14 text-right" value={output.rows}
            onChange={(e) => onChange({ ...output, rows: parseInt(e.target.value) || 64 })} />
          <span className="text-muted">x</span>
          <Input type="number" className="w-14 text-right" value={output.cols}
            onChange={(e) => onChange({ ...output, cols: parseInt(e.target.value) || 64 })} />
        </div>
      </Field>
      <Field label="Chain">
        <Input type="number" min={1} className="w-14 text-right" value={output.chain_length}
          onChange={(e) => onChange({ ...output, chain_length: parseInt(e.target.value) || 1 })} />
      </Field>
      <Field label="Parallel">
        <Input type="number" min={1} className="w-14 text-right" value={output.parallel}
          onChange={(e) => onChange({ ...output, parallel: parseInt(e.target.value) || 1 })} />
      </Field>
      <Field label="HW mapping">
        <Select value={output.hardware_mapping}
          onChange={(e) => onChange({ ...output, hardware_mapping: e.target.value })}>
          <option value="regular">regular</option>
          <option value="adafruit-hat">adafruit-hat</option>
          <option value="adafruit-hat-pwm">adafruit-hat-pwm</option>
        </Select>
      </Field>
      <Field label="Brightness">
        <div className="w-32"><Slider value={output.brightness} min={0} max={100} step={1}
          onChange={(v) => onChange({ ...output, brightness: Math.round(v) })} /></div>
      </Field>
      <Button variant="accent" className="w-full" disabled>
        <Power className="w-3.5 h-3.5" /> Connect
      </Button>
      <p className="text-[10px] text-muted">
        LED matrix output is only active when running on a Raspberry Pi with
        the rpi-rgb-led-matrix library installed.
      </p>
    </>
  );
}

function WindowOutputEditor({
  output, onChange,
}: { output: Extract<OutputDevice, { kind: 'window' }>; onChange: (o: OutputDevice) => void }) {
  const [monitors, setMonitors] = useState<MonitorInfo[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const tauri = isTauri();

  useEffect(() => {
    if (!tauri) return;
    listMonitors().then((m) => {
      setMonitors(m);
      // If saved monitor index no longer valid, clamp to 0
      if (m && (output.monitor < 0 || output.monitor >= m.length)) {
        onChange({ ...output, monitor: 0 });
      }
    });
  }, [tauri]);

  const handleOpen = async () => {
    setBusy(true);
    setErr(null);
    try {
      if (tauri) {
        const ok = await openScoreboardWindow({
          monitorIndex: output.monitor,
          fullscreen: output.fullscreen,
        });
        if (!ok) setErr('Tauri command failed - see devtools');
      } else {
        openScoreboardBrowserFallback({ fullscreen: output.fullscreen });
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <Field label="Fullscreen">
        <Switch checked={output.fullscreen} onChange={(b) => onChange({ ...output, fullscreen: b })} />
      </Field>

      <Field label="Display">
        {tauri && monitors ? (
          monitors.length === 0 ? (
            <span className="text-[10px] text-muted">No displays detected</span>
          ) : (
            <Select
              className="w-44"
              value={String(output.monitor)}
              onChange={(e) => onChange({ ...output, monitor: parseInt(e.target.value) || 0 })}
            >
              {monitors.map((m) => (
                <option key={m.index} value={m.index}>
                  {m.index}: {m.name} — {m.width}×{m.height}{m.is_primary ? ' (primary)' : ''}
                </option>
              ))}
            </Select>
          )
        ) : (
          <Input type="number" min={0} className="w-16 text-right" value={output.monitor}
            onChange={(e) => onChange({ ...output, monitor: parseInt(e.target.value) || 0 })} />
        )}
      </Field>

      <Field label="Upscale">
        <Input type="number" min={1} max={10} className="w-16 text-right" value={output.upscale}
          onChange={(e) => onChange({ ...output, upscale: parseInt(e.target.value) || 1 })} />
      </Field>

      <Button variant="accent" className="w-full" onClick={handleOpen} disabled={busy}>
        <Maximize2 className="w-3.5 h-3.5" /> {busy ? 'Opening…' : 'Open Window'}
      </Button>

      {err && <p className="text-[10px] text-red-400">{err}</p>}

      {tauri ? (
        <p className="text-[10px] text-muted">
          Opens a native window on the chosen display. Fullscreen is applied automatically.
        </p>
      ) : (
        <p className="text-[10px] text-muted">
          Browser fallback: drag the popup to your target monitor; F11 toggles fullscreen.
        </p>
      )}
    </>
  );
}
