import { useEffect, useState } from 'react';
import { subscribePreview } from '@/api/ws';

/** Fullscreen scoreboard. Opens in its own window via /scoreboard URL.
 *  No editor chrome. Image fills the viewport with aspect preserved.
 *  Press F11 (or system fullscreen) to remove window borders. */
export function FullscreenScoreboard() {
  const [src, setSrc] = useState<string | null>(null);

  useEffect(() => {
    document.title = 'Scoreboard';
    document.body.style.background = '#000';
    const unsub = subscribePreview((url) => setSrc(url));
    return unsub;
  }, []);

  return (
    <div className="fixed inset-0 bg-black flex items-center justify-center">
      {src ? (
        <img
          src={src}
          alt="scoreboard"
          style={{ imageRendering: 'pixelated' }}
          className="w-full h-full object-contain"
        />
      ) : (
        <div className="text-white/30 text-sm">Connecting...</div>
      )}
    </div>
  );
}
