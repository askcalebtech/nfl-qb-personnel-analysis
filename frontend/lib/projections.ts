import type { CompletedGame, ProjectionGame, ProjectionTeam } from '@/types'

export type Scope =
  | { kind: 'all' }
  | { kind: 'conference'; value: string }
  | { kind: 'division'; value: string }
  | { kind: 'team'; value: string }

export function parseScope(param: string | null, teams: ProjectionTeam[]): Scope {
  if (!param) return { kind: 'all' }
  if (teams.some((t) => t.conference === param)) return { kind: 'conference', value: param }
  if (teams.some((t) => t.division === param)) return { kind: 'division', value: param }
  if (teams.some((t) => t.team === param)) return { kind: 'team', value: param }
  return { kind: 'all' }
}

export function scopeToParam(s: Scope): string | null {
  return s.kind === 'all' ? null : s.value
}

function inScope(t: ProjectionTeam, s: Scope): boolean {
  switch (s.kind) {
    case 'all': return true
    case 'conference': return t.conference === s.value
    case 'division': return t.division === s.value
    case 'team': return t.team === s.value
  }
}

export function teamsInScope(teams: ProjectionTeam[], s: Scope): ProjectionTeam[] {
  return teams.filter((t) => inScope(t, s))
}

export function gamesInScope<G extends ProjectionGame>(games: G[], teams: ProjectionTeam[], s: Scope): G[] {
  if (s.kind === 'all') return games
  const codes = new Set(teamsInScope(teams, s).map((t) => t.team))
  return games.filter((g) => codes.has(g.home) || codes.has(g.away))
}

/** Earliest week that still has unplayed games (the data holds only unplayed games). */
export function defaultWeek(games: ProjectionGame[]): number | null {
  return games.length ? Math.min(...games.map((g) => g.week)) : null
}

/** True when gameday (YYYY-MM-DD) is before now's local calendar date. Missing or malformed gameday is false. */
export function isPastGameday(gameday: string | null | undefined, now: Date): boolean {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(gameday ?? '')
  if (!m) return false
  const day = Number(m[1]) * 10000 + Number(m[2]) * 100 + Number(m[3])
  const today = now.getFullYear() * 10000 + (now.getMonth() + 1) * 100 + now.getDate()
  return day < today
}

const STALE_DAYS = 8

export function isStale(generatedAt: string, now: Date, gamesRemaining: number): boolean {
  if (gamesRemaining <= 0) return false
  const generated = new Date(generatedAt).getTime()
  if (Number.isNaN(generated)) return true // never present unknown-age numbers as fresh
  const ageDays = (now.getTime() - generated) / 86_400_000
  return ageDays > STALE_DAYS
}

export interface RatingRow {
  team: ProjectionTeam
  rank: number
  off: number
  def: number
  total: number
}

/** Rank all teams by off + def for the view, highest first. Filter afterwards to keep league rank. */
export function rankRatings(teams: ProjectionTeam[], view: 'raw' | 'adjusted'): RatingRow[] {
  return teams
    .map((team) => {
      const off = (view === 'raw' ? team.off : team.adj_off) ?? 0
      const def = (view === 'raw' ? team.def : team.adj_def) ?? 0
      return { team, off, def, total: off + def }
    })
    .sort((a, b) => b.total - a.total)
    .map((r, i) => ({ ...r, rank: i + 1 }))
}

/** Model picked the winner: true/false, or null for a tie, a missing result or a 50-50 pick. */
export function modelCorrect(g: CompletedGame): boolean | null {
  const r = g.final.result
  if (r === null || r === 0 || g.p_home === 0.5) return null
  return r > 0 === g.p_home > 0.5
}

/** Closing market picked the winner, same rules; null when there is no closing line. */
export function marketCorrect(g: CompletedGame): boolean | null {
  const r = g.final.result
  const m = g.final.close_mkt_home
  if (r === null || r === 0 || m === null || m === 0.5) return null
  return r > 0 === m > 0.5
}

/** Absolute points between projected and actual home margin. */
export function marginMiss(g: CompletedGame): number | null {
  return g.final.result === null ? null : Math.abs(g.margin - g.final.result)
}

export interface Score {
  games: number // games with a result
  picks: number // games with a decided pick (ties and 50-50s excluded)
  correct: number
  mae: number | null // mean absolute margin miss, points
}

function tally(games: CompletedGame[], correct: (g: CompletedGame) => boolean | null,
  miss: (g: CompletedGame) => number | null): Score {
  const picks = games.map(correct).filter((c): c is boolean => c !== null)
  const misses = games.map(miss).filter((m): m is number => m !== null)
  return {
    games: games.filter((g) => g.final.result !== null).length,
    picks: picks.length,
    correct: picks.filter(Boolean).length,
    mae: misses.length ? misses.reduce((a, b) => a + b, 0) / misses.length : null,
  }
}

/** Model and closing-market record over the same games. The market margin is the closing spread. */
export function scorecard(games: CompletedGame[]): { model: Score; market: Score } {
  return {
    model: tally(games, modelCorrect, marginMiss),
    market: tally(games, marketCorrect, (g) =>
      g.final.result === null || g.final.close_spread === null ? null : Math.abs(g.final.close_spread - g.final.result)),
  }
}
