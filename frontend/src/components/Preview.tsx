import { useEffect, useRef, useState, useCallback } from 'react';
import { subscribePreview } from '@/api/ws';
import { ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';

/**
 * Preview pane with mouse-wheel zoom + drag pan.
 *
 * Default state: image auto-fits the pane (zoom = "fit"). Scroll the wheel
 * to zoom in/out around the cursor. Click and drag to pan when zoomed in.
 * The "Fit" button or double-click resets.
 */
export function Preview() {
  const [src, setSrc] = useState<string | null>(null);
  const [lastTick, setLastTick] = useState(Date.now());

  // 1.0 = fit-to-pane (auto). >1 = zoomed in.
  const [scale, setScale] = useState(1);
  const [tx, setTx] = useState(0);
  const [ty, setTy] = useState(0);
  const dragStart = useRef<{ x: number; y: number; tx: number; ty: number } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const unsub = subscribePreview((url) => {
      setSrc(url);
      setLastTick(Date.now());
    });
    return unsub;
  }, []);

  const reset = useCallback(() => { setScale(1); setTx(0); setTy(0); }, []);

  // Wheel zoom — anchor zoom around cursor position
  const onWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;
    const cx = e.clientX - rect.left - rect.width / 2;
    const cy = e.clientY - rect.top - rect.height / 2;
    const factor = e.deltaY > 0 ? 0.9 : 1.1;
    const newScale = Math.min(8, Math.max(0.25, scale * factor));
    if (newScale === scale) return;
    // Adjust translation so the pixel under the cursor stays put
    const ratio = newScale / scale;
    setTx((cx - (cx - tx) * ratio));
    setTy((cy - (cy - ty) * ratio));
    setScale(newScale);
  };

  const onMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return;
    dragStart.current = { x: e.clientX, y: e.clientY, tx, ty };
  };
  const onMouseMove = (e: React.MouseEvent) => {
    const d = dragStart.current;
    if (!d) return;
    setTx(d.tx + (e.clientX - d.x));
    setTy(d.ty + (e.clientY - d.y));
  };
  const stopDrag = () => { dragStart.current = null; };

  return (
    <div className="h-full flex flex-col bg-bg">
      <div className="flex items-center justify-between px-3 py-2 border-b border-border bg-panel">
        <div className="text-xs text-muted uppercase tracking-wider font-semibold">
          Preview
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setScale((s) => Math.max(0.25, s * 0.8))}
            className="p-1 hover:bg-panel-2 rounded"
            title="Zoom out"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </button>
          <span className="text-[10px] text-muted font-mono w-10 text-center">
            {Math.round(scale * 100)}%
          </span>
          <button
            onClick={() => setScale((s) => Math.min(8, s * 1.25))}
            className="p-1 hover:bg-panel-2 rounded"
            title="Zoom in"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
          <button onClick={reset} className="p-1 hover:bg-panel-2 rounded ml-1" title="Fit to pane">
            <Maximize2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      <div
        ref={containerRef}
        className="flex-1 min-h-0 flex items-center justify-center bg-bg overflow-hidden select-none"
        style={{ cursor: dragStart.current ? 'grabbing' : (scale > 1 ? 'grab' : 'default') }}
        onWheel={onWheel}
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={stopDrag}
        onMouseLeave={stopDrag}
        onDoubleClick={reset}
      >
        {src ? (
          <img
            src={src}
            alt="preview"
            draggable={false}
            style={{
              imageRendering: 'auto',
              transform: `translate(${tx}px, ${ty}px) scale(${scale})`,
              transformOrigin: 'center center',
              transition: dragStart.current ? 'none' : 'transform 80ms ease-out',
            }}
            className="max-w-full max-h-full w-auto h-auto object-contain"
          />
        ) : (
          <div className="text-muted text-sm">Connecting…</div>
        )}
      </div>

      <div className="text-[10px] text-muted px-3 py-1 border-t border-border bg-panel">
        Last frame: {new Date(lastTick).toLocaleTimeString()} · Scroll to zoom · Drag to pan · Double-click to reset
      </div>
    </div>
  );
}
