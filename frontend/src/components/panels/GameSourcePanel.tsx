import { useEffect, useMemo, useState } from 'react';
import { useProjectStore } from '@/store/project';
import { api } from '@/api/client';
import { Button, Input, Section, Field, Switch, Slider } from '@/components/ui/primitives';
import { FavoriteTeamModal } from '@/components/FavoriteTeamModal';
import type { GameSummary } from '@/types/project';
import {
  RefreshCw, Radio, FlaskConical, CircleDot, Plus, Pause, Play,
  Shield, Star, ChevronLeft, ChevronRight,
} from 'lucide-react';

const FAVORITE_TEAM_LS_KEY = 'nhlsb.favorite_team';

function getGlobalFavorite(): string {
  try { return localStorage.getItem(FAVORITE_TEAM_LS_KEY) || ''; }
  catch { return ''; }
}
function setGlobalFavorite(abbr: string) {
  try {
    if (abbr) localStorage.setItem(FAVORITE_TEAM_LS_KEY, abbr);
    else localStorage.removeItem(FAVORITE_TEAM_LS_KEY);
  } catch { /* ignore quota errors */ }
}

/** YYYY-MM-DD in user's local timezone. */
function toLocalISODate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

/** Short weekday + month/day for the day picker chip. */
function formatDayChip(dateStr: string): { weekday: string; date: string; isToday: boolean } {
  const d = new Date(dateStr + 'T12:00:00');
  const today = toLocalISODate(new Date());
  const weekday = d.toLocaleDateString(undefined, { weekday: 'short' });
  const date = d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  return { weekday, date, isToday: dateStr === today };
}

/** Render UTC start time as "h:mm AM/PM" in user's local timezone. */
function formatStartTime(utc: string | null | undefined): string {
  if (!utc) return '';
  try {
    const d = new Date(utc);
    return d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
  } catch { return ''; }
}

export function GameSourcePanel() {
  const project = useProjectStore((s) => s.project);
  const update = useProjectStore((s) => s.updateProject);

  const today = toLocalISODate(new Date());
  const [selectedDate, setSelectedDate] = useState(today);
  const [gamesByDate, setGamesByDate] = useState<Record<string, GameSummary[]>>({});
  const [teams, setTeams] = useState<Record<string, { primary: string; secondary: string }>>({});
  const [loading, setLoading] = useState(false);

  const [favoriteModalOpen, setFavoriteModalOpen] = useState(false);
  const [firstLaunchModalOpen, setFirstLaunchModalOpen] = useState(false);

  const refresh = async () => {
    setLoading(true);
    try {
      const data = await api.gamesRange(today, 7);
      setGamesByDate(data);
    } catch {
      setGamesByDate({});
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
    api.teams().then(setTeams).catch(() => {});
    const i = setInterval(refresh, 60_000);
    return () => clearInterval(i);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // First-launch favorite-team prompt: triggered when project has no favorite
  // AND no global localStorage value.
  useEffect(() => {
    if (!project) return;
    const projectFav = project.favorite_team || '';
    const globalFav = getGlobalFavorite();
    if (!projectFav && !globalFav) {
      setFirstLaunchModalOpen(true);
    } else if (!projectFav && globalFav) {
      // Migrate global favorite into the project
      update((p) => { p.favorite_team = globalFav; });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project?.name]);

  const dayKeys = useMemo(() => {
    const out: string[] = [];
    const start = new Date(today + 'T12:00:00');
    for (let i = 0; i < 7; i++) {
      const d = new Date(start); d.setDate(start.getDate() + i);
      out.push(toLocalISODate(d));
    }
    return out;
  }, [today]);

  const favorite = project?.favorite_team || getGlobalFavorite() || '';

  const selectedGames = useMemo(() => {
    const list = gamesByDate[selectedDate] || [];
    if (!favorite) return list;
    return [...list].sort((a, b) => {
      const aFav = a.away === favorite || a.home === favorite;
      const bFav = b.away === favorite || b.home === favorite;
      if (aFav === bFav) return 0;
      return aFav ? -1 : 1;
    });
  }, [gamesByDate, selectedDate, favorite]);

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
              p.source = {
                kind: 'nhl', team_filter: null, game_id: null,
                poll_interval_sec: 5, auto_rotate: false, rotate_interval_sec: 0,
              };
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
                  paused: true,
                  state: {
                    away: { abbrev: 'WSH', score: 0, shots: 15, hits: 33, blocks: 14, pim: 4, takeaways: 2, giveaways: 1, faceoff_win_pct: 52, penalty_remaining_sec: 0, active_penalty_count: 0 },
                    home: { abbrev: 'CAR', score: 2, shots: 25, hits: 28, blocks: 8, pim: 8, takeaways: 3, giveaways: 7, faceoff_win_pct: 48, penalty_remaining_sec: 0, active_penalty_count: 0 },
                    period_label: '1ST',
                    clock: '20:00',
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

      {isNHL && (
        <Section title="Favorite team">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setFavoriteModalOpen(true)}
              className="flex items-center gap-2 px-2 py-1.5 rounded border border-border bg-panel-2 hover:border-accent/60 transition-colors flex-1"
            >
              <Star className={`w-3 h-3 ${favorite ? 'text-amber-400 fill-amber-400' : 'text-muted'}`} />
              {favorite ? (
                <>
                  <div className="w-3 h-4 rounded-sm" style={{ background: teams[favorite]?.primary || '#888' }} />
                  <span className="font-mono font-bold text-xs">{favorite}</span>
                  <span className="text-[10px] text-muted ml-auto">change</span>
                </>
              ) : (
                <span className="text-xs text-muted">Tap to choose</span>
              )}
            </button>
          </div>
          {favorite && (
            <p className="text-[10px] text-muted mt-1">
              {favorite}'s games are pinned to the top of the list.
            </p>
          )}
        </Section>
      )}

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
          </Section>

          <Section
            title="Schedule"
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
            <div className="flex gap-1 overflow-x-auto pb-1 mb-2 -mx-1 px-1">
              {dayKeys.map((d) => {
                const { weekday, date, isToday } = formatDayChip(d);
                const isSelected = d === selectedDate;
                const count = (gamesByDate[d] || []).length;
                return (
                  <button
                    key={d}
                    onClick={() => setSelectedDate(d)}
                    className={`shrink-0 px-2 py-1.5 rounded text-center min-w-[3.2rem] border transition-colors ${
                      isSelected
                        ? 'border-accent bg-panel-2 text-fg'
                        : 'border-border bg-panel-2 text-muted hover:border-accent/50'
                    }`}
                  >
                    <div className="text-[9px] uppercase font-bold tracking-wide">
                      {isToday ? 'TODAY' : weekday}
                    </div>
                    <div className="text-[10px] font-mono">{date}</div>
                    <div className="text-[9px] text-muted mt-0.5">
                      {count > 0 ? `${count} game${count > 1 ? 's' : ''}` : '—'}
                    </div>
                  </button>
                );
              })}
            </div>

            <div className="space-y-1">
              <button
                onClick={() => update((p) => {
                  if (p.source.kind === 'nhl') {
                    p.source.game_id = null;
                    p.source.team_filter = favorite || null;
                  }
                })}
                className={`w-full px-2 py-1.5 rounded text-xs text-left flex items-center gap-2 border ${
                  !src.game_id
                    ? 'border-accent bg-panel-2'
                    : 'border-border bg-panel-2 hover:border-accent/50'
                }`}
              >
                <CircleDot className="w-3 h-3 text-muted" />
                <span className="flex-1">
                  {favorite
                    ? `Auto-pick (prefer ${favorite}, fallback to first live)`
                    : 'Auto-pick (first live game)'}
                </span>
              </button>
              {selectedGames.map((g) => {
                const apri = teams[g.away]?.primary || '#888';
                const hpri = teams[g.home]?.primary || '#888';
                const isActive = src.game_id === g.id;
                const isFavGame = !!favorite && (g.away === favorite || g.home === favorite);
                const time = formatStartTime(g.start_time_utc);
                return (
                  <button
                    key={g.id}
                    onClick={() => update((p) => {
                      if (p.source.kind === 'nhl') {
                        p.source.game_id = g.id;
                        p.source.team_filter = null;
                      }
                    })}
                    className={`w-full px-2 py-1.5 rounded text-xs flex items-center gap-2 border transition-colors ${
                      isActive
                        ? 'border-accent bg-panel-2'
                        : 'border-border bg-panel-2 hover:border-accent/50'
                    }`}
                  >
                    {isFavGame && <Star className="w-3 h-3 text-amber-400 fill-amber-400 shrink-0" />}
                    <div className="w-2.5 h-6 rounded-sm shrink-0" style={{ background: apri }} />
                    <span className="font-mono font-bold">{g.away}</span>
                    <span className="text-muted">@</span>
                    <span className="font-mono font-bold">{g.home}</span>
                    <div className="w-2.5 h-6 rounded-sm shrink-0" style={{ background: hpri }} />
                    {time && (
                      <span className="text-[10px] text-muted ml-1">{time}</span>
                    )}
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
              {selectedGames.length === 0 && !loading && (
                <p className="text-[10px] text-muted text-center py-3">
                  No games scheduled for this day
                </p>
              )}
            </div>
          </Section>

          <Section title="Polling">
            <Field label="Refresh interval">
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

      <FavoriteTeamModal
        open={favoriteModalOpen}
        current={favorite}
        onSelect={(abbrev) => {
          setGlobalFavorite(abbrev);
          update((p) => { p.favorite_team = abbrev; });
        }}
        onClose={() => setFavoriteModalOpen(false)}
      />
      <FavoriteTeamModal
        open={firstLaunchModalOpen}
        current=""
        onSelect={(abbrev) => {
          setGlobalFavorite(abbrev);
          update((p) => { p.favorite_team = abbrev; });
          setFirstLaunchModalOpen(false);
        }}
        onClose={() => setFirstLaunchModalOpen(false)}
      />
    </div>
  );
}

const PERIOD_ORDER = ['1ST', '2ND', '3RD', 'OT', 'SO', 'FINAL'] as const;

function MockEditor() {
  const project = useProjectStore((s) => s.project);
  const update = useProjectStore((s) => s.updateProject);
  if (!project || project.source.kind !== 'mock') return null;
  const s = project.source.state;
  const paused = project.source.paused !== false;
  const intermissionSec = project.mock_intermission_sec ?? 1020;

  const local = (mut: (st: typeof s) => void) =>
    update((p) => { if (p.source.kind === 'mock') mut(p.source.state); });

  const togglePause = async () => {
    const newPaused = !paused;
    update((p) => { if (p.source.kind === 'mock') p.source.paused = newPaused; });
    try { await api.mockSetPaused(newPaused); } catch { /* WS reconciles */ }
  };

  const fireGoal = async (side: 'away' | 'home') => {
    local((st) => {
      if (side === 'away') st.away.score += 1;
      else st.home.score += 1;
    });
    try { await api.mockGoal(side); } catch { /* ignore */ }
  };

  const firePenalty = async (side: 'away' | 'home') => {
    local((st) => {
      const t = side === 'away' ? st.away : st.home;
      t.penalty_remaining_sec = 120;
      t.active_penalty_count = (t.active_penalty_count || 0) + 1;
    });
    try { await api.mockPenalty(side, 120); } catch { /* ignore */ }
  };

  const clearPens = async () => {
    local((st) => {
      st.away.penalty_remaining_sec = 0;
      st.home.penalty_remaining_sec = 0;
      st.away.active_penalty_count = 0;
      st.home.active_penalty_count = 0;
    });
    try { await api.mockClearPenalties(); } catch { /* ignore */ }
  };

  const endPeriod = async () => {
    local((st) => { st.clock = '00:00'; });
    try { await api.mockEndPeriod(); } catch { /* ignore */ }
  };

  const stepPeriod = async (delta: 1 | -1) => {
    const cur = (s.period_label || '').toUpperCase();
    const idx = PERIOD_ORDER.indexOf(cur as typeof PERIOD_ORDER[number]);
    if (idx < 0) return;
    const nextIdx = Math.max(0, Math.min(PERIOD_ORDER.length - 1, idx + delta));
    const next = PERIOD_ORDER[nextIdx];
    if (next === cur) return;
    local((st) => { st.period_label = next; st.intermission = false; });
    try { await api.mockSetPeriod(next); } catch { /* ignore */ }
  };

  return (
    <>
      <Section title="Game clock">
        <div className="flex items-center gap-2">
          <Button onClick={togglePause} variant={paused ? 'accent' : 'default'}>
            {paused ? <><Play className="w-3 h-3" /> Play</> : <><Pause className="w-3 h-3" /> Pause</>}
          </Button>
          <div className="flex-1 text-right font-mono text-2xl tabular-nums">
            {s.clock}
          </div>
        </div>
        <p className="text-[10px] text-muted mt-1">
          {paused
            ? 'Clock paused — click Play to start counting down.'
            : s.intermission
              ? 'Intermission — clock will auto-start the next period at 0:00.'
              : 'Clock running. At 0:00 the period auto-ends and intermission begins.'}
        </p>
      </Section>

      <Section title="Period">
        <Field label="Current">
          <div className="flex items-center gap-1">
            <button
              onClick={() => stepPeriod(-1)}
              disabled={(s.period_label || '').toUpperCase() === '1ST'}
              className="w-7 h-7 rounded border border-border bg-panel-2 hover:border-accent/60 disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center"
              aria-label="Previous period"
            >
              <ChevronLeft className="w-3 h-3" />
            </button>
            <div className="font-mono font-bold w-12 text-center text-xs">
              {s.period_label}
            </div>
            <button
              onClick={() => stepPeriod(1)}
              disabled={(s.period_label || '').toUpperCase() === 'FINAL'}
              className="w-7 h-7 rounded border border-border bg-panel-2 hover:border-accent/60 disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center"
              aria-label="Next period"
            >
              <ChevronRight className="w-3 h-3" />
            </button>
          </div>
        </Field>
        <Field label="Intermission length">
          <div className="flex items-center gap-1">
            <div className="w-24">
              <Slider
                value={intermissionSec}
                min={30} max={1200} step={30}
                onChange={(v) => update((p) => { p.mock_intermission_sec = Math.round(v); })}
              />
            </div>
            <span className="text-[10px] text-muted font-mono w-14 text-right">
              {Math.floor(intermissionSec / 60)}:{String(intermissionSec % 60).padStart(2, '0')}
            </span>
          </div>
        </Field>
        <Button onClick={endPeriod} className="mt-1">
          End period now (jump to 0:00)
        </Button>
      </Section>

      <Section title="Goals & penalties">
        <div className="grid grid-cols-2 gap-1">
          <Button onClick={() => fireGoal('away')}>
            <Plus className="w-3 h-3" /> Goal AWAY
          </Button>
          <Button onClick={() => fireGoal('home')}>
            <Plus className="w-3 h-3" /> Goal HOME
          </Button>
          <Button onClick={() => api.triggerGoal(s.away.abbrev || 'WSH', 'away').catch(() => {})}>
            ▶ Replay anim AWAY
          </Button>
          <Button onClick={() => api.triggerGoal(s.home.abbrev || 'CAR', 'home').catch(() => {})}>
            ▶ Replay anim HOME
          </Button>
          <Button onClick={() => firePenalty('away')}>
            <Shield className="w-3 h-3" /> Pen AWAY 2:00
          </Button>
          <Button onClick={() => firePenalty('home')}>
            <Shield className="w-3 h-3" /> Pen HOME 2:00
          </Button>
          <Button onClick={clearPens}>Clear penalties</Button>
        </div>
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
  const project = useProjectStore((s) => s.project);
  const update = useProjectStore((s) => s.updateProject);
  if (!project || project.source.kind !== 'mock') return null;
  const t = project.source.state[side];

  const setLocal = (mut: (tt: typeof t) => void) =>
    update((p) => { if (p.source.kind === 'mock') mut(p.source.state[side]); });

  const setAbbrev = async (val: string) => {
    const v = val.toUpperCase().slice(0, 3);
    setLocal((tt) => { tt.abbrev = v; });
    try { await api.mockSetTeam(side, v); } catch { /* ignore */ }
  };
  const setScore = async (val: number) => {
    setLocal((tt) => { tt.score = Math.max(0, val); });
    try { await api.mockSetScore(side, Math.max(0, val)); } catch { /* ignore */ }
  };
  const setStat = async (field: 'shots' | 'hits', val: number) => {
    setLocal((tt) => { (tt as any)[field] = Math.max(0, val); });
    try { await api.mockSetStat(side, field, Math.max(0, val)); } catch { /* ignore */ }
  };

  return (
    <>
      <Field label="Abbrev">
        <Input className="w-16 text-right uppercase" maxLength={3}
          value={t.abbrev}
          onChange={(e) => setAbbrev(e.target.value)} />
      </Field>
      <Field label="Score">
        <Input className="w-16 text-right" type="number" min={0}
          value={t.score}
          onChange={(e) => setScore(parseInt(e.target.value) || 0)} />
      </Field>
      <Field label="Shots / Hits">
        <div className="flex gap-1">
          <Input className="w-12 text-right" type="number" min={0}
            value={t.shots}
            onChange={(e) => setStat('shots', parseInt(e.target.value) || 0)} />
          <Input className="w-12 text-right" type="number" min={0}
            value={t.hits}
            onChange={(e) => setStat('hits', parseInt(e.target.value) || 0)} />
        </div>
      </Field>
    </>
  );
}
