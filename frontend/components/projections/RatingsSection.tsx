'use client'

import { useMemo, useState } from 'react'
import { DataTable, type Column } from '@/components/ui/DataTable'
import { fmt } from '@/lib/format'
import { heatStyle } from '@/lib/heat'
import { rankRatings, type RatingRow } from '@/lib/projections'
import type { ProjectionTeam } from '@/types'

interface Props {
  allTeams: ProjectionTeam[] // all 32, so rank and heat scale never depend on the filter
  scopedTeams: ProjectionTeam[]
}

type View = 'raw' | 'adjusted'

export function RatingsSection({ allTeams, scopedTeams }: Props) {
  const [view, setView] = useState<View>('raw')

  const { rows, columns } = useMemo(() => {
    const ranked = rankRatings(allTeams, view)
    const maxOf = (f: (r: RatingRow) => number) => Math.max(0, ...ranked.map((r) => Math.abs(f(r))))
    const maxOff = maxOf((r) => r.off)
    const maxDef = maxOf((r) => r.def)
    const maxTotal = maxOf((r) => r.total)
    const codes = new Set(scopedTeams.map((t) => t.team))

    const cols: Column<RatingRow>[] = [
      { key: 'team', label: 'Team', align: 'left', render: (r) => r.team.name, sortValue: (r) => r.team.name },
      { key: 'rank', label: 'Rank', align: 'right', render: (r) => String(r.rank), sortValue: (r) => r.rank },
      { key: 'off', label: 'Off', align: 'right', render: (r) => fmt(r.off), sortValue: (r) => r.off, cellStyle: (r) => heatStyle(r.off, maxOff) },
      { key: 'def', label: 'Def', align: 'right', render: (r) => fmt(r.def), sortValue: (r) => r.def, cellStyle: (r) => heatStyle(r.def, maxDef) },
      { key: 'total', label: 'Total', align: 'right', render: (r) => fmt(r.total), sortValue: (r) => r.total, cellStyle: (r) => heatStyle(r.total, maxTotal) },
    ]
    if (view === 'adjusted') {
      cols.push(
        { key: 'qb', label: 'Projected QB', align: 'left', render: (r) => r.team.starter ?? '—', sortValue: (r) => r.team.starter },
        { key: 'qbadj', label: 'QB adj', align: 'right', render: (r) => fmt(r.team.qb_adj, 1, true), sortValue: (r) => r.team.qb_adj },
      )
    }
    return { rows: ranked.filter((r) => codes.has(r.team.team)), columns: cols }
  }, [allTeams, scopedTeams, view])

  const btn = (v: View, label: string) => (
    <button
      type="button"
      aria-pressed={view === v}
      onClick={() => setView(v)}
      className={`px-3 py-1.5 text-sm font-medium border border-gray-300 first:rounded-l last:rounded-r ${
        view === v ? 'bg-gray-900 text-white' : 'bg-white text-gray-800 hover:bg-gray-100'
      }`}
    >
      {label}
    </button>
  )

  return (
    <section aria-labelledby="ratings-h" className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="ratings-h" className="text-lg font-semibold text-gray-900">Team ratings</h2>
        <div className="inline-flex" role="group" aria-label="Ratings view">
          {btn('raw', 'Raw')}
          {btn('adjusted', 'Adjusted')}
        </div>
      </div>
      <p className="text-xs text-gray-600">
        Rating units, higher is better. Rank is among all 32 teams. Colors are scaled across all 32 teams.
      </p>
      <DataTable
        rows={rows}
        rowKey={(r) => r.team.team}
        columns={columns}
        caption={`Team ratings, ${view} view`}
        defaultSort={{ key: 'total', dir: 'desc' }}
        stickyFirstColumn
      />
    </section>
  )
}
