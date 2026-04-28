import { useEffect, useState } from 'react';
import { subscribePreview } from '@/api/ws';

/**
 * Preview pane.
 *
 * The backend renders frames at the project's full layout resolution (e.g.
 * 1080×1350). Since that's typically much larger than the preview pane,
 * we let the browser downscale with high-quality smoothing — this gives
 * crisp output at any preview pane size with no pixelation.
 *
 * `object-fit: contain` keeps the aspect ratio while filling whatever
 * space is available. No zoom slider — the preview always fits the screen.
 */
export function Preview() {
  const [src, setSrc] = useState<string | null>(null);
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
        <div className="text-xs text-muted uppercase tracking-wider font-semibold">
          Preview
        </div>
        <div className="text-[10px] text-muted">Auto-fit</div>
      </div>

      <div className="flex-1 min-h-0 flex items-center justify-center p-4 bg-bg overflow-hidden">
        {src ? (
          <img
            src={src}
            alt="preview"
            // imageRendering: 'auto' tells the browser to use its highest-quality
            // resampling when downscaling. The frames arrive at full layout
            // resolution (e.g. 1080×1350) and get smoothly fit into the pane.
            style={{ imageRendering: 'auto' }}
            className="max-w-full max-h-full w-auto h-auto object-contain"
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
