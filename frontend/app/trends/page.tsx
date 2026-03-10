'use client'

import { useEffect, useState, useMemo } from 'react'
import { getTrends } from '@/lib/api'
import type { LeagueTrend } from '@/types'
import SeasonFilter, { type Season } from '@/components/dashboard/SeasonFilter'
import MatchupUsageChart from '@/components/trends/MatchupUsageChart'
import TrendsTable from '@/components/trends/TrendsTable'

export default function TrendsPage() {
  const [allTrends, setAllTrends] = useState<LeagueTrend[]>([])
  const [season, setSeason] = useState<Season>('2024')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getTrends()
      .then(setAllTrends)
      .catch(() => setError('Failed to load trends. Is the API running?'))
      .finally(() => setLoading(false))
  }, [])

  const VALID_OFFENSE = new Set(['11', '12', '21'])
  const VALID_DEFENSE = new Set(['Base', 'Nickel', 'Dime'])

  function isCommonMatchup(matchup: string | null | undefined): boolean {
    if (!matchup) return false
    const [off, def] = matchup.split(' vs ')
    return VALID_OFFENSE.has(off) && VALID_DEFENSE.has(def)
  }

  const filtered = useMemo(() => {
    const bySeason = season === '2022–25' ? allTrends : allTrends.filter((r) => r.season === season)
    return bySeason.filter((r) => isCommonMatchup(r.personnel_matchup))
  }, [allTrends, season])

  // Chart always shows all seasons to render lines across time
  const chartData = season === '2022–25' ? allTrends : allTrends

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {error && (
        <div className="rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-sm text-gray-500">Loading...</div>
      ) : (
        <>
          <MatchupUsageChart trends={chartData} />
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Filter table by season</p>
            <SeasonFilter selected={season} onChange={setSeason} />
          </div>
          <TrendsTable trends={filtered} />
        </>
      )}
    </div>
  )
}
