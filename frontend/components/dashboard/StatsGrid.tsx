'use client'

import { useEffect, useState } from 'react'
import type { QB, QBStats, QBRanking } from '@/types'
import type { Season } from '@/components/dashboard/SeasonFilter'
import { getRankings } from '@/lib/api'

interface Props {
  stats: QBStats[]
  qbs: QB[]
  selectedId: string
  season: Season
}

function fmt(n: number | null | undefined, decimals = 3, sign = false): string {
  if (n == null) return '—'
  const fixed = n.toFixed(decimals)
  return sign && n > 0 ? `+${fixed}` : fixed
}

function weightedAvg(rows: QBStats[], field: keyof QBStats): number | null {
  const totalPlays = rows.reduce((s, r) => s + (r.play_count ?? 0), 0)
  if (totalPlays === 0) return null
  const sum = rows.reduce((s, r) => {
    const v = r[field] as number | null
    return s + (v ?? 0) * (r.play_count ?? 0)
  }, 0)
  return sum / totalPlays
}

function rankInPool<T extends { qb_id: string; is_starter: boolean | null }>(
  pool: T[],
  selectedId: string,
  getValue: (q: T) => number | null,
): { rank: number; total: number } | null {
  const starters = pool.filter((q) => q.is_starter)
  const sorted = [...starters]
    .filter((q) => getValue(q) != null)
    .sort((a, b) => (getValue(b) as number) - (getValue(a) as number))
  const idx = sorted.findIndex((q) => q.qb_id === selectedId)
  if (idx === -1) return null
  return { rank: idx + 1, total: starters.length }
}

function RankBadge({ info }: { info: { rank: number; total: number } | null }) {
  if (!info) return null
  const color =
    info.rank <= Math.ceil(info.total * 0.25)
      ? 'bg-green-50 text-green-700 border-green-200'
      : info.rank <= Math.ceil(info.total * 0.5)
        ? 'bg-blue-50 text-blue-700 border-blue-200'
        : 'bg-gray-50 text-gray-500 border-gray-200'
  return (
    <span className={`text-xs font-medium px-1.5 py-0.5 rounded border ${color}`}>
      #{info.rank} of {info.total}
    </span>
  )
}

export default function StatsGrid({ stats, qbs, selectedId, season }: Props) {
  const [seasonRankings, setSeasonRankings] = useState<QBRanking[] | null>(null)

  useEffect(() => {
    if (season === '2022–25') {
      setSeasonRankings(null)
      return
    }
    getRankings(season)
      .then(setSeasonRankings)
      .catch(() => setSeasonRankings(null))
  }, [season])

  const totalPlays = stats.reduce((s, r) => s + (r.play_count ?? 0), 0)
  const epa = weightedAvg(stats, 'epa_per_play')
  const sr = weightedAvg(stats, 'success_rate')
  const passAttempts = stats.reduce((s, r) => s + (r.pass_attempts ?? 0), 0)

  const ranks =
    season === '2022–25' || seasonRankings === null
      ? {
          plays: rankInPool(qbs, selectedId, (q) => q.career_plays),
          epa: rankInPool(qbs, selectedId, (q) => q.career_epa_per_play),
          sr: rankInPool(qbs, selectedId, (q) => q.career_success_rate),
          passAttempts: rankInPool(qbs, selectedId, (q) => q.career_pass_attempts),
        }
      : {
          plays: rankInPool(seasonRankings, selectedId, (q) => q.total_plays),
          epa: rankInPool(seasonRankings, selectedId, (q) => q.epa_per_play),
          sr: rankInPool(seasonRankings, selectedId, (q) => q.success_rate),
          passAttempts: rankInPool(seasonRankings, selectedId, (q) => q.pass_attempts),
        }

  const cards = [
    { label: 'Total Plays', value: totalPlays.toLocaleString(), rank: ranks.plays },
    { label: 'EPA / Play', value: fmt(epa, 3, true), rank: ranks.epa },
    { label: 'Success Rate', value: sr != null ? `${(sr * 100).toFixed(1)}%` : '—', rank: ranks.sr },
    { label: 'Pass Attempts', value: passAttempts.toLocaleString(), rank: ranks.passAttempts },
  ]

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
      {cards.map(({ label, value, rank }) => (
        <div key={label} className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
          <div className="flex items-start justify-between gap-2">
            <p className="text-xs text-gray-500 uppercase tracking-wide font-medium">{label}</p>
            {rank && <RankBadge info={rank} />}
          </div>
          <p className="mt-1 text-2xl font-bold text-gray-900">{value}</p>
        </div>
      ))}
    </div>
  )
}
