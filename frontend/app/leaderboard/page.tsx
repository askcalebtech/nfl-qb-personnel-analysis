'use client'

import { useEffect, useState, useMemo } from 'react'
import { getLeaderboard, getTrends } from '@/lib/api'
import type { LeaderboardEntry, LeagueTrend } from '@/types'
import LeaderboardTable from '@/components/leaderboard/LeaderboardTable'

const SEASONS = ['2022', '2023', '2024', '2025']
const VALID_OFFENSE = new Set(['11', '12', '21'])
const VALID_DEFENSE = new Set(['Base', 'Nickel', 'Dime'])

function isCommonMatchup(m: string | null | undefined): boolean {
  if (!m) return false
  const [off, def] = m.split(' vs ')
  return VALID_OFFENSE.has(off) && VALID_DEFENSE.has(def)
}

function toUrlMatchup(m: string): string {
  return m.replace(/ /g, '_')
}

export default function LeaderboardPage() {
  const [season, setSeason] = useState('2025')
  const [trends, setTrends] = useState<LeagueTrend[]>([])
  const [entries, setEntries] = useState<LeaderboardEntry[]>([])
  const [selectedMatchup, setSelectedMatchup] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Load trends once for matchup list
  useEffect(() => {
    getTrends().catch(() => null).then((data) => {
      if (data) setTrends(data)
    })
  }, [])

  // Derive matchup options sorted by total usage across all seasons
  const matchupOptions = useMemo(() => {
    const totals = new Map<string, number>()
    for (const row of trends) {
      if (!isCommonMatchup(row.personnel_matchup)) continue
      const key = row.personnel_matchup!
      totals.set(key, (totals.get(key) ?? 0) + (row.league_play_count ?? 0))
    }
    return [...totals.entries()]
      .sort((a, b) => b[1] - a[1])
      .map(([matchup]) => matchup)
  }, [trends])

  // Set default matchup once options load
  useEffect(() => {
    if (matchupOptions.length > 0 && !selectedMatchup) {
      setSelectedMatchup(matchupOptions[0])
    }
  }, [matchupOptions, selectedMatchup])

  // Fetch leaderboard whenever season or matchup changes
  useEffect(() => {
    if (!selectedMatchup) return
    setLoading(true)
    setError(null)
    getLeaderboard(season, toUrlMatchup(selectedMatchup))
      .then(setEntries)
      .catch(() => setError('Failed to load leaderboard. Is the API running?'))
      .finally(() => setLoading(false))
  }, [season, selectedMatchup])

  const threshold = entries[0]?.min_plays_threshold ?? null

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Controls */}
      <div className="flex flex-wrap items-end gap-6">
        {/* Season */}
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">
            Season
          </label>
          <div className="flex gap-1">
            {SEASONS.map((s) => (
              <button
                key={s}
                onClick={() => setSeason(s)}
                className={`px-3 py-1.5 rounded text-sm font-medium border transition-colors ${
                  season === s
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                }`}
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        {/* Matchup */}
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">
            Personnel Matchup
          </label>
          <select
            value={selectedMatchup}
            onChange={(e) => setSelectedMatchup(e.target.value)}
            className="px-3 py-1.5 rounded border border-gray-300 bg-white text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {matchupOptions.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </div>

        {/* Threshold note */}
        {threshold != null && !loading && (
          <p className="text-xs text-gray-500 pb-1.5">
            Min plays threshold:{' '}
            <span className="font-semibold text-gray-700">{threshold}</span>
            {' '}(40th percentile of play volume for this matchup)
          </p>
        )}
      </div>

      {error && (
        <div className="rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-sm text-gray-500">Loading...</div>
      ) : entries.length === 0 ? (
        <div className="rounded-md bg-gray-50 border border-gray-200 px-4 py-8 text-center text-sm text-gray-500">
          No data available for {selectedMatchup} in {season}.
        </div>
      ) : (
        <LeaderboardTable entries={entries} />
      )}
    </div>
  )
}
