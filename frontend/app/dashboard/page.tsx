'use client'

import { useEffect, useState, useMemo } from 'react'
import { getQBs, getQBStats } from '@/lib/api'
import type { QB, QBStats } from '@/types'
import QBSelector from '@/components/dashboard/QBSelector'
import SeasonFilter, { type Season } from '@/components/dashboard/SeasonFilter'
import StatsGrid from '@/components/dashboard/StatsGrid'
import MatchupScatter from '@/components/dashboard/MatchupScatter'
import TopMatchups from '@/components/dashboard/TopMatchups'
import MatchupTable from '@/components/dashboard/MatchupTable'
import CompareToggle from '@/components/compare/CompareToggle'
import ComparePanel from '@/components/compare/ComparePanel'

const MIN_PLAYS_OPTIONS = [20, 50, 100] as const
type MinPlays = (typeof MIN_PLAYS_OPTIONS)[number]

export default function DashboardPage() {
  const [qbs, setQBs] = useState<QB[]>([])
  const [selectedId, setSelectedId] = useState('')
  const [season, setSeason] = useState<Season>('2025')
  const [minPlays, setMinPlays] = useState<MinPlays>(20)
  const [allStats, setAllStats] = useState<QBStats[]>([])
  const [compareOpen, setCompareOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getQBs()
      .then((data) => {
        setQBs(data)
        if (data.length > 0) setSelectedId(data[0].qb_id)
      })
      .catch(() => setError('Failed to load QB list. Is the API running?'))
  }, [])

  useEffect(() => {
    if (!selectedId) return
    setLoading(true)
    setError(null)
    getQBStats(selectedId)
      .then(setAllStats)
      .catch(() => setError('Failed to load QB stats.'))
      .finally(() => setLoading(false))
  }, [selectedId])

  const filteredStats = useMemo(() => {
    if (season === '2022–25') return allStats
    return allStats.filter((r) => r.season === season)
  }, [allStats, season])

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Controls */}
      <div className="flex flex-wrap items-end gap-4">
        {!compareOpen && qbs.length > 0 && (
          <QBSelector qbs={qbs} selectedId={selectedId} onChange={setSelectedId} />
        )}
        {!compareOpen && <SeasonFilter selected={season} onChange={setSeason} />}
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">
            Min Plays
          </label>
          <div className="flex gap-1">
            {MIN_PLAYS_OPTIONS.map((n) => (
              <button
                key={n}
                onClick={() => setMinPlays(n)}
                className={`px-3 py-1.5 rounded text-sm font-medium border transition-colors ${
                  minPlays === n
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                }`}
              >
                {n}+
              </button>
            ))}
          </div>
        </div>
        <CompareToggle open={compareOpen} onToggle={() => setCompareOpen((v) => !v)} />
      </div>

      {error && (
        <div className="rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {compareOpen ? (
        <ComparePanel
          qbs={qbs}
          minPlays={minPlays}
          qbAId={selectedId}
          onQbAIdChange={setSelectedId}
          seasonA={season}
          onSeasonAChange={setSeason}
        />
      ) : loading ? (
        <div className="text-sm text-gray-500">Loading...</div>
      ) : (
        <>
          <StatsGrid stats={filteredStats} qbs={qbs} selectedId={selectedId} season={season} />

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <MatchupScatter stats={filteredStats} season={season} />
            <TopMatchups stats={filteredStats} minPlays={minPlays} />
          </div>

          <MatchupTable stats={filteredStats} minPlays={minPlays} />
        </>
      )}
    </div>
  )
}
