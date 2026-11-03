'use client'

import { DataTable, type Column } from '@/components/ui/DataTable'
import { fmt, pct } from '@/lib/format'
import type { ProjectionTeam } from '@/types'

const columns: Column<ProjectionTeam>[] = [
  { key: 'team', label: 'Team', align: 'left', render: (t) => t.name, sortValue: (t) => t.name },
  { key: 'record', label: 'Record', align: 'right', render: (t) => t.record },
  { key: 'avg', label: 'Avg wins', align: 'right', render: (t) => fmt(t.avg_wins), sortValue: (t) => t.avg_wins },
  {
    key: 'range', label: '80% range', align: 'right',
    render: (t) => `${Math.round(t.wins_p10)}–${Math.round(t.wins_p90)}`,
    sortValue: (t) => t.wins_p10,
  },
  { key: 'div', label: 'Win division', align: 'right', render: (t) => pct(t.div), sortValue: (t) => t.div },
  { key: 'playoffs', label: 'Playoffs', align: 'right', render: (t) => pct(t.playoffs), sortValue: (t) => t.playoffs },
  { key: 'seed1', label: '#1 seed', align: 'right', render: (t) => pct(t.seed1), sortValue: (t) => t.seed1 },
]

export function OutlookSection({ teams }: { teams: ProjectionTeam[] }) {
  const divisions = Array.from(new Set(teams.map((t) => t.division))).sort()
  return (
    <section aria-labelledby="outlook-h" className="space-y-3">
      <h2 id="outlook-h" className="text-lg font-semibold text-gray-900">Season outlook</h2>
      {divisions.map((d) => (
        <div key={d} className="space-y-1">
          <h3 className="text-sm font-semibold text-gray-800">{d}</h3>
          <DataTable
            rows={teams.filter((t) => t.division === d)}
            rowKey={(t) => t.team}
            columns={columns}
            caption={`${d} season outlook`}
            defaultSort={{ key: 'avg', dir: 'desc' }}
            stickyFirstColumn
          />
        </div>
      ))}
    </section>
  )
}
