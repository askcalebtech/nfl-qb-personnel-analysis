'use client'

import { useState } from 'react'
import type { QBStats } from '@/types'

interface Props {
  stats: QBStats[]
  minPlays: number
}

type SortKey = 'personnel_matchup' | 'season' | 'play_count' | 'epa_per_play' | 'success_rate' | 'pass_attempts' | 'sacks' | 'scrambles' | 'avg_cpoe'

const PAGE_SIZE = 10

function fmt(n: number | null | undefined, decimals = 3, sign = false): string {
  if (n == null) return '—'
  const fixed = n.toFixed(decimals)
  return sign && n > 0 ? `+${fixed}` : fixed
}

export default function MatchupTable({ stats, minPlays }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>('play_count')
  const [sortAsc, setSortAsc] = useState(false)
  const [page, setPage] = useState(0)

  const filtered = stats.filter((r) => (r.play_count ?? 0) >= minPlays)

  const sorted = [...filtered].sort((a, b) => {
    const av = a[sortKey] as string | number | null
    const bv = b[sortKey] as string | number | null
    if (av == null && bv == null) return 0
    if (av == null) return 1
    if (bv == null) return -1
    if (typeof av === 'string') return sortAsc ? av.localeCompare(bv as string) : (bv as string).localeCompare(av)
    return sortAsc ? av - (bv as number) : (bv as number) - av
  })

  const totalPages = Math.ceil(sorted.length / PAGE_SIZE)
  const page_rows = sorted.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setSortAsc((v) => !v)
    } else {
      setSortKey(key)
      setSortAsc(false)
    }
    setPage(0)
  }

  const cols: { key: SortKey; label: string }[] = [
    { key: 'personnel_matchup', label: 'Matchup' },
    { key: 'season', label: 'Season' },
    { key: 'play_count', label: 'Plays' },
    { key: 'epa_per_play', label: 'EPA/Play' },
    { key: 'success_rate', label: 'Success%' },
    { key: 'pass_attempts', label: 'Pass Att' },
    { key: 'sacks', label: 'Sacks' },
    { key: 'scrambles', label: 'Scrambles' },
    { key: 'avg_cpoe', label: 'Avg CPOE' },
  ]

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-100">
        <h3 className="text-sm font-semibold text-gray-700">All Matchups</h3>
        <p className="text-xs text-gray-500 mt-0.5">{filtered.length} matchups · {PAGE_SIZE}/page</p>
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
                  {sortKey === key && (
                    <span className="ml-1">{sortAsc ? '↑' : '↓'}</span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {page_rows.map((r, i) => (
              <tr
                key={i}
                className="hover:bg-gray-50"
              >
                <td className="px-4 py-2 font-medium text-gray-900 whitespace-nowrap">
                  {r.personnel_matchup ?? '—'}
                  {r.meets_starter_threshold && (
                    <span className="ml-2 inline-block w-1.5 h-1.5 rounded-full bg-green-500 align-middle" />
                  )}
                </td>
                <td className="px-4 py-2 tabular-nums text-gray-900">{r.season ?? '—'}</td>
                <td className="px-4 py-2 tabular-nums text-gray-900">{r.play_count ?? '—'}</td>
                <td className={`px-4 py-2 tabular-nums font-medium ${(r.epa_per_play ?? 0) >= 0 ? 'text-green-700' : 'text-red-600'}`}>
                  {fmt(r.epa_per_play, 3, true)}
                </td>
                <td className="px-4 py-2 tabular-nums text-gray-900">
                  {r.success_rate != null ? `${(r.success_rate * 100).toFixed(1)}%` : '—'}
                </td>
                <td className="px-4 py-2 tabular-nums text-gray-900">{r.pass_attempts ?? '—'}</td>
                <td className="px-4 py-2 tabular-nums text-gray-900">{r.sacks ?? '—'}</td>
                <td className="px-4 py-2 tabular-nums text-gray-900">{r.scrambles ?? '—'}</td>
                <td className="px-4 py-2 tabular-nums text-gray-900">{fmt(r.avg_cpoe, 2, true)}</td>
              </tr>
            ))}
            {page_rows.length === 0 && (
              <tr>
                <td colSpan={9} className="px-4 py-8 text-center text-gray-500">
                  No matchups meet the minimum play threshold
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {totalPages > 1 && (
        <div className="px-4 py-3 border-t border-gray-100 flex items-center justify-between text-xs text-gray-500">
          <span>Page {page + 1} of {totalPages}</span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="px-2 py-1 rounded border border-gray-200 disabled:opacity-40 hover:bg-gray-50"
            >
              Prev
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page === totalPages - 1}
              className="px-2 py-1 rounded border border-gray-200 disabled:opacity-40 hover:bg-gray-50"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
