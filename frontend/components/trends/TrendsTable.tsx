'use client'

import { useState } from 'react'
import type { LeagueTrend } from '@/types'

interface Props {
  trends: LeagueTrend[]
}

type SortKey =
  | 'personnel_matchup'
  | 'season'
  | 'usage_pct'
  | 'league_epa_per_play'
  | 'qbs_used_matchup'
  | 'league_pass_rate'
  | 'usage_pct_change_yoy'

function fmt(n: number | null | undefined, decimals = 3, sign = false): string {
  if (n == null) return '—'
  const fixed = n.toFixed(decimals)
  return sign && n > 0 ? `+${fixed}` : fixed
}

function YoYBadge({ value }: { value: number | null | undefined }) {
  if (value == null) return <span className="text-gray-500">—</span>
  const pct = value.toFixed(1)
  if (value > 0.05)
    return <span className="text-green-700 font-medium">+{pct}%</span>
  if (value < -0.05)
    return <span className="text-red-600 font-medium">{pct}%</span>
  return <span className="text-gray-500">~0%</span>
}

export default function TrendsTable({ trends }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>('usage_pct')
  const [sortAsc, setSortAsc] = useState(false)

  const sorted = [...trends].sort((a, b) => {
    const av = a[sortKey] as string | number | null
    const bv = b[sortKey] as string | number | null
    if (av == null && bv == null) return 0
    if (av == null) return 1
    if (bv == null) return -1
    if (typeof av === 'string')
      return sortAsc ? av.localeCompare(bv as string) : (bv as string).localeCompare(av)
    return sortAsc ? av - (bv as number) : (bv as number) - av
  })

  function toggleSort(key: SortKey) {
    if (key === sortKey) setSortAsc((v) => !v)
    else { setSortKey(key); setSortAsc(false) }
  }

  const cols: { key: SortKey; label: string }[] = [
    { key: 'personnel_matchup', label: 'Matchup' },
    { key: 'season', label: 'Season' },
    { key: 'usage_pct', label: 'Usage %' },
    { key: 'league_epa_per_play', label: 'League EPA/Play' },
    { key: 'qbs_used_matchup', label: '# QBs' },
    { key: 'league_pass_rate', label: 'Pass Rate' },
    { key: 'usage_pct_change_yoy', label: 'YoY Usage Change' },
  ]

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-100">
        <h3 className="text-sm font-semibold text-gray-700">Personnel Matchup Trends</h3>
        <p className="text-xs text-gray-500 mt-0.5">{trends.length} rows</p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-gray-600 text-xs uppercase tracking-wide">
              {cols.map(({ key, label }) => (
                <th
                  key={key}
                  onClick={() => toggleSort(key)}
                  className="px-4 py-2 text-left cursor-pointer select-none hover:bg-gray-100 whitespace-nowrap"
                >
                  {label}
                  {sortKey === key && <span className="ml-1">{sortAsc ? '↑' : '↓'}</span>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {sorted.map((r, i) => (
              <tr key={i} className="hover:bg-gray-50">
                <td className="px-4 py-2 font-medium text-gray-900 whitespace-nowrap">
                  {r.personnel_matchup ?? '—'}
                </td>
                <td className="px-4 py-2 tabular-nums text-gray-900">{r.season ?? '—'}</td>
                <td className="px-4 py-2 tabular-nums text-gray-900">
                  {r.usage_pct != null ? `${r.usage_pct.toFixed(1)}%` : '—'}
                </td>
                <td className={`px-4 py-2 tabular-nums font-medium ${(r.league_epa_per_play ?? 0) >= 0 ? 'text-green-700' : 'text-red-600'}`}>
                  {fmt(r.league_epa_per_play, 3, true)}
                </td>
                <td className="px-4 py-2 tabular-nums text-gray-900">{r.qbs_used_matchup ?? '—'}</td>
                <td className="px-4 py-2 tabular-nums text-gray-900">
                  {r.league_pass_rate != null ? `${(r.league_pass_rate * 100).toFixed(1)}%` : '—'}
                </td>
                <td className="px-4 py-2">
                  <YoYBadge value={r.usage_pct_change_yoy} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
