'use client'

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import type { CompareRow } from './ComparePanel'

interface Props {
  rows: CompareRow[]
  nameA: string
  nameB: string
}

interface TooltipEntry {
  name: string
  value: number
  color: string
}

function CustomTooltip({ active, payload, label }: { active?: boolean; payload?: TooltipEntry[]; label?: string }) {
  if (!active || !payload?.length) return null
  return (
    <div style={{ backgroundColor: '#fff', border: '1px solid #e5e7eb', borderRadius: 6, padding: '8px 12px', fontSize: 12, color: '#111827' }}>
      <p style={{ fontWeight: 600, marginBottom: 4 }}>{label}</p>
      {payload.map((entry) => (
        <p key={entry.name} style={{ color: '#111827', margin: '2px 0' }}>
          <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: 2, backgroundColor: entry.color, marginRight: 6 }} />
          {entry.name}: {entry.value >= 0 ? '+' : ''}{entry.value.toFixed(3)}
        </p>
      ))}
    </div>
  )
}

export default function CompareBarChart({ rows, nameA, nameB }: Props) {
  const sorted = [...rows].sort((a, b) => b.aEpa - a.aEpa)

  const chartData = sorted.map((r) => ({
    matchup: r.matchup,
    [nameA]: Number(r.aEpa.toFixed(4)),
    [nameB]: Number(r.bEpa.toFixed(4)),
  }))

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm min-h-[400px]">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">EPA / Play by Matchup</h3>
      <ResponsiveContainer width="100%" height={350}>
        <BarChart
          layout="vertical"
          data={chartData}
          margin={{ top: 20, right: 40, bottom: 40, left: 40 }}
          barCategoryGap="30%"
          barGap={2}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
          <XAxis
            type="number"
            tick={{ fontSize: 10 }}
            tickFormatter={(v: number) => v.toFixed(2)}
            domain={['auto', 'auto']}
            label={{ value: 'EPA / Play', position: 'insideBottom', offset: -10, fontSize: 12 }}
          />
          <YAxis
            type="category"
            dataKey="matchup"
            tick={{ fontSize: 11 }}
            width={105}
          />
          <ReferenceLine x={0} stroke="#9ca3af" strokeDasharray="4 4" />
          <Tooltip content={<CustomTooltip />} />
          <Legend verticalAlign="top" wrapperStyle={{ fontSize: 11, paddingBottom: 8 }} />
          <Bar dataKey={nameA} fill="#3b82f6" radius={[0, 2, 2, 0]} />
          <Bar dataKey={nameB} fill="#f97316" radius={[0, 2, 2, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}