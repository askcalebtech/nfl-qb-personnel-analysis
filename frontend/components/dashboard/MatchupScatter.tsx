'use client'

import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Cell,
  LabelList,
} from 'recharts'
import type { QBStats } from '@/types'
import type { Season } from '@/components/dashboard/SeasonFilter'

interface Props {
  stats: QBStats[]
  season: Season
}

interface TooltipPayload {
  payload: {
    matchup: string
    season: string
    play_count: number
    epa_per_play: number
    success_rate: number
  }
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: TooltipPayload[] }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="bg-white border border-gray-200 rounded shadow p-3 text-sm text-gray-900">
      <p className="font-semibold mb-1">{d.matchup}</p>
      <p className="text-gray-600 text-xs mb-1">{d.season}</p>
      <p>Plays: {d.play_count}</p>
      <p>EPA/Play: {d.epa_per_play >= 0 ? '+' : ''}{d.epa_per_play.toFixed(3)}</p>
      <p>Success Rate: {(d.success_rate * 100).toFixed(1)}%</p>
    </div>
  )
}

export default function MatchupScatter({ stats, season }: Props) {
  const allSeasons = season === '2022–25'

  // Build raw filtered points
  const raw = stats
    .filter((r) => r.play_count != null && r.epa_per_play != null)
    .map((r) => ({
      matchup: r.personnel_matchup ?? '',
      season: r.season ?? '',
      play_count: r.play_count!,
      epa_per_play: r.epa_per_play!,
      success_rate: r.success_rate ?? 0,
    }))

  // In all-seasons mode, aggregate by matchup (weighted avg) then apply threshold
  const data = allSeasons
    ? (() => {
        const grouped: Record<string, { play_count: number; epa_sum: number; sr_sum: number }> = {}
        for (const d of raw) {
          if (!grouped[d.matchup]) grouped[d.matchup] = { play_count: 0, epa_sum: 0, sr_sum: 0 }
          grouped[d.matchup].play_count += d.play_count
          grouped[d.matchup].epa_sum += d.epa_per_play * d.play_count
          grouped[d.matchup].sr_sum += d.success_rate * d.play_count
        }
        return Object.entries(grouped)
          .filter(([, g]) => g.play_count >= 50)
          .map(([matchup, g]) => ({
            matchup,
            season: '2022–25',
            play_count: g.play_count,
            epa_per_play: g.epa_sum / g.play_count,
            success_rate: g.sr_sum / g.play_count,
          }))
      })()
    : raw.filter((r) => r.play_count >= 20)

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500 text-sm">
        No data for this selection
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm min-h-[400px]">
      <h3 className="text-sm font-semibold text-gray-700">Matchup Efficiency — Volume vs EPA/Play</h3>
      {allSeasons && (
        <p className="text-xs text-gray-500 mt-0.5 mb-3">Showing all seasons — select a specific season to isolate.</p>
      )}
      {!allSeasons && <div className="mb-4" />}
      <ResponsiveContainer width="100%" height={350}>
        <ScatterChart margin={{ top: 20, right: 60, bottom: 60, left: 60 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            type="number"
            dataKey="play_count"
            name="Plays"
            label={{ value: 'Play Volume', position: 'insideBottom', offset: -10, fontSize: 12 }}
            tick={{ fontSize: 11 }}
          />
          <YAxis
            dataKey="epa_per_play"
            name="EPA/Play"
            label={{ value: 'EPA/Play', angle: -90, position: 'insideLeft', fontSize: 12 }}
            tick={{ fontSize: 11 }}
            tickFormatter={(v: number) => v.toFixed(2)}
          />
          <ReferenceLine y={0} stroke="#9ca3af" strokeDasharray="4 4" />
          <Tooltip content={<CustomTooltip />} />
          <Scatter data={data} fillOpacity={allSeasons ? 0.6 : 0.85}>
            {data.map((entry, i) => (
              <Cell key={i} fill={entry.epa_per_play >= 0 ? '#16a34a' : '#dc2626'} />
            ))}
            <LabelList
              dataKey="matchup"
              position="top"
              content={(props) => {
                const { x, y, value } = props as { x?: number; y?: number; value?: string }
                return (
                  <text
                    x={x}
                    y={(y ?? 0) - 6}
                    textAnchor="middle"
                    fontSize={11}
                    fill="#374151"
                  >
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
