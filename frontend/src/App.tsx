import { useEffect, useState } from 'react';
import { useProjectStore } from '@/store/project';
import { Toolbar } from '@/components/Toolbar';
import { Preview } from '@/components/Preview';
import { FullscreenScoreboard } from '@/components/FullscreenScoreboard';
import { GameSourcePanel } from '@/components/panels/GameSourcePanel';
import { ThemePanel } from '@/components/panels/ThemePanel';
import { LayoutPanel } from '@/components/panels/LayoutPanel';
import { TeamsPanel } from '@/components/panels/TeamsPanel';
import { OutputPanel } from '@/components/panels/OutputPanel';
import { StatusPanel } from '@/components/panels/StatusPanel';
import { Radio, Palette, LayoutGrid, Users, Cable, Activity } from 'lucide-react';

const PANELS = [
  { id: 'source', label: 'Source',  icon: Radio,      Component: GameSourcePanel },
  { id: 'theme',  label: 'Theme',   icon: Palette,    Component: ThemePanel },
  { id: 'layout', label: 'Layout',  icon: LayoutGrid, Component: LayoutPanel },
  { id: 'teams',  label: 'Teams',   icon: Users,      Component: TeamsPanel },
  { id: 'output', label: 'Output',  icon: Cable,      Component: OutputPanel },
  { id: 'status', label: 'Status',  icon: Activity,   Component: StatusPanel },
] as const;

type PanelId = typeof PANELS[number]['id'];

function Editor() {
  const fetchProject = useProjectStore((s) => s.fetchProject);
  const project = useProjectStore((s) => s.project);
  const error = useProjectStore((s) => s.error);
  const [active, setActive] = useState<PanelId>('source');

  useEffect(() => { fetchProject(); }, [fetchProject]);

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
    return <div className="h-screen flex items-center justify-center text-muted">Loading...</div>;
  }

  const ActivePanel = PANELS.find((p) => p.id === active)?.Component;
  return (
    <div className="h-screen flex flex-col">
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
          {ActivePanel ? <ActivePanel /> : null}
        </div>
        <div className="flex-1 min-w-0">
          <Preview />
        </div>
      </div>
    </div>
  );
}

function App() {
  // Route check: native scoreboard windows are tagged via initialization_script
  // before any JS runs. Browser fallback uses /scoreboard or #/scoreboard.
  const isFullscreen = (window as any).__NHLSB_SCOREBOARD__ === true
                    || window.location.pathname === '/scoreboard'
                    || window.location.hash === '#/scoreboard';
  return isFullscreen ? <FullscreenScoreboard /> : <Editor />;
}

export default App;
