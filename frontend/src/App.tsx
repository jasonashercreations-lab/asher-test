import { useEffect, useState } from 'react';
import { useProjectStore } from '@/store/project';
import { api } from '@/api/client';
import { Toolbar } from '@/components/Toolbar';
import { Preview } from '@/components/Preview';
import { FullscreenScoreboard } from '@/components/FullscreenScoreboard';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { GameSourcePanel } from '@/components/panels/GameSourcePanel';
import { ThemePanel } from '@/components/panels/ThemePanel';
import { LayoutPanel } from '@/components/panels/LayoutPanel';
import { TeamsPanel } from '@/components/panels/TeamsPanel';
import { OutputPanel } from '@/components/panels/OutputPanel';
import { StatusPanel } from '@/components/panels/StatusPanel';
import { AssetsPanel } from '@/components/panels/AssetsPanel';
import { Radio, Palette, LayoutGrid, Users, Cable, Activity, Image as ImageIcon } from 'lucide-react';

const PANELS = [
  { id: 'source', label: 'Source',  icon: Radio,      Component: GameSourcePanel },
  { id: 'theme',  label: 'Theme',   icon: Palette,    Component: ThemePanel },
  { id: 'layout', label: 'Layout',  icon: LayoutGrid, Component: LayoutPanel },
  { id: 'teams',  label: 'Teams',   icon: Users,      Component: TeamsPanel },
  { id: 'assets', label: 'Assets',  icon: ImageIcon,  Component: AssetsPanel },
  { id: 'output', label: 'Output',  icon: Cable,      Component: OutputPanel },
  { id: 'status', label: 'Status',  icon: Activity,   Component: StatusPanel },
] as const;

type PanelId = typeof PANELS[number]['id'];

function Editor() {
  const fetchProject = useProjectStore((s) => s.fetchProject);
  const replaceProject = useProjectStore((s) => s.replaceProject);
  const project = useProjectStore((s) => s.project);
  const error = useProjectStore((s) => s.error);
  const [active, setActive] = useState<PanelId>('source');
  const [dragOver, setDragOver] = useState(false);

  useEffect(() => { fetchProject(); }, [fetchProject]);

  // Window-level drag-drop: drop a .nhlsb file anywhere to import
  useEffect(() => {
    const onDragOver = (e: DragEvent) => {
      if (e.dataTransfer?.types.includes('Files')) {
        e.preventDefault();
        setDragOver(true);
      }
    };
    const onDragLeave = (e: DragEvent) => {
      // Only clear when leaving the window itself
      if (!e.relatedTarget) setDragOver(false);
    };
    const onDrop = async (e: DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer?.files?.[0];
      if (!file) return;
      if (!file.name.endsWith('.nhlsb')) {
        alert('Drop a .nhlsb file');
        return;
      }
      try {
        const r = await api.importProject(file);
        const filename = r.path.split(/[\\/]/).pop() || file.name;
        replaceProject(r.project, { filename });
      } catch (err: any) {
        alert(`Import failed: ${err?.message || err}`);
      }
    };
    window.addEventListener('dragover', onDragOver);
    window.addEventListener('dragleave', onDragLeave);
    window.addEventListener('drop', onDrop);
    return () => {
      window.removeEventListener('dragover', onDragOver);
      window.removeEventListener('dragleave', onDragLeave);
      window.removeEventListener('drop', onDrop);
    };
  }, [replaceProject]);

  if (error) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-400 mb-2">Backend unreachable</div>
          <div className="text-muted text-sm font-mono">{error}</div>
        </div>
      </div>
    );
  }
  if (!project) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-muted text-sm mb-2">Starting backend…</div>
          <div className="text-muted text-[10px]">First launch can take a few seconds.</div>
        </div>
      </div>
    );
  }

  const ActivePanel = PANELS.find((p) => p.id === active)?.Component;
  return (
    <div className="h-screen flex flex-col relative">
      <Toolbar />
      <div className="flex-1 flex min-h-0">
        <div className="w-12 bg-panel border-r border-border flex flex-col">
          {PANELS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActive(id)}
              className={`h-12 flex flex-col items-center justify-center text-[9px] uppercase tracking-wider transition-colors ${
                active === id ? 'bg-panel-2 text-accent' : 'text-muted hover:text-text hover:bg-panel-2'
              }`}
              title={label}
            >
              <Icon className="w-4 h-4" />
              <span className="mt-0.5">{label}</span>
            </button>
          ))}
        </div>
        <div className="w-80 bg-panel border-r border-border overflow-y-auto">
          <ErrorBoundary>
            {ActivePanel ? <ActivePanel /> : null}
          </ErrorBoundary>
        </div>
        <div className="flex-1 min-w-0">
          <ErrorBoundary>
            <Preview />
          </ErrorBoundary>
        </div>
      </div>

      {dragOver && (
        <div className="absolute inset-0 bg-accent/20 border-4 border-accent border-dashed flex items-center justify-center pointer-events-none z-50">
          <div className="text-2xl text-accent font-bold tracking-widest">Drop .nhlsb to open</div>
        </div>
      )}
    </div>
  );
}

function App() {
  // Route check: native scoreboard windows are tagged via initialization_script
  // before any JS runs. Browser fallback uses /scoreboard or #/scoreboard.
  const isFullscreen = (window as any).__NHLSB_SCOREBOARD__ === true
                    || window.location.pathname === '/scoreboard'
                    || window.location.hash === '#/scoreboard';
  return (
    <ErrorBoundary>
      {isFullscreen ? <FullscreenScoreboard /> : <Editor />}
    </ErrorBoundary>
  );
}

export default App;
