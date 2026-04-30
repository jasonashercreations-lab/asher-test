import { useEffect, useState } from 'react';
import { api } from '@/api/client';

/** Modal for picking a favorite team. Renders a grid of all 32 NHL team
 *  abbreviations with their primary color as a swatch. Click a team to
 *  select; the choice is reported via onSelect. The caller decides where
 *  to persist (per-project, localStorage global, or both). */
export function FavoriteTeamModal({
  open,
  current,
  onSelect,
  onClose,
}: {
  open: boolean;
  current: string;
  onSelect: (abbrev: string) => void;
  onClose: () => void;
}) {
  const [teams, setTeams] = useState<Record<string, { primary: string; secondary: string }>>({});

  useEffect(() => {
    if (!open) return;
    api.teams().then(setTeams).catch(() => setTeams({}));
  }, [open]);

  if (!open) return null;

  const teamList = Object.entries(teams).sort(([a], [b]) => a.localeCompare(b));

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70"
      onClick={onClose}
    >
      <div
        className="bg-panel border border-border rounded-lg p-4 max-w-md w-full max-h-[80vh] overflow-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold">Pick your favorite team</h2>
          <button
            onClick={onClose}
            className="text-muted hover:text-fg text-lg leading-none"
            aria-label="Close"
          >
            ×
          </button>
        </div>
        <p className="text-[10px] text-muted mb-3">
          Your favorite team's games will be pinned to the top of the list.
        </p>
        <div className="grid grid-cols-4 gap-2">
          {teamList.map(([abbrev, { primary, secondary }]) => {
            const isSelected = abbrev === current;
            return (
              <button
                key={abbrev}
                onClick={() => {
                  onSelect(abbrev);
                  onClose();
                }}
                className={`rounded p-2 flex flex-col items-center gap-1 border transition-colors ${
                  isSelected
                    ? 'border-accent bg-panel-2'
                    : 'border-border bg-panel-2 hover:border-accent/60'
                }`}
                title={abbrev}
              >
                <div
                  className="w-8 h-8 rounded"
                  style={{
                    background: `linear-gradient(135deg, ${primary} 50%, ${secondary} 50%)`,
                  }}
                />
                <span className="font-mono text-xs font-bold">{abbrev}</span>
              </button>
            );
          })}
          {teamList.length === 0 && (
            <p className="col-span-4 text-center text-xs text-muted py-4">
              Loading teams…
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
