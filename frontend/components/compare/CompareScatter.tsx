'use client'

import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
  LabelList,
} from 'recharts'
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

interface TooltipPayload {
  payload: {
    matchup: string
    x: number
    y: number
    sr: number
  }
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: TooltipPayload[] }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div style={{ backgroundColor: '#fff', border: '1px solid #e5e7eb', borderRadius: 6, padding: '8px 12px', fontSize: 12, color: '#111827' }}>
      <p style={{ fontWeight: 600, marginBottom: 4 }}>{d.matchup}</p>
      <p style={{ margin: '2px 0' }}>Plays: {d.x}</p>
      <p style={{ margin: '2px 0' }}>EPA/Play: {d.y >= 0 ? '+' : ''}{d.y.toFixed(3)}</p>
      <p style={{ margin: '2px 0' }}>SR: {(d.sr * 100).toFixed(1)}%</p>
    </div>
  )
}

export default function CompareScatter({ rows, nameA, nameB, sameQB, seasonA, seasonB }: Props) {
  const legendA = sameQB ? `${nameA} ${seasonA}` : nameA
  const legendB = sameQB ? `${nameB} ${seasonB}` : nameB

  const dataA = rows.map((r) => ({ matchup: r.matchup, x: r.aPlays, y: r.aEpa, sr: r.aSR }))
  const dataB = rows.map((r) => ({ matchup: r.matchup, x: r.bPlays, y: r.bEpa, sr: r.bSR }))

  const sortedPlaysA = [...dataA].map((d) => d.x).sort((a, b) => a - b)
  const median = sortedPlaysA.length > 0 ? sortedPlaysA[Math.floor(sortedPlaysA.length / 2)] : 0

  const sortedPlaysB = [...dataB].map((d) => d.x).sort((a, b) => a - b)
  const medianB = sortedPlaysB.length > 0 ? sortedPlaysB[Math.floor(sortedPlaysB.length / 2)] : 0

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm min-h-[400px]">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">Volume vs EPA/Play — Shared Matchups</h3>
      <ResponsiveContainer width="100%" height={350}>
        <ScatterChart margin={{ top: 20, right: 40, bottom: 40, left: 40 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            type="number"
            dataKey="x"
            name="Plays"
            label={{ value: 'Play Volume', position: 'insideBottom', offset: -10, fontSize: 12 }}
            tick={{ fontSize: 11 }}
          />
          <YAxis
            dataKey="y"
            name="EPA/Play"
            label={{ value: 'EPA/Play', angle: -90, position: 'insideLeft', fontSize: 12 }}
            tick={{ fontSize: 11 }}
            tickFormatter={(v: number) => v.toFixed(2)}
          />
          <ReferenceLine y={0} stroke="#9ca3af" strokeDasharray="4 4" />
          <Tooltip content={<CustomTooltip />} />
          <Legend verticalAlign="top" wrapperStyle={{ fontSize: 11, paddingBottom: 8 }} />
          <Scatter name={legendA} data={dataA} fill="#3b82f6" fillOpacity={0.8}>
            <LabelList
              dataKey="matchup"
              position="top"
              content={(props) => {
                const { x, y, value, index } = props as { x?: number; y?: number; value?: string; index?: number }
                if (index == null || dataA[index]?.x <= median) return null
                return (
                  <text x={x} y={(y ?? 0) - 6} textAnchor="middle" fontSize={11} fill="#374151">
                    {value}
                  </text>
                )
              }}
            />
          </Scatter>
          <Scatter name={legendB} data={dataB} fill="#f97316" fillOpacity={0.8}>
            <LabelList
              dataKey="matchup"
              position="top"
              content={(props) => {
                const { x, y, value, index } = props as { x?: number; y?: number; value?: string; index?: number }
                if (index == null || dataB[index]?.x <= medianB) return null
                return (
                  <text x={x} y={(y ?? 0) - 6} textAnchor="middle" fontSize={11} fill="#374151">
                    {value}
                  </text>
                )
              }}
            />
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  )
}