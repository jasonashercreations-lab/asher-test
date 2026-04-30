import { useEffect, useMemo, useRef, useState } from 'react';
import { useProjectStore } from '@/store/project';
import { api } from '@/api/client';
import { Button, Section, Field, Switch, Slider } from '@/components/ui/primitives';
import { TeamPickerModal } from '@/components/TeamPickerModal';
import type { GameSummary, BackendStatus } from '@/types/project';
import {
  RefreshCw, Radio, FlaskConical, Plus, Pause, Play,
  Shield, Star, ChevronLeft, ChevronRight, X, Clock, Calendar,
} from 'lucide-react';

/** Poll /api/status at the given interval and return the latest current_state.
 *  Used by MockEditor so it sees the engine's authoritative state in real-time
 *  instead of relying on the project file. */
function useLiveState(intervalMs = 500) {
  const [status, setStatus] = useState<BackendStatus | null>(null);
  const mountedRef = useRef(true);
  useEffect(() => {
    mountedRef.current = true;
    let cancelled = false;
    const tick = async () => {
      try {
        const s = await api.status();
        if (!cancelled && mountedRef.current) setStatus(s);
      } catch { /* ignore */ }
    };
    tick();
    const i = setInterval(tick, intervalMs);
    return () => {
      cancelled = true;
      mountedRef.current = false;
      clearInterval(i);
    };
  }, [intervalMs]);
  return status?.current_state ?? null;
}

// =============================================================================
// HELPERS
// =============================================================================

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

function toLocalISODate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function formatDayChip(dateStr: string): { weekday: string; date: string; isToday: boolean } {
  const d = new Date(dateStr + 'T12:00:00');
  const today = toLocalISODate(new Date());
  const weekday = d.toLocaleDateString(undefined, { weekday: 'short' });
  const date = d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  return { weekday, date, isToday: dateStr === today };
}

function formatStartTime(utc: string | null | undefined): string {
  if (!utc) return '';
  try {
    const d = new Date(utc);
    return d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
  } catch { return ''; }
}

function gameStateBadge(state: string): { label: string; color: string } {
  const s = (state || '').toUpperCase();
  if (s === 'LIVE') return { label: 'LIVE', color: 'text-red-400 font-bold' };
  if (s === 'CRIT') return { label: 'CRIT', color: 'text-red-400 font-bold' };
  if (s === 'FUT' || s === 'PRE') return { label: 'SCHED', color: 'text-amber-400' };
  if (s === 'FINAL' || s === 'OFF') return { label: 'FINAL', color: 'text-muted' };
  return { label: s || '—', color: 'text-muted' };
}

// =============================================================================
// MAIN PANEL
// =============================================================================

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

  // First-launch favorite-team prompt: only when project has NO favorite AND
  // no global localStorage value AND user hasn't explicitly cleared it.
  useEffect(() => {
    if (!project) return;
    const projectFav = project.favorite_team;
    const globalFav = getGlobalFavorite();
    const hasShown = (() => {
      try { return localStorage.getItem('nhlsb.favorite_prompt_shown') === '1'; }
      catch { return false; }
    })();
    // Trigger only when both are undefined AND we've never shown the prompt
    // (so users who chose "no favorite" don't get re-prompted)
    if (projectFav === undefined && !globalFav && !hasShown) {
      setFirstLaunchModalOpen(true);
    } else if (!projectFav && globalFav && projectFav !== '') {
      // Migrate global favorite into the project (only if not explicitly cleared)
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

  const favorite = project?.favorite_team ?? getGlobalFavorite() ?? '';

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

  // ---- Click handler for picking a game (FIX bug 9) ----
  // If user is on Mock when they click an NHL game, automatically switch
  // source to NHL and select that game.
  const pickGame = (gameId: number | null) => {
    update((p) => {
      // Switch to NHL if not already
      if (p.source.kind !== 'nhl') {
        p.source = {
          kind: 'nhl',
          team_filter: gameId ? null : (favorite || null),
          game_id: gameId,
          poll_interval_sec: 5,
          auto_rotate: false,
          rotate_interval_sec: 0,
        };
      } else {
        p.source.game_id = gameId;
        p.source.team_filter = gameId ? null : (favorite || null);
      }
    });
  };

  return (
    <div>
      <Section title="Source">
        <div className="grid grid-cols-2 gap-1">
          <Button
            variant={isNHL ? 'accent' : 'default'}
            onClick={() => update((p) => {
              p.source = {
                kind: 'nhl', team_filter: favorite || null, game_id: null,
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

      {/* Favorite team — visible regardless of source. (FIX bug 7: clear button) */}
      <Section title="Favorite team">
        <div className="flex items-center gap-1">
          <button
            onClick={() => setFavoriteModalOpen(true)}
            className="flex items-center gap-2 px-2 py-1.5 rounded border border-border bg-panel-2 hover:border-accent/60 transition-colors flex-1"
          >
            <Star className={`w-3 h-3 shrink-0 ${favorite ? 'text-amber-400 fill-amber-400' : 'text-muted'}`} />
            {favorite ? (
              <>
                <div className="w-3 h-4 rounded-sm shrink-0" style={{ background: teams[favorite]?.primary || '#888' }} />
                <span className="font-mono font-bold text-xs">{favorite}</span>
                <span className="text-[10px] text-muted ml-auto">change</span>
              </>
            ) : (
              <span className="text-xs text-muted">No favorite — tap to set</span>
            )}
          </button>
          {favorite && (
            <button
              onClick={() => {
                setGlobalFavorite('');
                update((p) => { p.favorite_team = ''; });
              }}
              className="w-7 h-7 rounded border border-border bg-panel-2 hover:border-red-400/60 flex items-center justify-center text-muted hover:text-red-400"
              title="Clear favorite"
              aria-label="Clear favorite team"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </div>
      </Section>

      {isNHL && src.kind === 'nhl' && (
        <NHLSchedule
          src={src}
          dayKeys={dayKeys}
          selectedDate={selectedDate}
          setSelectedDate={setSelectedDate}
          gamesByDate={gamesByDate}
          selectedGames={selectedGames}
          favorite={favorite}
          teams={teams}
          loading={loading}
          refresh={refresh}
          pickGame={pickGame}
        />
      )}

      {!isNHL && src.kind === 'mock' && <MockEditor teams={teams} />}

      <TeamPickerModal
        open={favoriteModalOpen}
        current={favorite}
        title="Pick your favorite team"
        subtitle="This team's games will be pinned to the top of the schedule."
        allowClear={true}
        onSelect={(abbrev) => {
          setGlobalFavorite(abbrev);
          update((p) => { p.favorite_team = abbrev; });
          try { localStorage.setItem('nhlsb.favorite_prompt_shown', '1'); } catch {}
        }}
        onClose={() => setFavoriteModalOpen(false)}
      />
      <TeamPickerModal
        open={firstLaunchModalOpen}
        current=""
        title="Welcome — pick your favorite team"
        subtitle="We'll pin their games to the top of your schedule. You can change this any time."
        allowClear={true}
        onSelect={(abbrev) => {
          setGlobalFavorite(abbrev);
          update((p) => { p.favorite_team = abbrev; });
          try { localStorage.setItem('nhlsb.favorite_prompt_shown', '1'); } catch {}
          setFirstLaunchModalOpen(false);
        }}
        onClose={() => {
          try { localStorage.setItem('nhlsb.favorite_prompt_shown', '1'); } catch {}
          setFirstLaunchModalOpen(false);
        }}
      />
    </div>
  );
}

// =============================================================================
// NHL SCHEDULE — cleaner layout (FIX bug 8)
// =============================================================================

function NHLSchedule({
  src, dayKeys, selectedDate, setSelectedDate, gamesByDate,
  selectedGames, favorite, teams, loading, refresh, pickGame,
}: {
  src: { kind: 'nhl'; game_id?: number | null; team_filter?: string | null;
         poll_interval_sec: number; auto_rotate: boolean; rotate_interval_sec: number; };
  dayKeys: string[];
  selectedDate: string;
  setSelectedDate: (d: string) => void;
  gamesByDate: Record<string, GameSummary[]>;
  selectedGames: GameSummary[];
  favorite: string;
  teams: Record<string, { primary: string; secondary: string }>;
  loading: boolean;
  refresh: () => void;
  pickGame: (id: number | null) => void;
}) {
  const update = useProjectStore((s) => s.updateProject);

  return (
    <>
      <Section
        title="Schedule"
        action={
          <button
            onClick={refresh}
            disabled={loading}
            className="text-xs flex items-center gap-1 text-accent hover:underline disabled:opacity-50"
            title="Refresh schedule"
          >
            <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
          </button>
        }
      >
        {/* Day picker — horizontal chip strip */}
        <div className="flex gap-1 overflow-x-auto pb-1 mb-3 -mx-1 px-1">
          {dayKeys.map((d) => {
            const { weekday, date, isToday } = formatDayChip(d);
            const isSelected = d === selectedDate;
            const count = (gamesByDate[d] || []).length;
            return (
              <button
                key={d}
                onClick={() => setSelectedDate(d)}
                className={`shrink-0 px-2.5 py-1.5 rounded text-center min-w-[3.4rem] border transition-colors ${
                  isSelected
                    ? 'border-accent bg-panel-2 text-fg'
                    : 'border-border bg-panel-2 text-muted hover:border-accent/50'
                }`}
              >
                <div className={`text-[9px] uppercase font-bold tracking-wide ${
                  isToday ? 'text-accent' : ''
                }`}>
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

        {/* Auto-pick option */}
        <button
          onClick={() => pickGame(null)}
          className={`w-full px-2 py-1.5 rounded text-xs flex items-center gap-2 border mb-1 ${
            !src.game_id
              ? 'border-accent bg-panel-2'
              : 'border-border bg-panel-2 hover:border-accent/50'
          }`}
        >
          <Radio className="w-3 h-3 text-muted shrink-0" />
          <span className="flex-1 text-left">
            {favorite
              ? <>Auto-pick <span className="font-mono font-bold">{favorite}</span> (or first live)</>
              : <>Auto-pick (first live game)</>}
          </span>
        </button>

        {/* Game list — cleaner layout */}
        <div className="space-y-1">
          {selectedGames.map((g) => {
            const apri = teams[g.away]?.primary || '#888';
            const hpri = teams[g.home]?.primary || '#888';
            const isActive = src.game_id === g.id;
            const isFavGame = !!favorite && (g.away === favorite || g.home === favorite);
            const time = formatStartTime(g.start_time_utc);
            const badge = gameStateBadge(g.state || '');
            return (
              <button
                key={g.id}
                onClick={() => pickGame(g.id)}
                className={`w-full px-2 py-2 rounded text-xs flex items-center gap-2 border transition-colors text-left ${
                  isActive
                    ? 'border-accent bg-panel-2'
                    : 'border-border bg-panel-2 hover:border-accent/50'
                } ${isFavGame ? 'ring-1 ring-amber-400/30' : ''}`}
              >
                {isFavGame && <Star className="w-3 h-3 text-amber-400 fill-amber-400 shrink-0" />}
                <div className="flex items-center gap-1.5 flex-1 min-w-0">
                  <div className="w-1 h-7 rounded-sm shrink-0" style={{ background: apri }} />
                  <span className="font-mono font-bold w-8 text-center">{g.away}</span>
                  <span className="text-muted text-[10px]">@</span>
                  <span className="font-mono font-bold w-8 text-center">{g.home}</span>
                  <div className="w-1 h-7 rounded-sm shrink-0" style={{ background: hpri }} />
                </div>
                <div className="flex flex-col items-end gap-0.5 shrink-0">
                  <span className={`text-[10px] uppercase font-mono ${badge.color}`}>
                    {badge.label}
                  </span>
                  {time && (
                    <span className="text-[9px] text-muted flex items-center gap-0.5">
                      <Clock className="w-2.5 h-2.5" />
                      {time}
                    </span>
                  )}
                </div>
              </button>
            );
          })}
          {selectedGames.length === 0 && !loading && (
            <p className="text-[10px] text-muted text-center py-4 flex items-center justify-center gap-1">
              <Calendar className="w-3 h-3" />
              No games scheduled for this day
            </p>
          )}
        </div>
      </Section>

      <Section title="Auto-rotate">
        <Field label="Cycle through live games">
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
  );
}

// =============================================================================
// MOCK EDITOR
// (FIX bug 1, 3, 4, 5, 6 — direct API calls instead of project mutation)
// =============================================================================

const PERIOD_ORDER = ['1ST', '2ND', '3RD', 'OT', 'SO', 'FINAL'] as const;

function MockEditor({
  teams,
}: {
  teams: Record<string, { primary: string; secondary: string }>;
}) {
  const project = useProjectStore((s) => s.project);
  // Live state from backend polling — this is what the engine actually shows
  const liveState = useLiveState(500);
  const [busy, setBusy] = useState(false);

  // Mock team picker modal
  const [teamModal, setTeamModal] = useState<'away' | 'home' | null>(null);

  if (!project || project.source.kind !== 'mock') return null;

  // Use live engine state if available (snappier, real-time), else fallback
  // to project state. Engine state updates via WebSocket on every backend
  // mutation, so the user sees their button clicks reflected with no lag.
  const s = liveState || project.source.state;
  const paused = project.source.paused !== false;
  const intermissionSec = project.mock_intermission_sec ?? 1020;

  // Helper: call API directly, no project mutation. Engine broadcasts the
  // result via WebSocket which updates liveState. (Fixes laggy buttons.)
  const callApi = async (fn: () => Promise<unknown>) => {
    if (busy) return;
    setBusy(true);
    try { await fn(); } catch (e) { console.error('mock action failed', e); }
    finally { setBusy(false); }
  };

  const togglePause = () => {
    const newPaused = !paused;
    // We DO update the project for paused (it's a project field, not transient)
    useProjectStore.getState().updateProject((p) => {
      if (p.source.kind === 'mock') p.source.paused = newPaused;
    });
    callApi(() => api.mockSetPaused(newPaused));
  };

  const fireGoal = (side: 'away' | 'home') =>
    callApi(() => api.mockGoal(side));

  const firePenalty = (side: 'away' | 'home') =>
    callApi(() => api.mockPenalty(side, 120));

  const clearPens = () =>
    callApi(() => api.mockClearPenalties());

  const endPeriod = () =>
    callApi(() => api.mockEndPeriod());

  const stepPeriod = (delta: 1 | -1) => {
    const cur = (s.period_label || '').toUpperCase();
    const idx = PERIOD_ORDER.indexOf(cur as typeof PERIOD_ORDER[number]);
    if (idx < 0) return;
    const nextIdx = Math.max(0, Math.min(PERIOD_ORDER.length - 1, idx + delta));
    const next = PERIOD_ORDER[nextIdx];
    if (next === cur) return;
    callApi(() => api.mockSetPeriod(next));
  };

  const setTeam = (side: 'away' | 'home', abbrev: string) =>
    callApi(() => api.mockSetTeam(side, abbrev));

  const setScore = (side: 'away' | 'home', score: number) =>
    callApi(() => api.mockSetScore(side, score));

  const setStat = (side: 'away' | 'home', field: string, value: number) =>
    callApi(() => api.mockSetStat(side, field, value));

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
            ? 'Paused — click Play to start the clock counting down.'
            : s.intermission
              ? 'Intermission running — next period will auto-start at 0:00.'
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
                onChange={(v) => useProjectStore.getState().updateProject((p) => {
                  p.mock_intermission_sec = Math.round(v);
                })}
              />
            </div>
            <span className="text-[10px] text-muted font-mono w-14 text-right">
              {Math.floor(intermissionSec / 60)}:{String(intermissionSec % 60).padStart(2, '0')}
            </span>
          </div>
        </Field>
        <Button onClick={endPeriod} className="mt-1">
          End period now → 0:00
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
          <Button onClick={() => callApi(() => api.triggerGoal(s.away.abbrev || 'WSH', 'away'))}>
            ▶ Replay anim AWAY
          </Button>
          <Button onClick={() => callApi(() => api.triggerGoal(s.home.abbrev || 'CAR', 'home'))}>
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

      {/* Mock teams use the same modal picker (FIX bug 5) */}
      <Section title="Away team">
        <TeamRow
          side="away"
          team={s.away}
          teamColor={teams[s.away.abbrev]?.primary}
          onPickTeam={() => setTeamModal('away')}
          onSetScore={(v) => setScore('away', v)}
          onSetStat={(f, v) => setStat('away', f, v)}
        />
      </Section>
      <Section title="Home team">
        <TeamRow
          side="home"
          team={s.home}
          teamColor={teams[s.home.abbrev]?.primary}
          onPickTeam={() => setTeamModal('home')}
          onSetScore={(v) => setScore('home', v)}
          onSetStat={(f, v) => setStat('home', f, v)}
        />
      </Section>

      <TeamPickerModal
        open={teamModal !== null}
        current={teamModal === 'away' ? s.away.abbrev : (teamModal === 'home' ? s.home.abbrev : '')}
        title={`Pick ${teamModal === 'away' ? 'AWAY' : 'HOME'} team`}
        allowClear={false}
        onSelect={(abbrev) => {
          if (teamModal && abbrev) setTeam(teamModal, abbrev);
        }}
        onClose={() => setTeamModal(null)}
      />
    </>
  );
}

function TeamRow({
  side, team, teamColor, onPickTeam, onSetScore, onSetStat,
}: {
  side: 'away' | 'home';
  team: { abbrev: string; score: number; shots: number; hits: number };
  teamColor?: string;
  onPickTeam: () => void;
  onSetScore: (v: number) => void;
  onSetStat: (field: string, v: number) => void;
}) {
  return (
    <>
      <Field label="Team">
        <button
          onClick={onPickTeam}
          className="flex items-center gap-2 px-2 py-1 rounded border border-border bg-panel-2 hover:border-accent/60 transition-colors"
        >
          <div className="w-3 h-4 rounded-sm" style={{ background: teamColor || '#888' }} />
          <span className="font-mono font-bold text-xs">{team.abbrev}</span>
          <span className="text-[10px] text-muted">change</span>
        </button>
      </Field>
      <Field label="Score">
        <NumberStepper value={team.score} onChange={onSetScore} />
      </Field>
      <Field label="Shots">
        <NumberStepper value={team.shots} onChange={(v) => onSetStat('shots', v)} />
      </Field>
      <Field label="Hits">
        <NumberStepper value={team.hits} onChange={(v) => onSetStat('hits', v)} />
      </Field>
    </>
  );
}

/** +/- stepper that fires API on each click — no project mutation, no lag. */
function NumberStepper({
  value, onChange, min = 0, max = 999,
}: {
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
}) {
  return (
    <div className="flex items-center gap-1">
      <button
        onClick={() => onChange(Math.max(min, value - 1))}
        disabled={value <= min}
        className="w-6 h-6 rounded border border-border bg-panel-2 hover:border-accent/60 disabled:opacity-30 flex items-center justify-center"
      >
        <ChevronLeft className="w-3 h-3" />
      </button>
      <span className="font-mono w-8 text-center text-xs tabular-nums">{value}</span>
      <button
        onClick={() => onChange(Math.min(max, value + 1))}
        disabled={value >= max}
        className="w-6 h-6 rounded border border-border bg-panel-2 hover:border-accent/60 disabled:opacity-30 flex items-center justify-center"
      >
        <ChevronRight className="w-3 h-3" />
      </button>
    </div>
  );
}
