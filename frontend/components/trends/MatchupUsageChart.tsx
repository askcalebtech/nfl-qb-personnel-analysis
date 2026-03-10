'use client'

import { useState } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import type { LeagueTrend } from '@/types'

interface Props {
  trends: LeagueTrend[]
}

const COLORS = ['#6366f1', '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']

interface TooltipEntry {
  name: string
  value: number
  color: string
}

function CustomTooltip({ active, payload, label }: { active?: boolean; payload?: TooltipEntry[]; label?: string }) {
  if (!active || !payload?.length) return null
  const sorted = [...payload].sort((a, b) => b.value - a.value)
  return (
    <div style={{ backgroundColor: '#fff', border: '1px solid #e5e7eb', borderRadius: 6, padding: '8px 12px', fontSize: 12, color: '#111827' }}>
      <p style={{ fontWeight: 600, marginBottom: 4, color: '#111827' }}>{label}</p>
      {sorted.map((entry) => (
        <p key={entry.name} style={{ color: '#111827', margin: '2px 0' }}>
          <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', backgroundColor: entry.color, marginRight: 6 }} />
          {entry.name}: {entry.value}%
        </p>
      ))}
    </div>
  )
}

interface LegendEntry {
  value: string
  color: string
}

interface CustomLegendProps {
  payload?: LegendEntry[]
  hiddenMatchups: Set<string>
  onToggle: (name: string) => void
}

function CustomLegend({ payload, hiddenMatchups, onToggle }: CustomLegendProps) {
  if (!payload) return null
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px 16px', justifyContent: 'center', fontSize: 11, paddingTop: 8, color: '#111827' }}>
      {payload.map((entry) => {
        const hidden = hiddenMatchups.has(entry.value)
        return (
          <span
            key={entry.value}
            onClick={() => onToggle(entry.value)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 5,
              cursor: 'pointer',
              color: '#111827',
              opacity: hidden ? 0.4 : 1,
              textDecoration: hidden ? 'line-through' : 'none',
              userSelect: 'none',
            }}
          >
            <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', backgroundColor: entry.color, flexShrink: 0 }} />
            {entry.value}
          </span>
        )
      })}
    </div>
  )
}

export default function MatchupUsageChart({ trends }: Props) {
  const [hiddenMatchups, setHiddenMatchups] = useState<Set<string>>(new Set())

  function toggle(name: string) {
    setHiddenMatchups((prev) => {
      const next = new Set(prev)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      return next
    })
  }

  // Find top 6 matchups by total play volume across all seasons
  const volumeByMatchup: Record<string, number> = {}
  for (const row of trends) {
    if (row.personnel_matchup) {
      volumeByMatchup[row.personnel_matchup] =
        (volumeByMatchup[row.personnel_matchup] ?? 0) + (row.league_play_count ?? 0)
    }
  }
  const top6 = Object.entries(volumeByMatchup)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
    .map(([m]) => m)

  // Pivot: one row per season with each matchup's usage_pct as a key
  const seasons = Array.from(new Set(trends.map((r) => r.season).filter(Boolean))).sort() as string[]
  const chartData = seasons.map((season) => {
    const row: Record<string, string | number> = { season }
    for (const matchup of top6) {
      const found = trends.find((r) => r.season === season && r.personnel_matchup === matchup)
      row[matchup] = found?.usage_pct != null ? Number(found.usage_pct.toFixed(1)) : 0
    }
    return row
  })

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">
        Personnel Usage % Over Time — Top 6 Matchups
      </h3>
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={chartData} margin={{ top: 10, right: 20, bottom: 10, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="season" tick={{ fontSize: 11 }} />
          <YAxis
            tickFormatter={(v: number) => `${v}%`}
            tick={{ fontSize: 11 }}
            domain={[0, 'auto']}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{ color: '#111827' }}
            content={(props) => (
              <CustomLegend
                payload={props.payload as LegendEntry[]}
                hiddenMatchups={hiddenMatchups}
                onToggle={toggle}
              />
            )}
          />
          {top6.map((matchup, i) => (
            <Line
              key={matchup}
              type="monotone"
              dataKey={matchup}
              stroke={COLORS[i % COLORS.length]}
              strokeWidth={2}
              dot={{ r: 4, style: { cursor: 'pointer' } }}
              activeDot={{ r: 6, style: { cursor: 'pointer' }, onClick: () => toggle(matchup) }}
              hide={hiddenMatchups.has(matchup)}
              onClick={() => toggle(matchup)}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
