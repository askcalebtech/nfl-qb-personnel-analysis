// @vitest-environment jsdom
import { StrictMode } from 'react'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ProjectionsLoader } from '../ProjectionsLoader'
import { ProjectionsView } from '../ProjectionsView'
import type { CompletedGame, ProjectionGame, ProjectionTeam, ProjectionsData } from '@/types'

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
  season: 2026, through_week: 8, last_result_date: null, generated_at: new Date().toISOString(), league_anya: 6,
  model_version: '1', warnings: [],
  teams: [team('AAA', 'Alphas', 'AFC East'), team('BBB', 'Bravos', 'AFC East')],
  games: [game(9, 'AAA', 'BBB'), game(10, 'BBB', 'AAA')],
}

const final = (week: number, home: string, away: string, result: number, over: Partial<CompletedGame> = {}): CompletedGame => ({
  ...game(week, home, away), game_id: `c${week}${home}`, gameday: '2026-11-05', p_home: 0.6, margin: 3,
  source: 'published', predicted_at: '2026-11-03T19:27:48Z', home_starter: 'H.Then', away_starter: 'A.Then',
  final: { home_score: result > 0 ? 20 + result : 20, away_score: result > 0 ? 20 : 20 - result, result,
    close_mkt_home: 0.4, close_spread: -2 },
  ...over,
})

describe('ProjectionsView', () => {
  test('header shows season, through week and result date', () => {
    render(<ProjectionsView data={{ ...base, last_result_date: '2026-11-02' }} />)
    const p = screen.getByRole('heading', { level: 1 }).nextElementSibling as HTMLElement
    expect(p.textContent).toContain('2026 season · Through Week 8')
    expect(p.textContent).toContain('Results through Nov 2, 2026')
  })

  test('header omits result date when absent', () => {
    render(<ProjectionsView data={{ ...base, last_result_date: null }} />)
    const p = screen.getByRole('heading', { level: 1 }).nextElementSibling as HTMLElement
    expect(p.textContent).toContain('2026 season · Through Week 8')
    expect(p.textContent).not.toContain('Results through')
  })

  test('past gameday shows tag and section note', () => {
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(new Date(2026, 10, 3, 12))
    try {
      const g = { ...game(9, 'AAA', 'BBB'), gameday: '2026-11-02' }
      const { unmount } = render(<ProjectionsView data={{ ...base, games: [g] }} />)
      expect(screen.getByText('Played, result not loaded yet')).toBeTruthy()
      expect(screen.getByText(/results are not loaded yet/i)).toBeTruthy()
      unmount()
      render(<ProjectionsView data={{ ...base, games: [{ ...g, gameday: '2026-11-03' }] }} />)
      expect(screen.queryByText('Played, result not loaded yet')).toBeNull()
      expect(screen.queryByText(/results are not loaded yet/i)).toBeNull()
    } finally {
      vi.useRealTimers()
    }
  })

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

  test('an older response cannot overwrite a newer one', async () => {
    const resolvers: Array<(v: unknown) => void> = []
    const fetchMock = vi.fn().mockImplementation(
      () => new Promise((res) => resolvers.push(res)),
    )
    vi.stubGlobal('fetch', fetchMock)
    // StrictMode runs the load effect twice, so two requests are in flight.
    render(
      <StrictMode>
        <ProjectionsLoader />
      </StrictMode>,
    )
    await waitFor(() => expect(resolvers.length).toBe(2))
    const reply = (season: number) => ({ ok: true, status: 200, json: async () => ({ ...base, season }) })
    resolvers[1](reply(2031)) // newer request answers first
    await waitFor(() => expect(screen.getByText(/2031 season/)).toBeTruthy())
    resolvers[0](reply(2020)) // older request answers late
    await new Promise((r) => setTimeout(r, 20))
    expect(screen.getByText(/2031 season/)).toBeTruthy()
    expect(screen.queryByText(/2020 season/)).toBeNull()
  })

  test('network error also shows the alert', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))
    render(<ProjectionsLoader />)
    expect(await screen.findByRole('alert')).toBeTruthy()
  })

  describe('completed games', () => {
    test('a week mixes completed and upcoming games; completed shows final, pick and source', () => {
      nav.search = 'week=9'
      const data = { ...base, games: [game(9, 'AAA', 'BBB')], completed: [final(9, 'BBB', 'AAA', -10)] }
      render(<ProjectionsView data={data} />)
      expect(screen.getAllByRole('listitem')).toHaveLength(2)
      expect(screen.getByTestId('final').textContent).toBe('Final: Alphas 30, Bravos 20')
      expect(screen.getByTestId('model-pick').textContent).toContain('wrong')
      expect(screen.getByText('Missed margin by 13.0 pts')).toBeTruthy()
      expect(screen.getByText(/Prediction as published Nov 3/)).toBeTruthy()
      const row = screen.getByTestId('final').closest('li') as HTMLElement
      expect(within(row).getByText('Market (close)')).toBeTruthy()
      expect(within(row).getByText('Alphas 60%')).toBeTruthy() // closing line, not the pre-game one
      expect(screen.queryByText('Played, result not loaded yet')).toBeNull()
    })

    test('scorecard shows week and season records for model and market', () => {
      nav.search = 'week=9'
      const completed = [
        final(8, 'AAA', 'BBB', 7, { source: 'backfill', predicted_at: null }),
        final(9, 'BBB', 'AAA', -10),
      ]
      render(<ProjectionsView data={{ ...base, completed }} />)
      expect(screen.getByTestId('Week 9-model-record').textContent).toBe('0-1 (0%)')
      expect(screen.getByTestId('Week 9-market-record').textContent).toBe('1-0 (100%)')
      expect(screen.getByTestId('Season to date-model-record').textContent).toBe('1-1 (50%)')
      expect(screen.getByTestId('Season to date-model-mae').textContent).toBe('8.5 pts')
    })

    test('completed-only weeks are selectable and backfill is labeled', () => {
      nav.search = 'week=8'
      render(<ProjectionsView data={{ ...base, completed: [final(8, 'AAA', 'BBB', 7, { source: 'backfill', predicted_at: null })] }} />)
      expect(screen.getByRole('heading', { name: 'Week 8 games' })).toBeTruthy()
      expect(screen.getByText(/Backfilled: predicted from earlier weeks/)).toBeTruthy()
      expect(screen.getByTestId('model-pick').textContent).toContain('right')
    })

    test('details use the starters at prediction time', async () => {
      nav.search = 'week=9'
      render(<ProjectionsView data={{ ...base, games: [], completed: [final(9, 'BBB', 'AAA', -10)] }} />)
      await userEvent.click(screen.getByRole('button', { name: /Details/ }))
      expect(screen.getByTestId('starter-home').textContent).toContain('H.Then')
    })

    test('after the season ends the last played week is shown, not the complete message', () => {
      render(<ProjectionsView data={{ ...base, games: [], completed: [final(18, 'AAA', 'BBB', 3)] }} />)
      expect(screen.getByRole('heading', { name: 'Week 18 games' })).toBeTruthy()
    })

    test('a corrected prediction is shown and scored like any other', () => {
      nav.search = 'week=9'
      const g = final(9, 'BBB', 'AAA', 1, {
        p_home: 0.52, margin: 0.5, source: 'corrected', corrected_starters: { AAA: 'S.Backup' }, note: 'Backup started.',
      })
      render(<ProjectionsView data={{ ...base, games: [], completed: [g] }} />)
      expect(screen.getByText('Prediction from Nov 3, corrected to S.Backup at QB for the Alphas')).toBeTruthy()
      expect(screen.getByTestId('model-pick').textContent).toContain('right')
      expect(screen.getByTestId('Week 9-model-record').textContent).toBe('1-0 (100%)')
      expect(screen.queryByTestId('whatif')).toBeNull()
    })

    test('no scorecard without completed games', () => {
      render(<ProjectionsView data={base} />)
      expect(screen.queryByRole('region', { name: 'Model scorecard' })).toBeNull()
    })
  })
})
