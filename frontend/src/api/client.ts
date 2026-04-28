import type { Project, GameSummary, GameState, BackendStatus } from '@/types/project';
import { API_BASE } from '@/lib/config';

async function j<T>(r: Response): Promise<T> {
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}: ${await r.text()}`);
  return r.json() as Promise<T>;
}

const u = (p: string) => `${API_BASE}${p}`;

export const api = {
  getProject:   (): Promise<Project> => fetch(u('/api/project')).then((r) => j<Project>(r)),
  putProject:   (p: Project): Promise<Project> =>
    fetch(u('/api/project'), { method: 'PUT', headers: { 'content-type': 'application/json' }, body: JSON.stringify(p) }).then((r) => j<Project>(r)),
  saveProject:  (filename: string): Promise<{ path: string }> =>
    fetch(u('/api/project/save'), { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ filename }) }).then((r) => j<{ path: string }>(r)),
  loadProject:  (filename: string): Promise<Project> =>
    fetch(u('/api/project/load'), { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ filename }) }).then((r) => j<Project>(r)),
  listProjects: (): Promise<string[]> => fetch(u('/api/projects')).then((r) => j<string[]>(r)),
  teams:        (): Promise<Record<string, { primary: string; secondary: string; emblem: string }>> =>
    fetch(u('/api/teams')).then((r) => j(r)),
  gamesToday:   (): Promise<GameSummary[]> => fetch(u('/api/games/today')).then((r) => j<GameSummary[]>(r)),
  game:         (id: number): Promise<GameState> => fetch(u(`/api/games/${id}`)).then((r) => j<GameState>(r)),
  status:       (): Promise<BackendStatus> => fetch(u('/api/status')).then((r) => j<BackendStatus>(r)),
  health:       (): Promise<{ ok: boolean; bundled: boolean }> => fetch(u('/api/health')).then((r) => j(r)),
  uploadSprite: async (file: File): Promise<{ path: string }> => {
    const fd = new FormData();
    fd.append('file', file);
    return fetch(u('/api/assets/sprites'), { method: 'POST', body: fd }).then((r) => j<{ path: string }>(r));
  },
};
