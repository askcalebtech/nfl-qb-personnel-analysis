'use client'

import { useMemo } from 'react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { GamesSection } from './GamesSection'
import { OutlookSection } from './OutlookSection'
import { RatingsSection } from './RatingsSection'
import { ScopeFilter } from './ScopeFilter'
import { TeamSchedule } from './TeamSchedule'
import { defaultWeek, gamesInScope, isStale, parseScope, teamsInScope } from '@/lib/projections'
import type { ProjectionsData } from '@/types'

export function ProjectionsView({ data }: { data: ProjectionsData }) {
  const router = useRouter()
  const pathname = usePathname()
  const sp = useSearchParams()

  const scope = useMemo(() => parseScope(sp.get('scope'), data.teams), [sp, data.teams])
  const weeks = useMemo(() => Array.from(new Set(data.games.map((g) => g.week))).sort((a, b) => a - b), [data.games])
  const fallback = defaultWeek(data.games)
  const weekParam = Number(sp.get('week'))
  const week = weeks.includes(weekParam) ? weekParam : fallback

  function update(changes: { scope?: string | null; week?: number }) {
    const next = new URLSearchParams(sp.toString())
    if ('scope' in changes) {
      if (changes.scope) next.set('scope', changes.scope)
      else next.delete('scope')
    }
    if (changes.week !== undefined) next.set('week', String(changes.week))
    const q = next.toString()
    router.replace(q ? `${pathname}?${q}` : pathname, { scroll: false })
  }

  const scopedTeams = teamsInScope(data.teams, scope)
  const scopedGames = gamesInScope(data.games, data.teams, scope)
  const weekGames = scopedGames.filter((g) => g.week === week)
  const stale = isStale(data.generated_at, new Date(), data.games.length)
  const generated = new Date(data.generated_at)
  const generatedText = Number.isNaN(generated.getTime()) ? data.generated_at : generated.toLocaleString()
  const team = scope.kind === 'team' ? data.teams.find((t) => t.team === scope.value) : undefined

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-bold text-gray-900">ANY/A Projections</h1>
        <p className="text-sm text-gray-700">
          Through Week {data.through_week} · Generated {generatedText}
        </p>
        {stale && (
          <p className="rounded border border-amber-400 bg-amber-50 p-3 text-sm font-medium text-amber-900">
            These projections may be out of date. They were generated {generatedText}, and games remain unplayed.
          </p>
        )}
        {data.warnings.length > 0 && (
          <div className="rounded border border-amber-400 bg-amber-50 p-3 text-sm text-amber-900">
            <p className="font-semibold">Warnings</p>
            <ul className="list-disc pl-5">
              {data.warnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          </div>
        )}
      </header>

      <ScopeFilter teams={data.teams} scope={scope} onChange={(s) => update({ scope: s })} />

      <GamesSection
        week={week}
        weeks={weeks}
        games={weekGames}
        teams={data.teams}
        scope={scope}
        onWeekChange={(w) => update({ week: w })}
      />

      {team && <TeamSchedule team={team} week={week} games={scopedGames} teams={data.teams} />}

      <OutlookSection teams={scopedTeams} />
      <RatingsSection allTeams={data.teams} scopedTeams={scopedTeams} />
    </div>
  )
}
