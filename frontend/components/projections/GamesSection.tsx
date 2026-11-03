'use client'

import { GameRow } from './GameRow'
import type { Scope } from '@/lib/projections'
import type { ProjectionGame, ProjectionTeam } from '@/types'

interface Props {
  week: number | null
  weeks: number[]
  games: ProjectionGame[] // already filtered to scope and week
  teams: ProjectionTeam[]
  scope: Scope
  onWeekChange: (w: number) => void
}

export function GamesSection({ week, weeks, games, teams, scope, onWeekChange }: Props) {
  const byCode = new Map(teams.map((t) => [t.team, t]))
  const scopeTeam = scope.kind === 'team' ? byCode.get(scope.value) : undefined

  let empty: string | null = null
  if (week === null) empty = 'The regular season is complete.'
  else if (games.length === 0)
    empty = scopeTeam ? `${scopeTeam.name} is on bye in Week ${week}.` : `No games match this filter in Week ${week}.`

  return (
    <section aria-labelledby="games-h" className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="games-h" className="text-lg font-semibold text-gray-900">
          {week === null ? 'Games' : `Week ${week} games`}
        </h2>
        {week !== null && (
          <label className="flex items-center gap-2 text-sm text-gray-700">
            Week
            <select
              value={week}
              onChange={(e) => onWeekChange(Number(e.target.value))}
              className="rounded border border-gray-300 bg-white px-2 py-1 text-gray-900"
            >
              {weeks.map((w) => (
                <option key={w} value={w}>
                  {w}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>
      {empty ? (
        <p className="rounded-lg border border-gray-200 bg-white p-4 text-sm text-gray-700">{empty}</p>
      ) : (
        <ul className="space-y-2">
          {games.map((g) => {
            const home = byCode.get(g.home)
            const away = byCode.get(g.away)
            return home && away ? <GameRow key={g.game_id} game={g} home={home} away={away} /> : null
          })}
        </ul>
      )}
    </section>
  )
}
