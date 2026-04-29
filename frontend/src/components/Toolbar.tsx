import { useEffect, useRef, useState } from 'react';
import { useProjectStore } from '@/store/project';
import { api } from '@/api/client';
import { Button, Input } from '@/components/ui/primitives';
import {
  Save, FolderOpen, Activity, Undo2, Redo2, Upload, Trash2, Check, AlertCircle,
} from 'lucide-react';

export function Toolbar() {
  const project = useProjectStore((s) => s.project);
  const update = useProjectStore((s) => s.updateProject);
  const replace = useProjectStore((s) => s.replaceProject);
  const undo = useProjectStore((s) => s.undo);
  const redo = useProjectStore((s) => s.redo);
  const canUndo = useProjectStore((s) => s.past.length > 0);
  const canRedo = useProjectStore((s) => s.future.length > 0);
  const dirty = useProjectStore((s) => s.dirty);
  const save = useProjectStore((s) => s.save);
  const saveNow = useProjectStore((s) => s.saveNow);
  const setFilename = useProjectStore((s) => s.setFilename);
  const currentFilename = useProjectStore((s) => s.currentFilename);

  const [filenameInput, setFilenameInput] = useState('default.nhlsb');
  const [savedProjects, setSavedProjects] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  // Sync local filename input with store
  useEffect(() => {
    if (currentFilename) setFilenameInput(currentFilename);
  }, [currentFilename]);

  const refreshList = () => api.listProjects().then(setSavedProjects).catch(() => {});
  useEffect(() => { refreshList(); }, []);

  // Keyboard shortcuts: Ctrl+Z / Ctrl+Shift+Z / Ctrl+S
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const mod = e.ctrlKey || e.metaKey;
      if (!mod) return;
      // Don't hijack if user is typing in an input
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA') return;
      if (e.key.toLowerCase() === 'z' && !e.shiftKey) { e.preventDefault(); undo(); }
      else if ((e.key.toLowerCase() === 'z' && e.shiftKey)
              || e.key.toLowerCase() === 'y') { e.preventDefault(); redo(); }
      else if (e.key.toLowerCase() === 's') { e.preventDefault(); void saveNow(filenameInput); refreshList(); }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [undo, redo, saveNow, filenameInput]);

  if (!project) return null;

  const handleSave = async () => {
    setBusy(true);
    try {
      setFilename(filenameInput);
      await saveNow(filenameInput);
      await refreshList();
    } finally { setBusy(false); }
  };

  const handleLoad = async (name: string) => {
    setBusy(true);
    try {
      const p = await api.loadProject(name);
      replace(p, { filename: name });
      setFilenameInput(name);
    } finally { setBusy(false); }
  };

  const handleDelete = async (name: string) => {
    if (!confirm(`Delete project "${name}"?`)) return;
    await api.deleteProject(name);
    await refreshList();
  };

  const handleImport = async (file: File) => {
    setBusy(true);
    try {
      const r = await api.importProject(file);
      const filename = r.path.split(/[\\/]/).pop() || file.name;
      replace(r.project, { filename });
      setFilenameInput(filename);
      await refreshList();
    } finally { setBusy(false); }
  };

  // Save status badge
  const saveBadge = (() => {
    if (save.saving) return <span className="text-muted text-[10px]">Saving…</span>;
    if (save.saveError) {
      return (
        <span className="flex items-center gap-1 text-amber-400 text-[10px]" title={save.saveError}>
          <AlertCircle className="w-3 h-3" /> Save failed
        </span>
      );
    }
    if (dirty) return <span className="text-amber-400 text-[10px]">● Unsaved</span>;
    if (save.lastSavedAt) {
      return (
        <span className="flex items-center gap-1 text-green-400 text-[10px]">
          <Check className="w-3 h-3" /> Saved
        </span>
      );
    }
    return null;
  })();

  return (
    <div className="h-12 border-b border-border bg-panel flex items-center px-3 gap-3">
      <div className="text-accent font-mono text-sm font-bold tracking-wider">NHL•SCOREBOARD STUDIO</div>

      <Input
        className="w-56"
        value={project.name}
        onChange={(e) => update((p) => { p.name = e.target.value; })}
      />

      <div className="flex items-center gap-0.5 ml-2">
        <button
          onClick={undo}
          disabled={!canUndo}
          className="p-1.5 rounded hover:bg-panel-2 disabled:opacity-30 disabled:cursor-not-allowed"
          title="Undo (Ctrl+Z)"
        >
          <Undo2 className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={redo}
          disabled={!canRedo}
          className="p-1.5 rounded hover:bg-panel-2 disabled:opacity-30 disabled:cursor-not-allowed"
          title="Redo (Ctrl+Shift+Z)"
        >
          <Redo2 className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="ml-2">{saveBadge}</div>

      <div className="flex-1" />

      <Input
        className="w-48"
        value={filenameInput}
        onChange={(e) => setFilenameInput(e.target.value)}
        placeholder="filename.nhlsb"
      />
      <Button onClick={handleSave} disabled={busy}>
        <Save className="w-3.5 h-3.5" /> Save
      </Button>

      <input
        ref={fileInput}
        type="file"
        accept=".nhlsb,application/json"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) void handleImport(f);
          e.target.value = '';
        }}
      />
      <Button onClick={() => fileInput.current?.click()} disabled={busy} title="Import .nhlsb file">
        <Upload className="w-3.5 h-3.5" />
      </Button>

      <ProjectsMenu
        projects={savedProjects}
        onLoad={handleLoad}
        onDelete={handleDelete}
        currentFilename={currentFilename}
      />

      <div className="flex items-center gap-1 text-xs text-muted ml-2">
        <Activity className="w-3 h-3" /> live
      </div>
    </div>
  );
}

function ProjectsMenu({
  projects, onLoad, onDelete, currentFilename,
}: {
  projects: string[];
  onLoad: (n: string) => void;
  onDelete: (n: string) => void;
  currentFilename: string;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1 bg-panel-2 border border-border rounded-md px-2 py-1 text-sm cursor-pointer hover:border-accent"
      >
        <FolderOpen className="w-3.5 h-3.5" /> Open
      </button>
      {open && (
        <>
          <div className="fixed inset-0" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full mt-1 w-64 bg-panel-2 border border-border rounded-md shadow-lg z-50 max-h-80 overflow-y-auto">
            {projects.length === 0 && (
              <div className="px-3 py-2 text-xs text-muted">No saved projects</div>
            )}
            {projects.map((n) => (
              <div key={n}
                   className={`flex items-center px-2 py-1.5 hover:bg-panel text-xs ${
                     n === currentFilename ? 'text-accent' : 'text-text'
                   }`}>
                <button
                  onClick={() => { onLoad(n); setOpen(false); }}
                  className="flex-1 text-left truncate"
                  title={n}
                >
                  {n}
                </button>
                <button
                  onClick={() => { onDelete(n); }}
                  className="ml-1 p-1 text-muted hover:text-red-400"
                  title="Delete"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
