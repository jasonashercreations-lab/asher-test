import { create } from 'zustand';
import { api } from '@/api/client';
import type { Project } from '@/types/project';

interface ProjectStore {
  project: Project | null;
  loading: boolean;
  error: string | null;
  fetchProject: () => Promise<void>;
  updateProject: (mut: (p: Project) => void) => void;
  replaceProject: (p: Project) => void;
}

let pushTimer: number | null = null;
const PUSH_DEBOUNCE_MS = 100;

const schedulePush = (p: Project) => {
  if (pushTimer) window.clearTimeout(pushTimer);
  pushTimer = window.setTimeout(() => {
    api.putProject(p).catch((e) => console.error('PUT /api/project failed', e));
    pushTimer = null;
  }, PUSH_DEBOUNCE_MS);
};

export const useProjectStore = create<ProjectStore>((set, get) => ({
  project: null,
  loading: false,
  error: null,
  fetchProject: async () => {
    set({ loading: true, error: null });
    try {
      const p = await api.getProject();
      set({ project: p, loading: false });
    } catch (e: any) {
      set({ loading: false, error: String(e?.message || e) });
    }
  },
  updateProject: (mut) => {
    const p = get().project;
    if (!p) return;
    // Structuredclone for immutable update
    const next = structuredClone(p);
    mut(next);
    set({ project: next });
    schedulePush(next);
  },
  replaceProject: (p) => {
    set({ project: p });
    schedulePush(p);
  },
}));
