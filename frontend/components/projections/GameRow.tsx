'use client'

import { useId, useState } from 'react'
import { fmt, marginLabel, pct } from '@/lib/format'
import { isPastGameday, marginMiss, modelCorrect } from '@/lib/projections'
import type { CompletedGame, ProjectionGame, ProjectionTeam } from '@/types'

interface Props {
  game: ProjectionGame | CompletedGame
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

function isCompleted(g: ProjectionGame | CompletedGame): g is CompletedGame {
  return 'final' in g && g.final !== undefined
}

function formatPublished(iso: string | null): string | null {
  if (!iso) return null
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? null : d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

function Result({ game, home, away }: { game: CompletedGame; home: ProjectionTeam; away: ProjectionTeam }) {
  const f = game.final
  const correct = modelCorrect(game)
  const miss = marginMiss(game)
  const published = formatPublished(game.predicted_at)
  const byCode: Record<string, ProjectionTeam> = { [home.team]: home, [away.team]: away }
  const fixed = Object.entries(game.corrected_starters ?? {})
    .map(([t, qb]) => `${qb} at QB for the ${byCode[t]?.name ?? t}`)
    .join(' and ')
  const source =
    game.source === 'backfill'
      ? 'Backfilled: predicted from earlier weeks\u2019 games only'
      : game.source === 'corrected'
        ? `Prediction from ${published ?? 'publication'}, corrected to ${fixed || 'the actual starter'}`
        : `Prediction as published${published ? ` ${published}` : ''}`
  return (
    <div className="mt-1 space-y-1">
      <p className="text-sm text-gray-900" data-testid="final">
        <span className="font-semibold">Final:</span> {away.name} {f.away_score ?? '—'}, {home.name} {f.home_score ?? '—'}
      </p>
      <div className="flex flex-wrap items-center gap-2 text-xs">
        {correct !== null && (
          <span
            data-testid="model-pick"
            className={`rounded border px-1.5 py-0.5 font-medium ${
              correct ? 'border-green-600 bg-green-50 text-green-900' : 'border-red-600 bg-red-50 text-red-900'
            }`}
          >
            {correct ? '✓ Model pick right' : '✗ Model pick wrong'}
          </span>
        )}
        {correct === null && f.result === 0 && <span className="text-gray-700">Tie</span>}
        {miss !== null && <span className="text-gray-700">Missed margin by {miss.toFixed(1)} pts</span>}
      </div>
      <p className="text-xs text-gray-600">{source}</p>
    </div>
  )
}

export function GameRow({ game, home, away, showWeek = false }: Props) {
  const [open, setOpen] = useState(false)
  const panelId = useId()
  const c = game.components
  const completed = isCompleted(game) ? game : null
  const favorite = game.margin >= 0 ? home : away
  const mktHome = completed ? completed.final.close_mkt_home : game.mkt_home
  const mkt =
    mktHome === null
      ? '—'
      : mktHome >= 0.5
        ? `${home.name} ${pct(mktHome)}`
        : `${away.name} ${pct(1 - mktHome)}`
  const day = formatDay(game.gameday)
  const played = !completed && isPastGameday(game.gameday, new Date())
  const homeStarter = completed ? completed.home_starter : home.starter
  const awayStarter = completed ? completed.away_starter : away.starter

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
          {completed && <Result game={completed} home={home} away={away} />}
          {played && (
            <p className="mt-1 inline-block rounded border border-amber-400 bg-amber-50 px-1.5 py-0.5 text-xs font-medium text-amber-900">
              Played, result not loaded yet
            </p>
          )}
        </div>
        <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm">
          <div>
            <div className="text-xs text-gray-600">{completed ? 'Pre-game win %' : 'Win %'}</div>
            <div className="tabular-nums text-gray-900">
              {away.name} {pct(1 - game.p_home)} · {home.name} {pct(game.p_home)}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-600">Projection</div>
            <div className="text-gray-900">{marginLabel(favorite.name, game.margin)}</div>
          </div>
          <div className="border-l border-gray-300 pl-4">
            <div className="text-xs text-gray-600">{completed ? 'Market (close)' : 'Market'}</div>
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
                  {home.name}: {homeStarter ?? '—'}, {fmt(c.home_qb_adj_pts, 1, true)} pts
                </li>
                <li data-testid="starter-away">
                  {away.name}: {awayStarter ?? '—'}, {fmt(c.away_qb_adj_pts, 1, true)} pts
                </li>
              </ul>
            </div>
          </div>
        </div>
      )}
    </li>
  )
}
