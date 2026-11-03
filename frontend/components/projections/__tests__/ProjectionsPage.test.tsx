// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ProjectionsLoader } from '../ProjectionsLoader'
import { ProjectionsView } from '../ProjectionsView'
import type { ProjectionGame, ProjectionTeam, ProjectionsData } from '@/types'

const nav = vi.hoisted(() => ({ replace: vi.fn(), search: '' }))
vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace: nav.replace }),
  usePathname: () => '/projections',
  useSearchParams: () => new URLSearchParams(nav.search),
}))

beforeEach(() => {
  nav.replace.mockReset()
  nav.search = ''
})
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

const team = (code: string, name: string, division: string): ProjectionTeam => ({
  team: code, name, conference: 'AFC', division, record: '0-0', off: 1, def: 1,
  adj_off: 1, adj_def: 1, starter: null, qb_adj: 0, rush_off: 0, rush_def: 0, avg_wins: 8,
  wins_p10: 6, wins_p90: 10, div: 0.25, playoffs: 0.5, seed1: 0.05,
})
const game = (week: number, home: string, away: string): ProjectionGame => ({
  game_id: `g${week}${home}`, week, gameday: null, away, home, neutral: false, stadium: null,
  p_home: 0.5, margin: 1, nudge: 0, mkt_home: null, spread: null,
  components: { home_matchup: 0, away_matchup: 0, matchup_points: 1, hfa: 0, nudge: 0, home_qb_adj_pts: 0, away_qb_adj_pts: 0 },
})
const base: ProjectionsData = {
  season: 2026, through_week: 8, generated_at: new Date().toISOString(), league_anya: 6,
  model_version: '1', warnings: [],
  teams: [team('AAA', 'Alphas', 'AFC East'), team('BBB', 'Bravos', 'AFC East')],
  games: [game(9, 'AAA', 'BBB'), game(10, 'BBB', 'AAA')],
}

describe('ProjectionsView', () => {
  test('warnings from the JSON are displayed', () => {
    render(<ProjectionsView data={{ ...base, warnings: ['Odds file missing for week 12'] }} />)
    expect(screen.getByText(/Odds file missing for week 12/)).toBeTruthy()
  })

  test('shows season complete when there are no games', () => {
    render(<ProjectionsView data={{ ...base, games: [] }} />)
    expect(screen.getByText('The regular season is complete.')).toBeTruthy()
  })

  test('old generated_at with games remaining shows the stale banner', () => {
    const old = new Date(Date.now() - 20 * 86_400_000).toISOString()
    render(<ProjectionsView data={{ ...base, generated_at: old }} />)
    expect(screen.getByText(/may be out of date/i)).toBeTruthy()
  })

  test('fresh data shows no stale banner', () => {
    render(<ProjectionsView data={base} />)
    expect(screen.queryByText(/may be out of date/i)).toBeNull()
  })

  test('choosing a scope calls router.replace and keeps week', async () => {
    nav.search = 'week=10'
    render(<ProjectionsView data={base} />)
    await userEvent.selectOptions(screen.getByLabelText('Show'), 'AAA')
    expect(nav.replace).toHaveBeenCalledTimes(1)
    const url = new URL(nav.replace.mock.calls[0][0] as string, 'http://x')
    expect(url.pathname).toBe('/projections')
    expect(url.searchParams.get('scope')).toBe('AAA')
    expect(url.searchParams.get('week')).toBe('10')
  })

  test('choosing a week keeps scope', async () => {
    nav.search = 'scope=AAA'
    render(<ProjectionsView data={base} />)
    await userEvent.selectOptions(screen.getByLabelText('Week'), '10')
    const url = new URL(nav.replace.mock.calls[0][0] as string, 'http://x')
    expect(url.searchParams.get('scope')).toBe('AAA')
    expect(url.searchParams.get('week')).toBe('10')
  })

  test('selecting All removes scope but keeps week', async () => {
    nav.search = 'scope=AAA&week=10'
    render(<ProjectionsView data={base} />)
    await userEvent.selectOptions(screen.getByLabelText('Show'), '')
    expect(nav.replace).toHaveBeenCalledWith('/projections?week=10', { scroll: false })
  })

  test('team scope shows earlier unplayed games when a later week is selected', () => {
    nav.search = 'scope=AAA&week=10'
    render(<ProjectionsView data={base} />)
    const sched = screen.getByRole('heading', { name: 'Remaining schedule' }).closest('section')!
    expect(sched.textContent).toContain('Week 9')
    expect(sched.textContent).toContain('Week 10')
  })
})

describe('ProjectionsLoader', () => {
  test('failed fetch shows an alert; Retry refetches and renders data', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: false, status: 500, json: async () => ({}) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => base })
    vi.stubGlobal('fetch', fetchMock)
    render(<ProjectionsLoader />)
    const alert = await screen.findByRole('alert')
    expect(alert.textContent).toMatch(/couldn.t be loaded/i)
    await userEvent.click(screen.getByRole('button', { name: 'Retry' }))
    await waitFor(() => expect(screen.getByRole('heading', { level: 1 })).toBeTruthy())
    expect(screen.queryByRole('alert')).toBeNull()
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(fetchMock.mock.calls[1][0]).toBe('/data/projections.json')
  })

  test('network error also shows the alert', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))
    render(<ProjectionsLoader />)
    expect(await screen.findByRole('alert')).toBeTruthy()
  })
})
