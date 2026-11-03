// @vitest-environment jsdom
import { afterEach, describe, expect, test } from 'vitest'
import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { RatingsSection } from '../RatingsSection'
import type { ProjectionTeam } from '@/types'

afterEach(cleanup)

const mk = (code: string, division: string, off: number, def: number): ProjectionTeam => ({
  team: code, name: `Team ${code}`, conference: 'AFC', division, record: '0-0', off, def,
  adj_off: off * 2, adj_def: def * 2, starter: `QB.${code}`, qb_adj: 1.5, rush_off: 0, rush_def: 0,
  avg_wins: 8, wins_p10: 6, wins_p90: 10, div: 0.25, playoffs: 0.5, seed1: 0.05,
})
const all = [mk('AAA', 'AFC East', 10, 10), mk('BBB', 'AFC East', 5, 5), mk('CCC', 'AFC West', -8, -8)]

function offCellBg(name: RegExp) {
  const row = screen.getByRole('row', { name })
  return within(row).getAllByRole('cell')[2].style.backgroundColor
}

describe('RatingsSection', () => {
  test('Adjusted view shows QB columns; Raw does not', async () => {
    render(<RatingsSection allTeams={all} scopedTeams={all} />)
    expect(screen.queryByText('Projected QB')).toBeNull()
    const adj = screen.getByRole('button', { name: 'Adjusted' })
    expect(adj.getAttribute('aria-pressed')).toBe('false')
    await userEvent.click(adj)
    expect(adj.getAttribute('aria-pressed')).toBe('true')
    expect(screen.getByText('Projected QB')).toBeTruthy()
    expect(screen.getByText('QB adj')).toBeTruthy()
  })

  test('heat scale is unchanged by filtering', () => {
    const { unmount } = render(<RatingsSection allTeams={all} scopedTeams={all} />)
    const full = offCellBg(/Team BBB/)
    unmount()
    render(<RatingsSection allTeams={all} scopedTeams={[all[1]]} />)
    expect(offCellBg(/Team BBB/)).toBe(full)
  })

  test('keeps league rank when filtered', () => {
    render(<RatingsSection allTeams={all} scopedTeams={[all[2]]} />)
    const row = screen.getByRole('row', { name: /Team CCC/ })
    expect(within(row).getAllByRole('cell')[1].textContent).toBe('3')
  })
})
