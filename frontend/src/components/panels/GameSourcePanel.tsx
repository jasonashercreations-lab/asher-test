import { useEffect, useState } from 'react';
import { useProjectStore } from '@/store/project';
import { api } from '@/api/client';
import { Button, Input, Select, Section, Field, Switch } from '@/components/ui/primitives';
import type { GameSummary } from '@/types/project';
import { RefreshCw, Radio, FlaskConical } from 'lucide-react';

export function GameSourcePanel() {
  const project = useProjectStore((s) => s.project);
  const update = useProjectStore((s) => s.updateProject);
  const [games, setGames] = useState<GameSummary[]>([]);
  const [loading, setLoading] = useState(false);

  const refresh = async () => {
    setLoading(true);
    try { setGames(await api.gamesToday()); }
    catch { setGames([]); }
    finally { setLoading(false); }
  };
  useEffect(() => { refresh(); }, []);

  if (!project) return null;
  const src = project.source;
  const isNHL = src.kind === 'nhl';

  return (
    <div>
      <Section title="Source">
        <div className="grid grid-cols-2 gap-1">
          <Button
            variant={isNHL ? 'accent' : 'default'}
            onClick={() => update((p) => { p.source = { kind: 'nhl', team_filter: null, game_id: null, poll_interval_sec: 10 }; })}
          >
            <Radio className="w-3 h-3" /> Live NHL
          </Button>
          <Button
            variant={!isNHL ? 'accent' : 'default'}
            onClick={() => update((p) => {
              if (p.source.kind !== 'mock') {
                p.source = {
                  kind: 'mock',
                  state: {
                    away: { abbrev: 'WSH', score: 0, shots: 15, hits: 33, blocks: 14, pim: 4, takeaways: 2, giveaways: 1, faceoff_win_pct: 52, penalty_remaining_sec: 0 },
                    home: { abbrev: 'CAR', score: 2, shots: 25, hits: 28, blocks: 8, pim: 8, takeaways: 3, giveaways: 7, faceoff_win_pct: 48, penalty_remaining_sec: 0 },
                    period_label: 'INT.',
                    clock: '04:40',
                    intermission: true,
                  },
                };
              }
            })}
          >
            <FlaskConical className="w-3 h-3" /> Mock
          </Button>
        </div>
      </Section>

      {isNHL && src.kind === 'nhl' && (
        <>
          <Section title="Game" action={
            <Button variant="ghost" onClick={refresh} disabled={loading} className="h-6 px-2">
              <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
            </Button>
          }>
            <Field label="Team filter">
              <Input
                placeholder="any"
                className="w-24 text-right uppercase"
                maxLength={3}
                value={src.team_filter ?? ''}
                onChange={(e) => update((p) => {
                  if (p.source.kind === 'nhl') p.source.team_filter = e.target.value.toUpperCase() || null;
                })}
              />
            </Field>
            <Field label="Specific game">
              <Select
                value={src.game_id?.toString() ?? ''}
                onChange={(e) => update((p) => {
                  if (p.source.kind === 'nhl') p.source.game_id = e.target.value ? parseInt(e.target.value) : null;
                })}
              >
                <option value="">Auto (first live)</option>
                {games.map((g) => (
                  <option key={g.id} value={g.id}>
                    {g.away} @ {g.home} — {g.state}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Poll interval">
              <div className="flex items-center gap-2">
                <Input
                  type="number" min={2} max={60} step={1}
                  value={src.poll_interval_sec}
                  className="w-16 text-right"
                  onChange={(e) => update((p) => {
                    if (p.source.kind === 'nhl') p.source.poll_interval_sec = parseFloat(e.target.value) || 10;
                  })}
                />
                <span className="text-xs text-muted">s</span>
              </div>
            </Field>
          </Section>
        </>
      )}

      {!isNHL && src.kind === 'mock' && (
        <>
          <Section title="Mock — Score/Clock">
            <Field label="Period">
              <Input
                value={src.state.period_label}
                className="w-20 text-center"
                onChange={(e) => update((p) => { if (p.source.kind === 'mock') p.source.state.period_label = e.target.value; })}
              />
            </Field>
            <Field label="Clock">
              <Input
                value={src.state.clock}
                className="w-20 text-center font-mono"
                onChange={(e) => update((p) => { if (p.source.kind === 'mock') p.source.state.clock = e.target.value; })}
              />
            </Field>
          </Section>
          {(['away', 'home'] as const).map((side) => (
            <Section key={side} title={side === 'away' ? 'Away team' : 'Home team'}>
              <Field label="Abbrev">
                <Input
                  className="w-16 text-center uppercase"
                  maxLength={3}
                  value={src.state[side].abbrev}
                  onChange={(e) => update((p) => { if (p.source.kind === 'mock') p.source.state[side].abbrev = e.target.value.toUpperCase(); })}
                />
              </Field>
              {(['score', 'shots', 'hits', 'blocks', 'pim', 'takeaways', 'giveaways', 'faceoff_win_pct'] as const).map((k) => (
                <Field key={k} label={k === 'faceoff_win_pct' ? 'fo%' : k}>
                  <Input
                    type="number" min={0}
                    className="w-16 text-right"
                    value={src.state[side][k]}
                    onChange={(e) => update((p) => { if (p.source.kind === 'mock') p.source.state[side][k] = parseInt(e.target.value) || 0; })}
                  />
                </Field>
              ))}
              <Field label="Penalty (sec)">
                <Input
                  type="number" min={0} max={600}
                  className="w-16 text-right"
                  value={src.state[side].penalty_remaining_sec}
                  onChange={(e) => update((p) => { if (p.source.kind === 'mock') p.source.state[side].penalty_remaining_sec = parseInt(e.target.value) || 0; })}
                />
              </Field>
            </Section>
          ))}
        </>
      )}
    </div>
  );
}
