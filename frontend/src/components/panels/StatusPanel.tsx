import { useEffect, useState } from 'react';
import { api } from '@/api/client';
import { Section, Field } from '@/components/ui/primitives';
import type { BackendStatus } from '@/types/project';
import { CheckCircle, AlertTriangle } from 'lucide-react';

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

  return (
    <div>
      <Section title="Data source">
        <Field label="Last fetch">
          <span className="text-xs font-mono">{ts}</span>
        </Field>
        <Field label="Status">
          {status.last_fetch_ok ? (
            <span className="flex items-center gap-1 text-xs text-green-400">
              <CheckCircle className="w-3 h-3" /> OK
            </span>
          ) : (
            <span className="flex items-center gap-1 text-xs text-amber-400">
              <AlertTriangle className="w-3 h-3" /> {status.last_error || 'error'}
            </span>
          )}
        </Field>
      </Section>

      <Section title="Current state">
        <div className="grid grid-cols-3 text-xs gap-y-1">
          <div className="text-muted">Period</div>
          <div className="col-span-2 font-mono">{status.current_state.period_label} {status.current_state.clock}</div>

          <div className="text-muted">Score</div>
          <div className="col-span-2 font-mono">
            {status.current_state.away.abbrev} {status.current_state.away.score}
            {' — '}
            {status.current_state.home.score} {status.current_state.home.abbrev}
          </div>

          <div className="text-muted col-span-3 mt-2 mb-1 text-[10px] uppercase">Stats</div>
          {(['shots', 'hits', 'blocks', 'pim', 'takeaways', 'giveaways', 'faceoff_win_pct'] as const).map((k) => (
            <FragRow key={k} label={k}
              away={status.current_state.away[k]}
              home={status.current_state.home[k]}
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
