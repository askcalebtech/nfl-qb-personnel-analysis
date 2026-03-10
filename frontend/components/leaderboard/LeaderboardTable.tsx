'use client'

import { useState } from 'react'
import type { LeaderboardEntry } from '@/types'

type SortKey = keyof LeaderboardEntry
type SortDir = 'asc' | 'desc'

const MEDAL_BORDER = ['border-l-4 border-yellow-400', 'border-l-4 border-gray-400', 'border-l-4 border-amber-700']

function epaColor(v: number | null): string {
  if (v == null) return 'text-gray-600'
  if (v >= 0.15) return 'text-green-700 font-semibold'
  if (v > 0) return 'text-green-600'
  if (v <= -0.15) return 'text-red-700 font-semibold'
  return 'text-red-600'
}

function fmt(v: number | null, decimals = 3, sign = false): string {
  if (v == null) return '—'
  const fixed = v.toFixed(decimals)
  return sign && v > 0 ? `+${fixed}` : fixed
}

interface ColDef {
  key: SortKey
  label: string
  align: 'left' | 'right'
  render: (row: LeaderboardEntry) => React.ReactNode
}

const COLUMNS: ColDef[] = [
  {
    key: 'rank',
    label: 'Rank',
    align: 'right',
    render: (r) => <span className="text-gray-500 font-medium">#{r.rank}</span>,
  },
  {
    key: 'qb_name',
    label: 'QB',
    align: 'left',
    render: (r) => <span className="font-medium text-gray-900">{r.qb_name ?? '—'}</span>,
  },
  {
    key: 'team',
    label: 'Team',
    align: 'left',
    render: (r) => <span className="text-gray-600 text-xs font-medium uppercase tracking-wide">{r.team ?? '—'}</span>,
  },
  {
    key: 'play_count',
    label: 'Plays',
    align: 'right',
    render: (r) => r.play_count?.toLocaleString() ?? '—',
  },
  {
    key: 'epa_per_play',
    label: 'EPA / Play',
    align: 'right',
    render: (r) => <span className={epaColor(r.epa_per_play)}>{fmt(r.epa_per_play, 3, true)}</span>,
  },
  {
    key: 'success_rate',
    label: 'Success%',
    align: 'right',
    render: (r) =>
      r.success_rate != null ? `${(r.success_rate * 100).toFixed(1)}%` : '—',
  },
  {
    key: 'pass_attempts',
    label: 'Pass Att',
    align: 'right',
    render: (r) => r.pass_attempts?.toLocaleString() ?? '—',
  },
  {
    key: 'sacks',
    label: 'Sacks',
    align: 'right',
    render: (r) => r.sacks?.toLocaleString() ?? '—',
  },
  {
    key: 'scrambles',
    label: 'Scrambles',
    align: 'right',
    render: (r) => r.scrambles?.toLocaleString() ?? '—',
  },
  {
    key: 'avg_cpoe',
    label: 'Avg CPOE',
    align: 'right',
    render: (r) => <span className={epaColor(r.avg_cpoe)}>{fmt(r.avg_cpoe, 2, true)}</span>,
  },
]

function SortIndicator({ active, dir }: { active: boolean; dir: SortDir }) {
  if (!active) return <span className="ml-1 text-gray-300">↕</span>
  return <span className="ml-1">{dir === 'desc' ? '↓' : '↑'}</span>
}

interface Props {
  entries: LeaderboardEntry[]
}

export default function LeaderboardTable({ entries }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>('epa_per_play')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  function handleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'))
    } else {
      setSortKey(key)
      setSortDir(key === 'qb_name' || key === 'team' ? 'asc' : 'desc')
    }
  }

  const sorted = [...entries].sort((a, b) => {
    const av = a[sortKey]
    const bv = b[sortKey]
    if (av == null && bv == null) return 0
    if (av == null) return 1
    if (bv == null) return -1
    if (typeof av === 'string' && typeof bv === 'string') {
      const cmp = av.localeCompare(bv)
      return sortDir === 'asc' ? cmp : -cmp
    }
    const cmp = (av as number) - (bv as number)
    return sortDir === 'asc' ? cmp : -cmp
  })

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm">
      <table className="min-w-full text-sm">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            {COLUMNS.map((col) => (
              <th
                key={col.key}
                onClick={() => handleSort(col.key)}
                className={`px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide cursor-pointer select-none hover:bg-gray-100 transition-colors ${
                  col.align === 'right' ? 'text-right' : 'text-left'
                }`}
              >
                {col.label}
                <SortIndicator active={sortKey === col.key} dir={sortDir} />
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-100">
          {sorted.map((row, i) => (
            <tr
              key={row.qb_id}
              className={`hover:bg-gray-50 transition-colors ${MEDAL_BORDER[i] ?? ''}`}
            >
              {COLUMNS.map((col) => (
                <td
                  key={col.key}
                  className={`px-4 py-3 text-gray-700 ${col.align === 'right' ? 'text-right tabular-nums' : 'text-left'}`}
                >
                  {col.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
