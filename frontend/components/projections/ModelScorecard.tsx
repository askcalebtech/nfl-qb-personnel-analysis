'use client'

import { scorecard, type Score } from '@/lib/projections'
import type { CompletedGame } from '@/types'

interface Props {
  week: number | null
  weekGames: CompletedGame[] // completed, in scope, selected week
  seasonGames: CompletedGame[] // completed, in scope, all weeks
}

function record(s: Score): string {
  if (!s.picks) return '—'
  return `${s.correct}-${s.picks - s.correct} (${Math.round((100 * s.correct) / s.picks)}%)`
}

function mae(s: Score): string {
  return s.mae === null ? '—' : `${s.mae.toFixed(1)} pts`
}

function Block({ title, games }: { title: string; games: CompletedGame[] }) {
  const { model, market } = scorecard(games)
  return (
    <div className="min-w-0">
      <h3 className="text-sm font-semibold text-gray-900">
        {title} <span className="font-normal text-gray-600">· {model.games} games</span>
      </h3>
      <table className="mt-1 text-sm tabular-nums">
        <thead>
          <tr className="text-xs text-gray-600">
            <th scope="col" className="pr-4 text-left font-normal" />
            <th scope="col" className="pr-4 text-left font-normal">Winners</th>
            <th scope="col" className="text-left font-normal">Avg. margin miss</th>
          </tr>
        </thead>
        <tbody className="text-gray-900">
          <tr>
            <th scope="row" className="pr-4 text-left font-medium">Model</th>
            <td className="pr-4" data-testid={`${title}-model-record`}>{record(model)}</td>
            <td data-testid={`${title}-model-mae`}>{mae(model)}</td>
          </tr>
          <tr>
            <th scope="row" className="pr-4 text-left font-medium">Market (close)</th>
            <td className="pr-4" data-testid={`${title}-market-record`}>{record(market)}</td>
            <td data-testid={`${title}-market-mae`}>{mae(market)}</td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}

/** How the model did on completed games in the current filter, next to the closing betting line. */
export function ModelScorecard({ week, weekGames, seasonGames }: Props) {
  if (!seasonGames.length) return null
  return (
    <section aria-label="Model scorecard" className="rounded-lg border border-gray-200 bg-white p-3">
      <div className="flex flex-wrap gap-x-10 gap-y-3">
        {week !== null && weekGames.length > 0 && <Block title={`Week ${week}`} games={weekGames} />}
        <Block title="Season to date" games={seasonGames} />
      </div>
      <p className="mt-2 text-xs text-gray-600">
        Ties and 50-50 picks are left out of the winner counts. Games played before the site started publishing
        are backfilled from earlier weeks&rsquo; games, with constants fit on data that includes them, so they
        flatter the model slightly. Week 1 has no earlier games and uses home field only.
      </p>
    </section>
  )
}
