// @vitest-environment jsdom
import { afterEach, describe, expect, test } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { GameRow } from '../GameRow'
import type { ProjectionGame, ProjectionTeam } from '@/types'

afterEach(cleanup)

const team = (code: string, name: string, starter: string | null): ProjectionTeam => ({
  team: code, name, conference: 'AFC', division: 'AFC North', record: '0-0', off: 1, def: 1,
  adj_off: 1, adj_def: 1, starter, qb_adj: 0, rush_off: 0, rush_def: 0, avg_wins: 8,
  wins_p10: 6, wins_p90: 10, div: 0.25, playoffs: 0.5, seed1: 0.05,
})
const home = team('BAL', 'Ravens', 'L.Jackson')
const away = team('JAX', 'Jaguars', null)

const game: ProjectionGame = {
  game_id: 'g1', week: 9, gameday: '2026-11-05', away: 'JAX', home: 'BAL', neutral: false,
  stadium: 'M&T Bank Stadium', p_home: 0.373, margin: -4.2312, nudge: 0.04, mkt_home: null, spread: null,
  components: {
    home_matchup: -223.0568, away_matchup: 476.8543, matchup_points: -6.3412, hfa: 2.11,
    nudge: 0.04, home_qb_adj_pts: -2.6627, away_qb_adj_pts: 0.0467,
  },
}
// margin consistent with components
game.margin = game.components.matchup_points + game.components.hfa + game.components.nudge

describe('GameRow', () => {
  test('shows — when market is null', () => {
    render(<GameRow game={game} home={home} away={away} />)
    expect(screen.getByText('Market').parentElement?.textContent).toContain('—')
  })

  test('shows market favorite name and percentage when present', () => {
    render(<GameRow game={{ ...game, mkt_home: 0.2086 }} home={home} away={away} />)
    expect(screen.getByText('Market').parentElement?.textContent).toContain('Jaguars 79%')
  })

  test('expand button toggles aria-expanded and shows components', async () => {
    render(<GameRow game={game} home={home} away={away} />)
    const btn = screen.getByRole('button', { name: /details/i })
    expect(btn.getAttribute('aria-expanded')).toBe('false')
    expect(screen.queryByText(/Home-field advantage/)).toBeNull()
    await userEvent.click(btn)
    expect(btn.getAttribute('aria-expanded')).toBe('true')
    expect(screen.getByText(/Home-field advantage/)).toBeTruthy()
    expect(screen.getByText(/already included in matchup/i)).toBeTruthy()
    expect(screen.getByText(/L\.Jackson/)).toBeTruthy()
    expect(screen.getAllByText(/rating units/i)).toHaveLength(2)
    await userEvent.click(btn)
    expect(btn.getAttribute('aria-expanded')).toBe('false')
  })

  test('null starter shows —', async () => {
    render(<GameRow game={game} home={home} away={away} />)
    await userEvent.click(screen.getByRole('button', { name: /details/i }))
    expect(screen.getByTestId('starter-away').textContent).toContain('—')
  })

  test('displayed components sum to the margin', async () => {
    render(<GameRow game={game} home={home} away={away} />)
    await userEvent.click(screen.getByRole('button', { name: /details/i }))
    const num = (id: string) => parseFloat(screen.getByTestId(id).textContent!.replace('−', '-'))
    const sum = num('comp-matchup') + num('comp-hfa') + num('comp-nudge')
    expect(Math.abs(sum - num('comp-total'))).toBeLessThanOrEqual(0.15)
    expect(Math.abs(num('comp-total') - game.margin)).toBeLessThanOrEqual(0.05)
  })

  test('neutral-site game shows the stadium', () => {
    render(<GameRow game={{ ...game, neutral: true, stadium: 'Wembley Stadium' }} home={home} away={away} />)
    expect(screen.getByText(/Wembley Stadium/)).toBeTruthy()
  })
})
