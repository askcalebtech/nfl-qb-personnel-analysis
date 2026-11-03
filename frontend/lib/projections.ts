import type { ProjectionGame, ProjectionTeam } from '@/types'

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

export function gamesInScope(games: ProjectionGame[], teams: ProjectionTeam[], s: Scope): ProjectionGame[] {
  if (s.kind === 'all') return games
  const codes = new Set(teamsInScope(teams, s).map((t) => t.team))
  return games.filter((g) => codes.has(g.home) || codes.has(g.away))
}

/** Earliest week that still has unplayed games (the data holds only unplayed games). */
export function defaultWeek(games: ProjectionGame[]): number | null {
  return games.length ? Math.min(...games.map((g) => g.week)) : null
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
