'use client'

import { useState } from 'react'
import type { CompareRow } from './ComparePanel'
import type { Season } from '@/components/dashboard/SeasonFilter'

interface Props {
  rows: CompareRow[]
  nameA: string
  nameB: string
  sameQB: boolean
  seasonA: Season
  seasonB: Season
}

type SortKey = 'matchup' | 'aPlays' | 'aEpa' | 'aSR' | 'bPlays' | 'bEpa' | 'bSR' | 'epaDiff'

function lastName(name: string): string {
  const dot = name.indexOf('.')
  return dot === -1 ? name : name.substring(dot + 1)
}

function fmt(n: number | null | undefined, decimals = 3, sign = false): string {
  if (n == null) return '—'
  const fixed = n.toFixed(decimals)
  return sign && n > 0 ? `+${fixed}` : fixed
}

export default function CompareTable({ rows, nameA, nameB, sameQB, seasonA, seasonB }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>('aPlays')
  const [sortAsc, setSortAsc] = useState(false)

  const labelA = sameQB ? seasonA : nameA
  const labelB = sameQB ? seasonB : nameB

  function toggleSort(key: SortKey) {
    if (key === sortKey) setSortAsc((v) => !v)
    else { setSortKey(key); setSortAsc(false) }
  }

  const sorted = [...rows].sort((a, b) => {
    let av: string | number
    let bv: string | number
    if (sortKey === 'matchup') { av = a.matchup; bv = b.matchup }
    else if (sortKey === 'epaDiff') { av = a.aEpa - a.bEpa; bv = b.aEpa - b.bEpa }
    else { av = a[sortKey] as number; bv = b[sortKey] as number }

    if (typeof av === 'string') return sortAsc ? av.localeCompare(bv as string) : (bv as string).localeCompare(av)
    return sortAsc ? av - (bv as number) : (bv as number) - av
  })

  function winner(r: CompareRow): string {
    if (r.aEpa === r.bEpa) return '—'
    if (sameQB) return r.aEpa > r.bEpa ? seasonA : seasonB
    return r.aEpa > r.bEpa ? nameA : nameB
  }

  type ColDef = { key: SortKey; label: string }
  const shortA = sameQB ? labelA : lastName(labelA)
  const shortB = sameQB ? labelB : lastName(labelB)

  const cols: ColDef[] = [
    { key: 'matchup', label: 'Matchup' },
    { key: 'aPlays', label: `${shortA} Plays` },
    { key: 'aEpa', label: `${shortA} EPA/Play` },
    { key: 'aSR', label: `${shortA} SR%` },
    { key: 'bPlays', label: `${shortB} Plays` },
    { key: 'bEpa', label: `${shortB} EPA/Play` },
    { key: 'bSR', label: `${shortB} SR%` },
    { key: 'epaDiff', label: 'EPA Diff' },
  ]

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-100">
        <h3 className="text-sm font-semibold text-gray-700">Matchup Breakdown</h3>
        <p className="text-xs text-gray-500 mt-0.5">{rows.length} shared matchups</p>
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
              <th className="px-4 py-2 text-left text-xs uppercase tracking-wide whitespace-nowrap">Winner</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {sorted.map((r, i) => {
              const diff = r.aEpa - r.bEpa
              const aWins = r.aEpa > r.bEpa
              return (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-4 py-2 font-medium text-gray-900 whitespace-nowrap">{r.matchup}</td>
                  <td className="px-4 py-2 tabular-nums text-gray-900">{r.aPlays}</td>
                  <td className={`px-4 py-2 tabular-nums font-medium ${r.aEpa >= 0 ? 'text-green-700' : 'text-red-600'}`}>
                    {fmt(r.aEpa, 3, true)}
                  </td>
                  <td className="px-4 py-2 tabular-nums text-gray-900">{(r.aSR * 100).toFixed(1)}%</td>
                  <td className="px-4 py-2 tabular-nums text-gray-900">{r.bPlays}</td>
                  <td className={`px-4 py-2 tabular-nums font-medium ${r.bEpa >= 0 ? 'text-green-700' : 'text-red-600'}`}>
                    {fmt(r.bEpa, 3, true)}
                  </td>
                  <td className="px-4 py-2 tabular-nums text-gray-900">{(r.bSR * 100).toFixed(1)}%</td>
                  <td className={`px-4 py-2 tabular-nums font-medium ${diff > 0 ? 'text-green-700' : diff < 0 ? 'text-red-600' : 'text-gray-500'}`}>
                    {fmt(diff, 3, true)}
                  </td>
                  <td className="px-4 py-2 whitespace-nowrap">
                    <span className={`text-xs font-medium px-1.5 py-0.5 rounded border ${
                      aWins
                        ? 'bg-blue-50 text-blue-700 border-blue-200'
                        : r.aEpa === r.bEpa
                        ? 'bg-gray-50 text-gray-500 border-gray-200'
                        : 'bg-orange-50 text-orange-700 border-orange-200'
                    }`}>
                      {winner(r)}
                    </span>
                  </td>
                </tr>
              )
            })}
            {rows.length === 0 && (
              <tr>
                <td colSpan={9} className="px-4 py-8 text-center text-gray-500">
                  No shared matchups meet the minimum play threshold
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}