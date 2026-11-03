import { describe, expect, test } from 'vitest'
import {
  defaultWeek, gamesInScope, isStale, parseScope, rankRatings, scopeToParam, teamsInScope, type Scope,
} from '@/lib/projections'
import type { ProjectionGame, ProjectionTeam } from '@/types'

const t = (team: string, conference: string, division: string, off: number, def: number,
  adj_off: number, adj_def: number): ProjectionTeam => ({
  team, name: team, conference, division, record: '0-0', off, def, adj_off, adj_def,
  starter: null, qb_adj: 0, rush_off: 0, rush_def: 0, avg_wins: 8, wins_p10: 6, wins_p90: 10,
  div: 0.25, playoffs: 0.5, seed1: 0.05,
})
const teams = [
  t('BUF', 'AFC', 'AFC East', 365, -160, 318, -4),
  t('MIA', 'AFC', 'AFC East', 100, 20, 10, 20),
  t('MIN', 'NFC', 'NFC North', 200, -50, 80, 3),
  t('GB', 'NFC', 'NFC North', 250, -80, 20, 1),
]
const g = (game_id: string, week: number, away: string, home: string): ProjectionGame => ({
  game_id, week, gameday: '2026-11-05', away, home, neutral: false, stadium: null, p_home: 0.5,
  margin: 0, nudge: 0, mkt_home: null, spread: null,
  components: { home_matchup: 0, away_matchup: 0, matchup_points: 0, hfa: 2, nudge: 0, home_qb_adj_pts: 0, away_qb_adj_pts: 0 },
})
const games = [g('a', 9, 'MIA', 'BUF'), g('b', 10, 'GB', 'MIN'), g('c', 9, 'MIN', 'MIA')]

describe('scope', () => {
  test('gamesInScope includes a game when either team matches', () => {
    expect(gamesInScope(games, teams, { kind: 'team', value: 'MIA' }).map((x) => x.game_id)).toEqual(['a', 'c'])
    expect(gamesInScope(games, teams, { kind: 'conference', value: 'NFC' }).map((x) => x.game_id)).toEqual(['b', 'c'])
    expect(gamesInScope(games, teams, { kind: 'all' })).toHaveLength(3)
  })
  test('team on bye gets an empty list, not an error', () => {
    expect(gamesInScope(games, teams, { kind: 'team', value: 'BUF' }).map((x) => x.game_id)).toEqual(['a'])
    expect(gamesInScope(games, teams, { kind: 'team', value: 'GB' }).map((x) => x.game_id)).toEqual(['b'])
    expect(gamesInScope([g('z', 9, 'MIA', 'MIN')], teams, { kind: 'team', value: 'BUF' })).toEqual([])
  })
  test('teamsInScope returns only matching teams', () => {
    expect(teamsInScope(teams, { kind: 'division', value: 'NFC North' }).map((x) => x.team)).toEqual(['MIN', 'GB'])
  })
  test('parseScope falls back to all on an unknown value', () => {
    expect(parseScope('XYZ', teams)).toEqual({ kind: 'all' })
    expect(parseScope(null, teams)).toEqual({ kind: 'all' })
  })
  test('parseScope and scopeToParam round-trip every scope kind', () => {
    const scopes: Scope[] = [
      { kind: 'conference', value: 'NFC' },
      { kind: 'division', value: 'NFC North' },
      { kind: 'team', value: 'MIN' },
    ]
    for (const s of scopes) expect(parseScope(scopeToParam(s), teams)).toEqual(s)
    expect(scopeToParam({ kind: 'all' })).toBeNull()
  })
})

describe('defaultWeek', () => {
  test('defaultWeek is the earliest week with unplayed games', () => {
    expect(defaultWeek(games)).toBe(9)
  })
  test('defaultWeek is null when no games remain', () => {
    expect(defaultWeek([])).toBeNull()
  })
})

describe('rankRatings', () => {
  test('rankRatings keeps league-wide rank after filtering', () => {
    const rows = rankRatings(teams, 'raw')
    expect(rows.map((r) => r.team.team)).toEqual(['BUF', 'GB', 'MIN', 'MIA'])
    const nfc = rows.filter((r) => r.team.conference === 'NFC')
    expect(nfc.map((r) => r.rank)).toEqual([2, 3])
    expect(rows[0]).toMatchObject({ rank: 1, off: 365, def: -160, total: 205 })
  })
  test('adjusted view uses adj_off + adj_def', () => {
    const rows = rankRatings(teams, 'adjusted')
    expect(rows[0]).toMatchObject({ rank: 1, off: 318, def: -4, total: 314 })
  })
})

describe('isStale', () => {
  const now = new Date('2026-11-12T00:00:00Z')
  test('isStale true at 9 days with games left, false at 7 days', () => {
    expect(isStale('2026-11-03T00:00:00Z', now, 10)).toBe(true)
    expect(isStale('2026-11-05T00:00:00Z', now, 10)).toBe(false)
  })
  test('isStale true for an unparseable generatedAt', () => {
    expect(isStale('not a date', now, 10)).toBe(true)
    expect(isStale('', now, 10)).toBe(true)
  })
  test('isStale false when no games remain', () => {
    expect(isStale('2026-11-03T00:00:00Z', now, 0)).toBe(false)
  })
})
