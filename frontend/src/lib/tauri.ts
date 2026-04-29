/** Thin wrapper around the Tauri global injected by withGlobalTauri:true.
 *  Returns null when running in a plain browser (Pi deployment, dev preview). */

export type MonitorInfo = {
  index: number;
  name: string;
  x: number;
  y: number;
  width: number;
  height: number;
  scale_factor: number;
  is_primary: boolean;
};

function tauri(): any {
  return (window as any).__TAURI__ ?? null;
}

export function isTauri(): boolean {
  return tauri() !== null;
}

export async function listMonitors(): Promise<MonitorInfo[] | null> {
  const t = tauri();
  if (!t) return null;
  try {
    return await t.invoke('list_monitors');
  } catch (e) {
    console.warn('list_monitors failed:', e);
    return null;
  }
}

export async function openScoreboardWindow(opts: {
  monitorIndex: number;
  fullscreen: boolean;
}): Promise<boolean> {
  const t = tauri();
  if (!t) return false;
  try {
    await t.invoke('open_scoreboard_window', {
      monitorIndex: opts.monitorIndex,
      fullscreen: opts.fullscreen,
    });
    return true;
  } catch (e) {
    console.error('open_scoreboard_window failed:', e);
    return false;
  }
}
