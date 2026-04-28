import { useEffect, useState } from 'react';
import { useProjectStore } from '@/store/project';
import { api } from '@/api/client';
import { Button, Input } from '@/components/ui/primitives';
import { Save, FolderOpen, Activity } from 'lucide-react';

export function Toolbar() {
  const project = useProjectStore((s) => s.project);
  const update = useProjectStore((s) => s.updateProject);
  const replace = useProjectStore((s) => s.replaceProject);
  const [filename, setFilename] = useState('default.nhlsb');
  const [savedProjects, setSavedProjects] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.listProjects().then(setSavedProjects).catch(() => {});
  }, []);

  if (!project) return null;

  const save = async () => {
    setBusy(true);
    try {
      await api.saveProject(filename);
      setSavedProjects(await api.listProjects());
    } finally { setBusy(false); }
  };

  const load = async (name: string) => {
    setBusy(true);
    try {
      const p = await api.loadProject(name);
      replace(p);
    } finally { setBusy(false); }
  };

  return (
    <div className="h-12 border-b border-border bg-panel flex items-center px-3 gap-3">
      <div className="text-accent font-mono text-sm font-bold tracking-wider">NHL•SCOREBOARD STUDIO</div>
      <Input
        className="w-64"
        value={project.name}
        onChange={(e) => update((p) => { p.name = e.target.value; })}
      />
      <div className="flex-1" />
      <Input
        className="w-48"
        value={filename}
        onChange={(e) => setFilename(e.target.value)}
        placeholder="filename.nhlsb"
      />
      <Button onClick={save} disabled={busy}>
        <Save className="w-3.5 h-3.5" /> Save
      </Button>
      <select
        className="bg-panel-2 border border-border rounded-md px-2 py-1 text-sm cursor-pointer"
        onChange={(e) => { if (e.target.value) load(e.target.value); }}
        value=""
      >
        <option value="">Open project…</option>
        {savedProjects.map((n) => <option key={n} value={n}>{n}</option>)}
      </select>
      <div className="flex items-center gap-1 text-xs text-muted ml-2">
        <Activity className="w-3 h-3" /> live
      </div>
    </div>
  );
}
