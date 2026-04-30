import { useEffect, useState } from 'react';
import { api } from '@/api/client';

/** Modal for picking a team. Used both for the user's favorite team (with
 *  the "No favorite" option enabled) AND for picking the mock-source teams
 *  (where clearing doesn't make sense). The caller decides where to persist. */
export function TeamPickerModal({
  open,
  current,
  title = 'Pick a team',
  subtitle,
  allowClear = false,
  onSelect,
  onClose,
}: {
  open: boolean;
  current: string;
  title?: string;
  subtitle?: string;
  /** When true, shows a "No favorite" option that calls onSelect(""). */
  allowClear?: boolean;
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
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      onClick={onClose}
    >
      <div
        className="bg-panel border border-border rounded-lg p-4 max-w-md w-full max-h-[80vh] overflow-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-sm font-semibold">{title}</h2>
          <button
            onClick={onClose}
            className="text-muted hover:text-fg text-lg leading-none w-6 h-6 flex items-center justify-center"
            aria-label="Close"
          >
            ×
          </button>
        </div>
        {subtitle && (
          <p className="text-[10px] text-muted mb-3">{subtitle}</p>
        )}

        {allowClear && (
          <button
            onClick={() => { onSelect(''); onClose(); }}
            className={`w-full mb-2 px-3 py-2 rounded border flex items-center gap-2 transition-colors ${
              current === ''
                ? 'border-accent bg-panel-2'
                : 'border-border bg-panel-2 hover:border-accent/60'
            }`}
          >
            <div className="w-8 h-8 rounded border border-border flex items-center justify-center text-muted text-lg">∅</div>
            <span className="text-xs font-semibold">No favorite team</span>
          </button>
        )}

        <div className="grid grid-cols-4 gap-2">
          {teamList.map(([abbrev, { primary, secondary }]) => {
            const isSelected = abbrev === current;
            return (
              <button
                key={abbrev}
                onClick={() => { onSelect(abbrev); onClose(); }}
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

/** Backwards-compat alias — keeps the old name working. */
export const FavoriteTeamModal = TeamPickerModal;
