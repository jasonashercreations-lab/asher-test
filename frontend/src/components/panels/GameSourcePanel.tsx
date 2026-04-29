import { useEffect, useState } from 'react';
import { useProjectStore } from '@/store/project';
import { api } from '@/api/client';
import { Button, Input, Section, Field, Switch, Slider } from '@/components/ui/primitives';
import type { GameSummary } from '@/types/project';
import {
  RefreshCw, Radio, FlaskConical, CircleDot, Plus, Minus, Pause, Play, Shield,
} from 'lucide-react';

export function GameSourcePanel() {
  const project = useProjectStore((s) => s.project);
  const update = useProjectStore((s) => s.updateProject);
  const [games, setGames] = useState<GameSummary[]>([]);
  const [teams, setTeams] = useState<Record<string, { primary: string; secondary: string }>>({});
  const [loading, setLoading] = useState(false);

  const refresh = async () => {
    setLoading(true);
    try { setGames(await api.gamesToday()); }
    catch { setGames([]); }
    finally { setLoading(false); }
  };
  useEffect(() => {
    refresh();
    api.teams().then(setTeams).catch(() => {});
    const i = setInterval(refresh, 30_000);
    return () => clearInterval(i);
  }, []);

  if (!project) return null;
  const src = project.source;
  const isNHL = src.kind === 'nhl';

  return (
    <div>
      <Section title="Source">
        <div className="grid grid-cols-2 gap-1">
          <Button
            variant={isNHL ? 'accent' : 'default'}
            onClick={() => update((p) => {
              p.source = { kind: 'nhl', team_filter: null, game_id: null,
                           poll_interval_sec: 5, auto_rotate: false, rotate_interval_sec: 0 };
            })}
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
                    away: { abbrev: 'WSH', score: 0, shots: 15, hits: 33, blocks: 14, pim: 4, takeaways: 2, giveaways: 1, faceoff_win_pct: 52, penalty_remaining_sec: 0, active_penalty_count: 0 },
                    home: { abbrev: 'CAR', score: 2, shots: 25, hits: 28, blocks: 8, pim: 8, takeaways: 3, giveaways: 7, faceoff_win_pct: 48, penalty_remaining_sec: 0, active_penalty_count: 0 },
                    period_label: '1ST',
                    clock: '15:00',
                    intermission: false,
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
          <Section title="Auto-rotate">
            <Field label="Auto-advance on FINAL">
              <Switch
                checked={src.auto_rotate}
                onChange={(b) => update((p) => {
                  if (p.source.kind === 'nhl') p.source.auto_rotate = b;
                })}
              />
            </Field>
            {src.auto_rotate && (
              <Field label="Cycle every">
                <div className="flex items-center gap-1">
                  <div className="w-32">
                    <Slider
                      value={src.rotate_interval_sec}
                      min={0} max={120} step={5}
                      onChange={(v) => update((p) => {
                        if (p.source.kind === 'nhl') p.source.rotate_interval_sec = Math.round(v);
                      })}
                    />
                  </div>
                  <span className="text-[10px] text-muted font-mono w-12 text-right">
                    {src.rotate_interval_sec === 0 ? 'off' : `${src.rotate_interval_sec}s`}
                  </span>
                </div>
              </Field>
            )}
            <p className="text-[10px] text-muted">
              On: switches to next live game when current goes FINAL. Cycle: rotates through all live games on a timer.
            </p>
          </Section>

          <Section
            title={`Live games today (${games.length})`}
            action={
              <button
                onClick={refresh}
                disabled={loading}
                className="text-xs flex items-center gap-1 text-accent hover:underline disabled:opacity-50"
                title="Refresh"
              >
                <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
              </button>
            }
          >
            <div className="space-y-1">
              <button
                onClick={() => update((p) => {
                  if (p.source.kind === 'nhl') { p.source.game_id = null; p.source.team_filter = null; }
                })}
                className={`w-full px-2 py-1.5 rounded text-xs text-left flex items-center gap-2 border ${
                  !src.game_id && !src.team_filter
                    ? 'border-accent bg-panel-2'
                    : 'border-border bg-panel-2 hover:border-accent/50'
                }`}
              >
                <CircleDot className="w-3 h-3 text-muted" />
                <span className="flex-1">Auto-pick (first live game)</span>
              </button>
              {games.map((g) => {
                const apri = teams[g.away]?.primary || '#888';
                const hpri = teams[g.home]?.primary || '#888';
                const isActive = src.game_id === g.id;
                return (
                  <button
                    key={g.id}
                    onClick={() => update((p) => {
                      if (p.source.kind === 'nhl') { p.source.game_id = g.id; p.source.team_filter = null; }
                    })}
                    className={`w-full px-2 py-1.5 rounded text-xs flex items-center gap-2 border transition-colors ${
                      isActive
                        ? 'border-accent bg-panel-2'
                        : 'border-border bg-panel-2 hover:border-accent/50'
                    }`}
                  >
                    <div className="w-2.5 h-6 rounded-sm" style={{ background: apri }} />
                    <span className="font-mono font-bold">{g.away}</span>
                    <span className="text-muted">@</span>
                    <span className="font-mono font-bold">{g.home}</span>
                    <div className="w-2.5 h-6 rounded-sm" style={{ background: hpri }} />
                    <span className={`flex-1 text-right text-[10px] ${
                      g.state === 'LIVE' ? 'text-green-400'
                      : g.state === 'FINAL' || g.state === 'OFF' ? 'text-muted'
                      : 'text-amber-400'
                    }`}>
                      {g.state}
                    </span>
                  </button>
                );
              })}
              {games.length === 0 && !loading && (
                <p className="text-[10px] text-muted text-center py-2">No games today</p>
              )}
            </div>
          </Section>

          <Section title="Manual filters">
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
            <Field label="Poll interval">
              <div className="flex items-center gap-1">
                <div className="w-24"><Slider
                  value={src.poll_interval_sec}
                  min={2} max={30} step={1}
                  onChange={(v) => update((p) => {
                    if (p.source.kind === 'nhl') p.source.poll_interval_sec = Math.round(v);
                  })}
                /></div>
                <span className="text-[10px] text-muted w-10 text-right">{src.poll_interval_sec}s</span>
              </div>
            </Field>
          </Section>
        </>
      )}

      {!isNHL && src.kind === 'mock' && <MockEditor />}
    </div>
  );
}

/** Mock state editor: inputs for the obvious fields plus a quick-set bar
 *  ("Goal AWAY", "Goal HOME", "Penalty AWAY", "End period", etc.). */
function MockEditor() {
  const update = useProjectStore((s) => s.updateProject);
  const project = useProjectStore((s) => s.project);
  if (!project || project.source.kind !== 'mock') return null;
  const s = project.source.state;

  const set = (mut: (st: typeof s) => void) => update((p) => {
    if (p.source.kind === 'mock') mut(p.source.state);
  });

  return (
    <>
      <Section title="Quick actions">
        <div className="grid grid-cols-2 gap-1">
          <Button onClick={() => {
            set((st) => { st.away.score += 1; });
            // Also trigger the banner animation so we can preview it
            void api.triggerGoal(s.away.abbrev || 'WSH', 'away').catch(() => {});
          }}>
            <Plus className="w-3 h-3" /> Goal AWAY
          </Button>
          <Button onClick={() => {
            set((st) => { st.home.score += 1; });
            void api.triggerGoal(s.home.abbrev || 'CAR', 'home').catch(() => {});
          }}>
            <Plus className="w-3 h-3" /> Goal HOME
          </Button>
          <Button onClick={() => {
            void api.triggerGoal(s.away.abbrev || 'WSH', 'away').catch(() => {});
          }}>
            ▶ Anim AWAY
          </Button>
          <Button onClick={() => {
            void api.triggerGoal(s.home.abbrev || 'CAR', 'home').catch(() => {});
          }}>
            ▶ Anim HOME
          </Button>
          <Button onClick={() => set((st) => {
            st.away.penalty_remaining_sec = 120;
            st.away.active_penalty_count = (st.away.active_penalty_count || 0) + 1;
            st.away.pim = (st.away.pim || 0) + 2;
          })}>
            <Shield className="w-3 h-3" /> Pen AWAY (2:00)
          </Button>
          <Button onClick={() => set((st) => {
            st.home.penalty_remaining_sec = 120;
            st.home.active_penalty_count = (st.home.active_penalty_count || 0) + 1;
            st.home.pim = (st.home.pim || 0) + 2;
          })}>
            <Shield className="w-3 h-3" /> Pen HOME (2:00)
          </Button>
          <Button onClick={() => set((st) => {
            // End period: bump label, clock 0:00, set intermission
            const next = ({ '1ST': '2ND', '2ND': '3RD', '3RD': 'OT', OT: 'SO' } as Record<string,string>)[st.period_label];
            if (next) { st.period_label = next; }
            st.intermission = true;
            st.clock = '17:00';
          })}>
            <Pause className="w-3 h-3" /> End period
          </Button>
          <Button onClick={() => set((st) => {
            st.intermission = false;
            st.clock = '20:00';
          })}>
            <Play className="w-3 h-3" /> Resume
          </Button>
          <Button onClick={() => set((st) => {
            st.away.penalty_remaining_sec = 0;
            st.home.penalty_remaining_sec = 0;
            st.away.active_penalty_count = 0;
            st.home.active_penalty_count = 0;
          })}>
            <Minus className="w-3 h-3" /> Clear pens
          </Button>
          <Button onClick={() => set((st) => {
            st.period_label = 'FINAL';
            st.clock = '00:00';
            st.intermission = false;
          })}>
            FINAL
          </Button>
        </div>
      </Section>

      <Section title="Direct edit">
        <Field label="Period label">
          <Input className="w-20 text-right" value={s.period_label}
            onChange={(e) => set((st) => { st.period_label = e.target.value; })} />
        </Field>
        <Field label="Clock">
          <Input className="w-20 text-right font-mono" value={s.clock}
            onChange={(e) => set((st) => { st.clock = e.target.value; })} />
        </Field>
        <Field label="Intermission">
          <Switch checked={s.intermission} onChange={(b) => set((st) => { st.intermission = b; })} />
        </Field>
      </Section>

      <Section title="Away team">
        <TeamFields side="away" />
      </Section>
      <Section title="Home team">
        <TeamFields side="home" />
      </Section>
    </>
  );
}

function TeamFields({ side }: { side: 'away' | 'home' }) {
  const update = useProjectStore((s) => s.updateProject);
  const project = useProjectStore((s) => s.project);
  if (!project || project.source.kind !== 'mock') return null;
  const t = project.source.state[side];
  const set = (mut: (tt: typeof t) => void) => update((p) => {
    if (p.source.kind === 'mock') mut(p.source.state[side]);
  });

  return (
    <>
      <Field label="Abbrev">
        <Input className="w-16 text-right uppercase" maxLength={3} value={t.abbrev}
          onChange={(e) => set((tt) => { tt.abbrev = e.target.value.toUpperCase(); })} />
      </Field>
      <Field label="Score">
        <Input className="w-16 text-right" type="number" min={0} value={t.score}
          onChange={(e) => set((tt) => { tt.score = parseInt(e.target.value) || 0; })} />
      </Field>
      <Field label="Shots / Hits">
        <div className="flex gap-1">
          <Input className="w-12 text-right" type="number" min={0} value={t.shots}
            onChange={(e) => set((tt) => { tt.shots = parseInt(e.target.value) || 0; })} />
          <Input className="w-12 text-right" type="number" min={0} value={t.hits}
            onChange={(e) => set((tt) => { tt.hits = parseInt(e.target.value) || 0; })} />
        </div>
      </Field>
    </>
  );
}
