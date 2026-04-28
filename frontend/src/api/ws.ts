import { WS_BASE } from '@/lib/config';

/** Subscribe to /ws/preview, call onFrame(blob URL) per frame. Auto-reconnects. */
export function subscribePreview(onFrame: (url: string) => void): () => void {
  let ws: WebSocket | null = null;
  let lastUrl: string | null = null;
  let stopped = false;
  let retryDelay = 500;

  const connect = () => {
    if (stopped) return;
    ws = new WebSocket(`${WS_BASE}/ws/preview`);
    ws.binaryType = 'blob';
    ws.onopen = () => { retryDelay = 500; };
    ws.onmessage = (ev) => {
      if (lastUrl) URL.revokeObjectURL(lastUrl);
      const url = URL.createObjectURL(ev.data as Blob);
      lastUrl = url;
      onFrame(url);
    };
    ws.onclose = () => {
      if (stopped) return;
      setTimeout(connect, retryDelay);
      retryDelay = Math.min(retryDelay * 2, 5000);
    };
    ws.onerror = () => ws?.close();
  };
  connect();
  return () => {
    stopped = true;
    ws?.close();
    if (lastUrl) URL.revokeObjectURL(lastUrl);
  };
}
