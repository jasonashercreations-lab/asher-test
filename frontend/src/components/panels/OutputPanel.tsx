import { useProjectStore } from '@/store/project';
import { Section, Field, Switch, Input, Slider, Button, Select } from '@/components/ui/primitives';
import type { OutputDevice } from '@/types/project';
import { Plus, Trash2, Monitor, Cpu, Globe, Maximize2, ExternalLink } from 'lucide-react';

function openScoreboardWindow() {
  // Open the fullscreen scoreboard route in a new browser window.
  // Works in both Tauri (opens in default browser) and dev/web mode.
  const url = '/#/scoreboard';
  const win = window.open(url, '_blank',
    'width=1280,height=720,menubar=no,toolbar=no,location=no,status=no');
  if (!win) {
    // Popup blocked - fall back to opening in a new tab
    window.open(url, '_blank');
  }
}

export function OutputPanel() {
  const project = useProjectStore((s) => s.project);
  const update = useProjectStore((s) => s.updateProject);
  if (!project) return null;

  const addOutput = (kind: 'window' | 'matrix' | 'stream') => {
    update((p) => {
      if (kind === 'window') p.outputs.push({ kind: 'window', monitor: 0, fullscreen: false, upscale: 4 });
      else if (kind === 'matrix') p.outputs.push({ kind: 'matrix', rows: 64, cols: 64, chain_length: 1, parallel: 1, hardware_mapping: 'regular', brightness: 80 });
      else p.outputs.push({ kind: 'stream', enabled: true });
    });
  };

  return (
    <div>
      <Section title="Display scoreboard">
        <p className="text-xs text-muted">
          Open the scoreboard in its own window. Drag it to a second monitor or
          your TV, then press <span className="font-mono text-accent">F11</span> for fullscreen.
        </p>
        <Button variant="accent" onClick={openScoreboardWindow} className="w-full">
          <Maximize2 className="w-3.5 h-3.5" /> Open Scoreboard Window
        </Button>
      </Section>

      <Section title="Output devices (advanced)">
        <p className="text-xs text-muted">
          Configure additional output destinations. Stream is always on (powers
          the editor preview). Matrix is for the Pi LED panel deployment.
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
          title={`#${i + 1} - ${out.kind}`}
          action={
            <button
              onClick={() => update((p) => { p.outputs.splice(i, 1); })}
              className="text-muted hover:text-red-400"
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
        <div className="px-3 py-6 text-xs text-muted text-center">No outputs configured.</div>
      )}
    </div>
  );
}

function OutputEditor({ output, onChange }: { output: OutputDevice; onChange: (o: OutputDevice) => void }) {
  if (output.kind === 'stream') {
    return (
      <Field label="Enabled">
        <Switch checked={output.enabled} onChange={(b) => onChange({ ...output, enabled: b })} />
      </Field>
    );
  }
  if (output.kind === 'window') {
    return (
      <>
        <Field label="Monitor">
          <Input type="number" min={0} className="w-16 text-right" value={output.monitor}
            onChange={(e) => onChange({ ...output, monitor: parseInt(e.target.value) || 0 })} />
        </Field>
        <Field label="Fullscreen">
          <Switch checked={output.fullscreen} onChange={(b) => onChange({ ...output, fullscreen: b })} />
        </Field>
        <Field label="Upscale">
          <Input type="number" min={1} max={10} className="w-16 text-right" value={output.upscale}
            onChange={(e) => onChange({ ...output, upscale: parseInt(e.target.value) || 1 })} />
        </Field>
      </>
    );
  }
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
    </>
  );
}
