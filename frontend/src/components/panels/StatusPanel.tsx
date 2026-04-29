import { useEffect, useState } from 'react';
import { api } from '@/api/client';
import { Section, Field } from '@/components/ui/primitives';
import type { BackendStatus } from '@/types/project';
import { CheckCircle, AlertTriangle, ExternalLink } from 'lucide-react';

export function StatusPanel() {
  const [status, setStatus] = useState<BackendStatus | null>(null);

  useEffect(() => {
    const fetch = () => api.status().then(setStatus).catch(() => {});
    fetch();
    const t = setInterval(fetch, 2000);
    return () => clearInterval(t);
  }, []);

  if (!status) return <div className="px-3 py-4 text-xs text-muted">Loading…</div>;

  const ts = status.last_fetch_at ? new Date(status.last_fetch_at * 1000).toLocaleTimeString() : '—';
  const meta = status.source_meta || {};
  const activeGame = meta.active_game_id;

  const gameCenterUrl = activeGame
    ? `https://www.nhl.com/gamecenter/${activeGame}`
    : null;

  return (
    <div>
      <Section title="Data source">
        <Field label="Source">
          <span className="text-xs font-mono">{status.source_kind || 'unknown'}</span>
        </Field>
        {status.source_kind === 'nhl' && (
          <>
            <Field label="Active game">
              {activeGame ? (
                <a
                  href={gameCenterUrl!}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs font-mono text-accent hover:underline flex items-center gap-1"
                  title="Open on NHL.com"
                >
                  {activeGame} <ExternalLink className="w-3 h-3" />
                </a>
              ) : (
                <span className="text-xs text-muted">—</span>
              )}
            </Field>
            <Field label="Team filter">
              <span className="text-xs font-mono">{meta.team_filter || '—'}</span>
            </Field>
            <Field label="Poll interval">
              <span className="text-xs font-mono">{meta.poll_interval_sec}s</span>
            </Field>
          </>
        )}
        <Field label="Last fetch">
          <span className="text-xs font-mono">{ts}</span>
        </Field>
        <Field label="Status">
          {status.last_fetch_ok ? (
            <span className="flex items-center gap-1 text-xs text-green-400">
              <CheckCircle className="w-3 h-3" /> OK
            </span>
          ) : (
            <span className="flex items-center gap-1 text-xs text-amber-400" title={status.last_error}>
              <AlertTriangle className="w-3 h-3" /> {status.last_error || 'error'}
            </span>
          )}
        </Field>
      </Section>

      <Section title="Outputs">
        <Field label="WS subscribers">
          <span className="text-xs font-mono">{status.subscriber_count}</span>
        </Field>
      </Section>

      <Section title="Current state">
        <div className="grid grid-cols-3 text-xs gap-y-1">
          <div className="text-muted">Period</div>
          <div className="col-span-2 font-mono">
            {status.current_state.period_label} {status.current_state.clock}
            {status.current_state.intermission && (
              <span className="ml-1 text-amber-400 text-[10px]">INT</span>
            )}
          </div>

          <div className="text-muted">Score</div>
          <div className="col-span-2 font-mono">
            {status.current_state.away.abbrev} {status.current_state.away.score}
            {' — '}
            {status.current_state.home.score} {status.current_state.home.abbrev}
          </div>

          <div className="text-muted col-span-3 mt-2 mb-1 text-[10px] uppercase">Stats</div>
          {(['shots', 'hits', 'blocks', 'pim', 'takeaways', 'giveaways', 'faceoff_win_pct'] as const).map((k) => (
            <FragRow key={k} label={k}
              away={(status.current_state.away as any)[k] ?? 0}
              home={(status.current_state.home as any)[k] ?? 0}
            />
          ))}
        </div>
      </Section>
    </div>
  );
}

function FragRow({ label, away, home }: { label: string; away: number; home: number }) {
  return (
    <>
      <div className="text-muted">{label}</div>
      <div className="font-mono text-right">{away}</div>
      <div className="font-mono text-right">{home}</div>
    </>
  );
}
