'use client'

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import type { QBStats } from '@/types'

interface Props {
  stats: QBStats[]
  minPlays: number
}

const OFFENSE_COLORS: Record<string, string> = {
  '10': '#3b82f6',
  '11': '#6366f1',
  '12': '#8b5cf6',
  '13': '#a855f7',
  '20': '#ec4899',
  '21': '#f43f5e',
  '22': '#ef4444',
}

function colorFor(matchup: string): string {
  const offense = matchup.split(' vs')[0]?.trim() ?? ''
  return OFFENSE_COLORS[offense] ?? '#64748b'
}

export default function TopMatchups({ stats, minPlays }: Props) {
  // Deduplicate by matchup name (Career view has one row per season × matchup),
  // keeping the row with the highest play_count for each matchup.
  const byMatchup = new Map<string, QBStats>()
  for (const r of stats) {
    const key = r.personnel_matchup ?? ''
    const prev = byMatchup.get(key)
    if (!prev || (r.play_count ?? 0) > (prev.play_count ?? 0)) {
      byMatchup.set(key, r)
    }
  }

  const top5 = Array.from(byMatchup.values())
    .filter((r) => (r.play_count ?? 0) >= Math.max(minPlays, 20) && r.epa_per_play != null)
    .sort((a, b) => (b.epa_per_play ?? 0) - (a.epa_per_play ?? 0))
    .slice(0, 5)
    .map((r) => ({
      matchup: r.personnel_matchup ?? '',
      epa: r.epa_per_play!,
    }))

  if (top5.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm flex items-center justify-center h-64 text-gray-500 text-sm">
        No matchups meet the minimum play threshold
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">Top 5 Matchups by EPA/Play</h3>
      <div className="h-[250px] sm:h-[350px]">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={top5}
          layout="vertical"
          margin={{ top: 20, right: 60, bottom: 60, left: 60 }}
        >
          <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f0f0f0" />
          <XAxis
            type="number"
            tick={{ fontSize: 11 }}
            tickFormatter={(v: number) => v.toFixed(2)}
            label={{ value: 'EPA / Play', position: 'insideBottom', offset: -10, fontSize: 12 }}
          />
          <YAxis
            dataKey="matchup"
            type="category"
            tick={{ fontSize: 11 }}
            width={110}
          />
          <ReferenceLine x={0} stroke="#9ca3af" />
          <Tooltip formatter={(v) => (typeof v === 'number' ? v.toFixed(3) : v)} />
          <Bar dataKey="epa" name="EPA/Play" radius={[0, 4, 4, 0]}>
            {top5.map((entry, i) => (
              <Cell key={i} fill={colorFor(entry.matchup)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      </div>
    </div>
  )
}
