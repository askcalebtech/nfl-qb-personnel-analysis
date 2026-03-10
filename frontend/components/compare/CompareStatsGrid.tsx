'use client'

import type { QBStats } from '@/types'

interface Props {
  filteredA: QBStats[]
  filteredB: QBStats[]
  nameA: string
  nameB: string
  sameQB: boolean
  seasonA: string
  seasonB: string
}

function summarize(rows: QBStats[]) {
  const plays = rows.reduce((s, r) => s + (r.play_count ?? 0), 0)
  const passAtt = rows.reduce((s, r) => s + (r.pass_attempts ?? 0), 0)
  if (plays === 0) return { plays, epa: null, sr: null, passAtt }
  const epa = rows.reduce((s, r) => s + (r.epa_per_play ?? 0) * (r.play_count ?? 0), 0) / plays
  const sr = rows.reduce((s, r) => s + (r.success_rate ?? 0) * (r.play_count ?? 0), 0) / plays
  return { plays, epa, sr, passAtt }
}

function fmt(n: number | null | undefined, decimals = 3, sign = false): string {
  if (n == null) return '—'
  const fixed = n.toFixed(decimals)
  return sign && n > 0 ? `+${fixed}` : fixed
}

export default function CompareStatsGrid({ filteredA, filteredB, nameA, nameB, sameQB, seasonA, seasonB }: Props) {
  const a = summarize(filteredA)
  const b = summarize(filteredB)

  const labelA = sameQB ? seasonA : nameA
  const labelB = sameQB ? seasonB : nameB

  const cards = [
    {
      label: 'Total Plays',
      aVal: a.plays.toLocaleString(),
      bVal: b.plays.toLocaleString(),
      aLeads: a.plays >= b.plays,
    },
    {
      label: 'EPA / Play',
      aVal: fmt(a.epa, 3, true),
      bVal: fmt(b.epa, 3, true),
      aLeads: (a.epa ?? -Infinity) >= (b.epa ?? -Infinity),
    },
    {
      label: 'Success Rate',
      aVal: a.sr != null ? `${(a.sr * 100).toFixed(1)}%` : '—',
      bVal: b.sr != null ? `${(b.sr * 100).toFixed(1)}%` : '—',
      aLeads: (a.sr ?? -Infinity) >= (b.sr ?? -Infinity),
    },
    {
      label: 'Pass Attempts',
      aVal: a.passAtt.toLocaleString(),
      bVal: b.passAtt.toLocaleString(),
      aLeads: a.passAtt >= b.passAtt,
    },
  ]

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      {cards.map(({ label, aVal, bVal, aLeads }) => (
        <div key={label} className="bg-white rounded-lg border border-gray-200 p-3 shadow-sm">
          <p className="text-xs text-gray-500 uppercase tracking-wide font-medium mb-2">{label}</p>
          <div className="space-y-1">
            <div className={`flex items-center justify-between rounded px-2 py-1 ${aLeads ? 'bg-green-50' : 'bg-gray-50'}`}>
              <span className="text-xs text-gray-500 truncate mr-1">{labelA}</span>
              <span className={`text-sm font-bold tabular-nums ${aLeads ? 'text-green-700' : 'text-gray-700'}`}>{aVal}</span>
            </div>
            <div className={`flex items-center justify-between rounded px-2 py-1 ${!aLeads ? 'bg-green-50' : 'bg-gray-50'}`}>
              <span className="text-xs text-gray-500 truncate mr-1">{labelB}</span>
              <span className={`text-sm font-bold tabular-nums ${!aLeads ? 'text-green-700' : 'text-gray-700'}`}>{bVal}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}