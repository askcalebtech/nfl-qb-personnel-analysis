// @vitest-environment jsdom
import { afterEach, describe, expect, test, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { ProjectionsView } from '../ProjectionsView'
import type { ProjectionsData } from '@/types'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace: vi.fn() }),
  usePathname: () => '/projections',
  useSearchParams: () => new URLSearchParams(),
}))

afterEach(cleanup)

const data: ProjectionsData = {
  season: 2026, through_week: 8, generated_at: new Date().toISOString(), league_anya: 6,
  model_version: '1', warnings: ['Odds file missing for week 12'], teams: [], games: [],
}

describe('ProjectionsView', () => {
  test('warnings from the JSON are displayed', () => {
    render(<ProjectionsView data={data} />)
    expect(screen.getByText(/Odds file missing for week 12/)).toBeTruthy()
  })
  test('shows season complete when there are no games', () => {
    render(<ProjectionsView data={data} />)
    expect(screen.getByText('The regular season is complete.')).toBeTruthy()
  })
})
