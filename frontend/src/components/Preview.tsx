import { useEffect, useState } from 'react';
import { subscribePreview } from '@/api/ws';

export function Preview() {
  const [src, setSrc] = useState<string | null>(null);
  const [zoom, setZoom] = useState(2);
  const [lastTick, setLastTick] = useState(Date.now());

  useEffect(() => {
    const unsub = subscribePreview((url) => {
      setSrc(url);
      setLastTick(Date.now());
    });
    return unsub;
  }, []);

  return (
    <div className="h-full flex flex-col bg-bg">
      <div className="flex items-center justify-between px-3 py-2 border-b border-border bg-panel">
        <div className="text-xs text-muted uppercase tracking-wider font-semibold">Preview</div>
        <div className="flex items-center gap-3 text-xs text-muted">
          <span>Zoom</span>
          {[1, 2, 3, 4, 6, 8].map((z) => (
            <button
              key={z}
              onClick={() => setZoom(z)}
              className={`px-2 py-0.5 rounded text-xs ${zoom === z ? 'bg-accent text-black' : 'hover:bg-panel-2'}`}
            >
              {z}×
            </button>
          ))}
        </div>
      </div>
      <div className="flex-1 overflow-auto flex items-center justify-center p-6 bg-bg">
        {src ? (
          <img
            src={src}
            alt="preview"
            style={{ imageRendering: 'pixelated', transform: `scale(${zoom})`, transformOrigin: 'center' }}
            className="block"
          />
        ) : (
          <div className="text-muted text-sm">Connecting…</div>
        )}
      </div>
      <div className="text-[10px] text-muted px-3 py-1 border-t border-border bg-panel">
        Last frame: {new Date(lastTick).toLocaleTimeString()}
      </div>
    </div>
  );
}
