// @vitest-environment jsdom
import { afterEach, describe, expect, test } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { TeamSchedule } from '../TeamSchedule'
import type { ProjectionGame, ProjectionTeam } from '@/types'

afterEach(cleanup)

const team = (code: string, name: string): ProjectionTeam => ({
  team: code, name, conference: 'AFC', division: 'AFC East', record: '0-0', off: 1, def: 1,
  adj_off: 1, adj_def: 1, starter: null, qb_adj: 0, rush_off: 0, rush_def: 0, avg_wins: 8,
  wins_p10: 6, wins_p90: 10, div: 0.25, playoffs: 0.5, seed1: 0.05,
})
const teams = [team('AAA', 'Alphas'), team('BBB', 'Bravos'), team('CCC', 'Charlies')]
const game = (week: number, home: string, away: string): ProjectionGame => ({
  game_id: `g${week}`, week, gameday: null, away, home, neutral: false, stadium: null,
  p_home: 0.5, margin: 1, nudge: 0, mkt_home: null, spread: null,
  components: { home_matchup: 0, away_matchup: 0, matchup_points: 1, hfa: 0, nudge: 0, home_qb_adj_pts: 0, away_qb_adj_pts: 0 },
})

describe('TeamSchedule', () => {
  test('shows all unplayed games in week order, including weeks before the selected week', () => {
    // the view passes every game for the team regardless of the selected week (e.g. Week 12)
    render(<TeamSchedule games={[game(12, 'AAA', 'BBB'), game(9, 'CCC', 'AAA'), game(10, 'AAA', 'CCC')]} teams={teams} />)
    expect(screen.getByRole('heading', { name: 'Remaining schedule' })).toBeTruthy()
    const items = screen.getAllByRole('listitem').map((li) => li.textContent ?? '')
    expect(items).toHaveLength(3)
    expect(items[0]).toContain('Week 9')
    expect(items[1]).toContain('Week 10')
    expect(items[2]).toContain('Week 12')
  })

  test('shows season-complete copy when the team has no games', () => {
    render(<TeamSchedule games={[]} teams={teams} />)
    expect(screen.getByText('The regular season is complete.')).toBeTruthy()
    expect(screen.queryByText(/null/)).toBeNull()
  })
})
