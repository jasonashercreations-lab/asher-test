// API base URL. In dev with Vite proxy this can be empty (same-origin).
// In Tauri build, the frontend is served from tauri://localhost while the
// backend lives at 127.0.0.1:8765 — must use absolute URL.
//
// Set VITE_API_BASE='' for dev (uses Vite proxy);
// leave it as the default 'http://127.0.0.1:8765' for Tauri.

const FROM_ENV = (import.meta as any).env?.VITE_API_BASE as string | undefined;

export const API_BASE: string =
  FROM_ENV !== undefined ? FROM_ENV : 'http://127.0.0.1:8765';

export const WS_BASE: string = API_BASE.replace(/^http/, 'ws');
