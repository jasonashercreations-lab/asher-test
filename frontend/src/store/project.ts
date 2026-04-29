import { create } from 'zustand';
import { api } from '@/api/client';
import type { Project } from '@/types/project';

/** Autosave / undo / redo capable project store.
 *
 *  - `updateProject(mut)` runs the mutator on a structured clone of the current
 *    project, sets it as the live state, debounces a PUT to the engine (~100ms),
 *    and pushes the previous state onto the undo stack.
 *  - `undo()` / `redo()` walk the history and re-PUT to the backend.
 *  - `triggerAutosave()` writes to disk under the current project's filename
 *    (or "Untitled.nhlsb" by default) on a slower debounce (~3s after last edit).
 *  - `dirty` is true when there are unsaved disk changes.
 */

interface SaveStatus {
  lastSavedAt: number | null;     // unix seconds; null = never
  saving: boolean;
  saveError: string | null;
}

interface ProjectStore {
  project: Project | null;
  loading: boolean;
  error: string | null;

  // History
  past: Project[];
  future: Project[];

  // Save state
  currentFilename: string;        // empty if not saved yet
  dirty: boolean;
  save: SaveStatus;

  fetchProject:    () => Promise<void>;
  updateProject:   (mut: (p: Project) => void) => void;
  replaceProject:  (p: Project, opts?: { filename?: string }) => void;
  undo:            () => void;
  redo:            () => void;
  canUndo:         () => boolean;
  canRedo:         () => boolean;
  saveNow:         (filename?: string) => Promise<void>;
  setFilename:     (name: string) => void;
}

const HISTORY_LIMIT     = 50;
const PUSH_DEBOUNCE_MS  = 100;
const AUTOSAVE_DELAY_MS = 3000;

let pushTimer: number | null = null;
let autosaveTimer: number | null = null;

const schedulePush = (p: Project, onDone?: () => void) => {
  if (pushTimer) window.clearTimeout(pushTimer);
  pushTimer = window.setTimeout(() => {
    api.putProject(p)
      .catch((e) => console.error('PUT /api/project failed', e))
      .finally(() => { onDone?.(); });
    pushTimer = null;
  }, PUSH_DEBOUNCE_MS);
};

const scheduleAutosave = (
  store: () => ProjectStore,
  set: (s: Partial<ProjectStore>) => void,
) => {
  if (autosaveTimer) window.clearTimeout(autosaveTimer);
  autosaveTimer = window.setTimeout(() => {
    const s = store();
    if (!s.project || !s.dirty) return;
    void s.saveNow(s.currentFilename || undefined);
  }, AUTOSAVE_DELAY_MS);
};

export const useProjectStore = create<ProjectStore>((set, get) => ({
  project: null,
  loading: false,
  error: null,

  past: [],
  future: [],

  currentFilename: '',
  dirty: false,
  save: { lastSavedAt: null, saving: false, saveError: null },

  fetchProject: async () => {
    set({ loading: true, error: null });
    try {
      const p = await api.getProject();
      set({ project: p, loading: false, dirty: false });
    } catch (e: any) {
      set({ loading: false, error: String(e?.message || e) });
    }
  },

  updateProject: (mut) => {
    const cur = get().project;
    if (!cur) return;
    const next = structuredClone(cur);
    mut(next);
    // Push current onto past, clear future (new branch)
    const past = [...get().past, cur].slice(-HISTORY_LIMIT);
    set({ project: next, past, future: [], dirty: true });
    schedulePush(next);
    scheduleAutosave(() => get(), set as any);
  },

  replaceProject: (p, opts) => {
    set({
      project: p,
      past: [],
      future: [],
      dirty: false,
      currentFilename: opts?.filename ?? get().currentFilename,
    });
    schedulePush(p);
  },

  undo: () => {
    const { past, project, future } = get();
    if (!project || past.length === 0) return;
    const prev = past[past.length - 1];
    const newPast = past.slice(0, -1);
    const newFuture = [project, ...future];
    set({ project: prev, past: newPast, future: newFuture, dirty: true });
    schedulePush(prev);
    scheduleAutosave(() => get(), set as any);
  },

  redo: () => {
    const { past, project, future } = get();
    if (!project || future.length === 0) return;
    const next = future[0];
    const newFuture = future.slice(1);
    const newPast = [...past, project].slice(-HISTORY_LIMIT);
    set({ project: next, past: newPast, future: newFuture, dirty: true });
    schedulePush(next);
    scheduleAutosave(() => get(), set as any);
  },

  canUndo: () => get().past.length > 0,
  canRedo: () => get().future.length > 0,

  saveNow: async (filename?: string) => {
    const s = get();
    const name = filename || s.currentFilename
                || `${(s.project?.name || 'Untitled').replace(/[^A-Za-z0-9._\- ]/g, '_')}.nhlsb`;
    set({ save: { ...s.save, saving: true, saveError: null } });
    try {
      await api.saveProject(name);
      set({
        save: { lastSavedAt: Date.now() / 1000, saving: false, saveError: null },
        dirty: false,
        currentFilename: name.endsWith('.nhlsb') ? name : `${name}.nhlsb`,
      });
    } catch (e: any) {
      set({ save: { ...get().save, saving: false, saveError: String(e?.message || e) } });
    }
  },

  setFilename: (name) => set({ currentFilename: name }),
}));
