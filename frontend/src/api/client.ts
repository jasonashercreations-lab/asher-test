import type {
  Project, GameSummary, GameState, BackendStatus, AssetList,
} from '@/types/project';
import { API_BASE } from '@/lib/config';

async function j<T>(r: Response): Promise<T> {
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}: ${await r.text()}`);
  return r.json() as Promise<T>;
}

const u = (p: string) => `${API_BASE}${p}`;

export const api = {
  getProject:    (): Promise<Project> => fetch(u('/api/project')).then((r) => j<Project>(r)),
  putProject:    (p: Project): Promise<Project> =>
    fetch(u('/api/project'), {
      method: 'PUT',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(p),
    }).then((r) => j<Project>(r)),

  saveProject:   (filename: string): Promise<{ path: string }> =>
    fetch(u('/api/project/save'), {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ filename }),
    }).then((r) => j<{ path: string }>(r)),

  loadProject:   (filename: string): Promise<Project> =>
    fetch(u('/api/project/load'), {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ filename }),
    }).then((r) => j<Project>(r)),

  importProject: async (file: File): Promise<{ path: string; project: Project }> => {
    const fd = new FormData();
    fd.append('file', file);
    return fetch(u('/api/project/import'), { method: 'POST', body: fd })
      .then((r) => j<{ path: string; project: Project }>(r));
  },

  deleteProject: (filename: string): Promise<{ ok: boolean }> =>
    fetch(u(`/api/projects/${encodeURIComponent(filename)}`), { method: 'DELETE' })
      .then((r) => j<{ ok: boolean }>(r)),

  listProjects:  (): Promise<string[]> => fetch(u('/api/projects')).then((r) => j<string[]>(r)),

  teams:         (): Promise<Record<string, { primary: string; secondary: string; emblem: string }>> =>
    fetch(u('/api/teams')).then((r) => j(r)),

  gamesToday:    (): Promise<GameSummary[]> => fetch(u('/api/games/today')).then((r) => j<GameSummary[]>(r)),
  gamesRange:    (start?: string, days = 7): Promise<Record<string, GameSummary[]>> => {
    const qs = new URLSearchParams();
    if (start) qs.set('start', start);
    qs.set('days', String(days));
    return fetch(u(`/api/games/range?${qs.toString()}`)).then((r) =>
      j<Record<string, GameSummary[]>>(r));
  },
  game:          (id: number): Promise<GameState> => fetch(u(`/api/games/${id}`)).then((r) => j<GameState>(r)),

  status:        (): Promise<BackendStatus> => fetch(u('/api/status')).then((r) => j<BackendStatus>(r)),
  health:        (): Promise<{ ok: boolean; bundled: boolean }> => fetch(u('/api/health')).then((r) => j(r)),

  // ---- Assets ----
  listAssets:    (): Promise<AssetList> => fetch(u('/api/assets')).then((r) => j<AssetList>(r)),

  uploadAsset:   async (kind: 'sprites'|'fonts'|'logos'|'banners', file: File): Promise<{ path: string }> => {
    const fd = new FormData();
    fd.append('file', file);
    return fetch(u(`/api/assets/${kind}`), { method: 'POST', body: fd })
      .then((r) => j<{ path: string }>(r));
  },

  deleteAsset:   (kind: 'sprites'|'fonts'|'logos'|'banners', name: string): Promise<{ ok: boolean }> =>
    fetch(u(`/api/assets/${kind}/${encodeURIComponent(name)}`), { method: 'DELETE' })
      .then((r) => j<{ ok: boolean }>(r)),

  assetUrl:      (kind: 'sprites'|'fonts'|'logos'|'banners', name: string): string =>
    u(`/api/assets/${kind}/${encodeURIComponent(name)}`),

  // Per-output preview thumbnail URL (uses cache-busting query string).
  outputPreviewUrl: (idx: number): string => u(`/api/output/${idx}/preview.png?t=${Date.now()}`),

  // Trigger a goal banner animation (mock testing)
  triggerGoal: (team: string, side: 'away' | 'home', durationSec = 3.0):
      Promise<{ ok: boolean; team: string; side: string }> =>
    fetch(u('/api/animation/goal'), {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ team, side, duration_sec: durationSec }),
    }).then((r) => j(r)),

  // ---- Mock control (lightweight, no full project PUT) ----
  mockSetPaused: (paused: boolean) =>
    fetch(u('/api/mock/paused'), {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ paused }),
    }).then((r) => j<{ ok: boolean }>(r)),

  mockGoal: (side: 'away' | 'home') =>
    fetch(u('/api/mock/goal'), {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ side }),
    }).then((r) => j<{ ok: boolean }>(r)),

  mockPenalty: (side: 'away' | 'home', durationSec = 120) =>
    fetch(u('/api/mock/penalty'), {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ side, duration_sec: durationSec }),
    }).then((r) => j<{ ok: boolean }>(r)),

  mockClearPenalties: () =>
    fetch(u('/api/mock/clear_penalties'), { method: 'POST' }).then((r) =>
      j<{ ok: boolean }>(r)),

  mockEndPeriod: () =>
    fetch(u('/api/mock/end_period'), { method: 'POST' }).then((r) =>
      j<{ ok: boolean }>(r)),

  mockSetPeriod: (periodLabel: string) =>
    fetch(u('/api/mock/period'), {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ period_label: periodLabel }),
    }).then((r) => j<{ ok: boolean }>(r)),

  mockSetClock: (clock: string) =>
    fetch(u('/api/mock/clock'), {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ clock }),
    }).then((r) => j<{ ok: boolean }>(r)),

  mockSetTeam: (side: 'away' | 'home', abbrev: string) =>
    fetch(u('/api/mock/team'), {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ side, abbrev }),
    }).then((r) => j<{ ok: boolean }>(r)),

  mockSetScore: (side: 'away' | 'home', score: number) =>
    fetch(u('/api/mock/score'), {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ side, score }),
    }).then((r) => j<{ ok: boolean }>(r)),

  mockSetStat: (side: 'away' | 'home', field: string, value: number) =>
    fetch(u('/api/mock/stat'), {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ side, field, value }),
    }).then((r) => j<{ ok: boolean }>(r)),

  // Backwards-compat alias
  uploadSprite:  async (file: File): Promise<{ path: string }> => {
    const fd = new FormData();
    fd.append('file', file);
    return fetch(u('/api/assets/sprites'), { method: 'POST', body: fd })
      .then((r) => j<{ path: string }>(r));
  },
};
