'use client'

import { GameRow } from './GameRow'
import type { ProjectionGame, ProjectionTeam } from '@/types'

interface Props {
  games: ProjectionGame[] // all games involving the team
  teams: ProjectionTeam[]
}

export function TeamSchedule({ games, teams }: Props) {
  const byCode = new Map(teams.map((t) => [t.team, t]))
  const remaining = [...games].sort((a, b) => a.week - b.week)
  return (
    <section aria-labelledby="sched-h" className="space-y-3">
      <h2 id="sched-h" className="text-lg font-semibold text-gray-900">
        Remaining schedule
      </h2>
      {remaining.length === 0 ? (
        <p className="rounded-lg border border-gray-200 bg-white p-4 text-sm text-gray-700">
          The regular season is complete.
        </p>
      ) : (
        <ul className="space-y-2">
          {remaining.map((g) => {
            const home = byCode.get(g.home)
            const away = byCode.get(g.away)
            return home && away ? <GameRow key={g.game_id} game={g} home={home} away={away} showWeek /> : null
          })}
        </ul>
      )}
    </section>
  )
}
