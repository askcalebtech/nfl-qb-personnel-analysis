'use client'

import { useId, useState } from 'react'
import { fmt, marginLabel, pct } from '@/lib/format'
import type { ProjectionGame, ProjectionTeam } from '@/types'

interface Props {
  game: ProjectionGame
  home: ProjectionTeam
  away: ProjectionTeam
  showWeek?: boolean
}

function formatDay(day: string | null): string | null {
  if (!day) return null
  const [y, m, d] = day.split('-').map(Number)
  if (!y || !m || !d) return null
  return new Date(y, m - 1, d).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })
}

function Pts({ label, value, testId, strong }: { label: string; value: number; testId: string; strong?: boolean }) {
  return (
    <div className={`flex justify-between gap-4 ${strong ? 'border-t border-gray-300 pt-1 font-semibold' : ''}`}>
      <dt className="text-gray-700">{label}</dt>
      <dd className="text-gray-900 tabular-nums">
        <span data-testid={testId}>{fmt(value, 1, true)}</span> pts
      </dd>
    </div>
  )
}

export function GameRow({ game, home, away, showWeek = false }: Props) {
  const [open, setOpen] = useState(false)
  const panelId = useId()
  const c = game.components
  const favorite = game.margin >= 0 ? home : away
  const mkt =
    game.mkt_home === null
      ? '—'
      : game.mkt_home >= 0.5
        ? `${home.name} ${pct(game.mkt_home)}`
        : `${away.name} ${pct(1 - game.mkt_home)}`
  const day = formatDay(game.gameday)

  return (
    <li className="rounded-lg border border-gray-200 bg-white p-3 text-gray-900">
      <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
        <div className="min-w-0">
          <p className="font-semibold text-gray-900">
            {away.name} @ {home.name}
          </p>
          <p className="text-xs text-gray-600">
            {[showWeek ? `Week ${game.week}` : null, day, game.neutral ? `Neutral site${game.stadium ? `: ${game.stadium}` : ''}` : null]
              .filter(Boolean)
              .join(' · ')}
          </p>
        </div>
        <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm">
          <div>
            <div className="text-xs text-gray-600">Win %</div>
            <div className="tabular-nums text-gray-900">
              {away.name} {pct(1 - game.p_home)} · {home.name} {pct(game.p_home)}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-600">Projection</div>
            <div className="text-gray-900">{marginLabel(favorite.name, game.margin)}</div>
          </div>
          <div className="border-l border-gray-300 pl-4">
            <div className="text-xs text-gray-600">Market</div>
            <div className="tabular-nums text-gray-900">{mkt}</div>
          </div>
        </div>
      </div>

      <button
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((v) => !v)}
        className="mt-2 text-sm font-medium text-blue-700 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
      >
        <span aria-hidden="true">{open ? '▾ ' : '▸ '}</span>Details
        <span className="sr-only"> for {away.name} at {home.name}</span>
      </button>

      {open && (
        <div id={panelId} className="mt-2 grid gap-4 border-t border-gray-100 pt-3 text-sm sm:grid-cols-2">
          <div>
            <h3 className="mb-1 font-semibold text-gray-900">Margin, in points toward {home.name}</h3>
            <dl className="space-y-1">
              <Pts label={`${home.name} matchup points`} value={c.matchup_points} testId="comp-matchup" />
              <Pts label="Home-field advantage" value={c.hfa} testId="comp-hfa" />
              <Pts label="Rush nudge" value={c.nudge} testId="comp-nudge" />
              <Pts label="Total (projected margin)" value={game.margin} testId="comp-total" strong />
            </dl>
          </div>
          <div className="space-y-3">
            <dl className="space-y-1">
              <div className="flex justify-between gap-4">
                <dt className="text-gray-700">Home matchup</dt>
                <dd className="text-gray-900 tabular-nums">{fmt(c.home_matchup)} rating units</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-gray-700">Away matchup</dt>
                <dd className="text-gray-900 tabular-nums">{fmt(c.away_matchup)} rating units</dd>
              </div>
            </dl>
            <div>
              <p className="mb-1 text-gray-700">QB adjustments (already included in matchup)</p>
              <ul className="space-y-1 text-gray-900">
                <li data-testid="starter-home">
                  {home.name}: {home.starter ?? '—'}, {fmt(c.home_qb_adj_pts, 1, true)} pts
                </li>
                <li data-testid="starter-away">
                  {away.name}: {away.starter ?? '—'}, {fmt(c.away_qb_adj_pts, 1, true)} pts
                </li>
              </ul>
            </div>
          </div>
        </div>
      )}
    </li>
  )
}
