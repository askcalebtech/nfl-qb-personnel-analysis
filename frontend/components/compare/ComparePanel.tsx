'use client'

import { useEffect, useState, useMemo } from 'react'
import { getQBStats } from '@/lib/api'
import type { QB, QBStats } from '@/types'
import QBSelector from '@/components/dashboard/QBSelector'
import SeasonFilter, { type Season } from '@/components/dashboard/SeasonFilter'
import CompareStatsGrid from './CompareStatsGrid'
import CompareBarChart from './CompareBarChart'
import CompareScatter from './CompareScatter'
import CompareTable from './CompareTable'

// Exported so child components can import the shape
export interface CompareRow {
  matchup: string
  aPlays: number
  aEpa: number
  aSR: number
  aPassAtt: number
  aSacks: number
  aScrambles: number
  aCpoe: number | null
  bPlays: number
  bEpa: number
  bSR: number
  bPassAtt: number
  bSacks: number
  bScrambles: number
  bCpoe: number | null
}

interface AggRow {
  plays: number
  epaSum: number
  srSum: number
  passAtt: number
  sacks: number
  scrambles: number
  cpoeSum: number
  cpoePlays: number
}

function aggregateByMatchup(rows: QBStats[]): Map<string, AggRow> {
  const map = new Map<string, AggRow>()
  for (const r of rows) {
    const key = r.personnel_matchup
    if (!key) continue
    const plays = r.play_count ?? 0
    const existing = map.get(key)
    if (!existing) {
      map.set(key, {
        plays,
        epaSum: (r.epa_per_play ?? 0) * plays,
        srSum: (r.success_rate ?? 0) * plays,
        passAtt: r.pass_attempts ?? 0,
        sacks: r.sacks ?? 0,
        scrambles: r.scrambles ?? 0,
        cpoeSum: (r.avg_cpoe ?? 0) * plays,
        cpoePlays: r.avg_cpoe != null ? plays : 0,
      })
    } else {
      existing.plays += plays
      existing.epaSum += (r.epa_per_play ?? 0) * plays
      existing.srSum += (r.success_rate ?? 0) * plays
      existing.passAtt += r.pass_attempts ?? 0
      existing.sacks += r.sacks ?? 0
      existing.scrambles += r.scrambles ?? 0
      existing.cpoeSum += (r.avg_cpoe ?? 0) * plays
      existing.cpoePlays += r.avg_cpoe != null ? plays : 0
    }
  }
  return map
}

interface Props {
  qbs: QB[]
  minPlays: number
  qbAId: string
  onQbAIdChange: (id: string) => void
  seasonA: Season
  onSeasonAChange: (s: Season) => void
}

export default function ComparePanel({ qbs, minPlays, qbAId, onQbAIdChange, seasonA, onSeasonAChange }: Props) {
  const [qbBId, setQbBId] = useState('')
  const [seasonB, setSeasonB] = useState<Season>('2025')
  const [allStatsA, setAllStatsA] = useState<QBStats[]>([])
  const [allStatsB, setAllStatsB] = useState<QBStats[]>([])
  const [loadingA, setLoadingA] = useState(false)
  const [loadingB, setLoadingB] = useState(false)
  const [errorA, setErrorA] = useState<string | null>(null)
  const [errorB, setErrorB] = useState<string | null>(null)

  useEffect(() => {
    if (!qbAId) { setAllStatsA([]); return }
    setLoadingA(true)
    setErrorA(null)
    getQBStats(qbAId)
      .then(setAllStatsA)
      .catch(() => setErrorA('Failed to load stats for QB A'))
      .finally(() => setLoadingA(false))
  }, [qbAId])

  useEffect(() => {
    if (!qbBId) { setAllStatsB([]); return }
    if (qbBId === qbAId) return  // synced via the allStatsA effect below
    setLoadingB(true)
    setErrorB(null)
    getQBStats(qbBId, seasonB === '2022–25' ? undefined : seasonB)
      .then(setAllStatsB)
      .catch(() => setErrorB('Failed to load stats for QB B'))
      .finally(() => setLoadingB(false))
  }, [qbBId, qbAId, seasonB])

  // When QB A stats load and same QB is selected, sync QB B stats
  useEffect(() => {
    if (qbBId && qbBId === qbAId) {
      setAllStatsB(allStatsA)
    }
  }, [allStatsA, qbAId, qbBId])

  const filteredA = useMemo(() => {
    if (seasonA === '2022–25') return allStatsA
    return allStatsA.filter((r) => r.season === seasonA)
  }, [allStatsA, seasonA])

  const filteredB = useMemo(() => {
    if (seasonB === '2022–25') return allStatsB
    return allStatsB.filter((r) => r.season === seasonB)
  }, [allStatsB, seasonB])

  const sharedRows = useMemo<CompareRow[]>(() => {
    if (!qbAId || !qbBId) return []
    const aggA = aggregateByMatchup(filteredA)
    const aggB = aggregateByMatchup(filteredB)
    const rows: CompareRow[] = []
    for (const [matchup, a] of Array.from(aggA.entries())) {
      const b = aggB.get(matchup)
      if (!b) continue
      if (a.plays < minPlays || b.plays < minPlays) continue
      rows.push({
        matchup,
        aPlays: a.plays,
        aEpa: a.plays > 0 ? a.epaSum / a.plays : 0,
        aSR: a.plays > 0 ? a.srSum / a.plays : 0,
        aPassAtt: a.passAtt,
        aSacks: a.sacks,
        aScrambles: a.scrambles,
        aCpoe: a.cpoePlays > 0 ? a.cpoeSum / a.cpoePlays : null,
        bPlays: b.plays,
        bEpa: b.plays > 0 ? b.epaSum / b.plays : 0,
        bSR: b.plays > 0 ? b.srSum / b.plays : 0,
        bPassAtt: b.passAtt,
        bSacks: b.sacks,
        bScrambles: b.scrambles,
        bCpoe: b.cpoePlays > 0 ? b.cpoeSum / b.cpoePlays : null,
      })
    }
    return rows.sort((a, b) => (b.aPlays + b.bPlays) - (a.aPlays + a.bPlays))
  }, [filteredA, filteredB, minPlays, qbAId, qbBId])

  const qbAName = qbs.find((q) => q.qb_id === qbAId)?.qb_name ?? qbAId
  const qbBName = qbs.find((q) => q.qb_id === qbBId)?.qb_name ?? qbBId
  const sameQB = Boolean(qbAId && qbBId && qbAId === qbBId)

  const title = !qbAId && !qbBId
    ? 'Select QBs to Compare'
    : sameQB
    ? `${qbAName}: ${seasonA} vs ${seasonB}`
    : qbAId && qbBId
    ? `${qbAName} vs ${qbBName}`
    : qbAId
    ? `${qbAName} — select a second QB`
    : `${qbBName} — select a first QB`

  const bothSelected = Boolean(qbAId && qbBId)
  const loading = loadingA || loadingB

  return (
    <div className="bg-gray-50 rounded-xl border border-gray-200 p-4 space-y-4">
      {/* Panel header */}
      <div className="flex items-center gap-3">
        <h2 className="text-base font-semibold text-gray-800">{title}</h2>
        {bothSelected && !loading && (
          <span className="text-xs text-gray-500 bg-white border border-gray-200 rounded px-2 py-0.5">
            {sharedRows.length} shared matchup{sharedRows.length !== 1 ? 's' : ''}
          </span>
        )}
      </div>

      {/* QB selectors */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* QB A */}
        <div className="bg-white rounded-lg border border-blue-200 p-3 space-y-3">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-blue-500 flex-shrink-0" />
            <span className="text-xs font-medium text-gray-600 uppercase tracking-wide">QB A</span>
          </div>
          <QBSelector qbs={qbs} selectedId={qbAId} onChange={onQbAIdChange} />
          <SeasonFilter selected={seasonA} onChange={onSeasonAChange} />
          {errorA && <p className="text-xs text-red-600">{errorA}</p>}
        </div>

        {/* QB B */}
        <div className="bg-white rounded-lg border border-orange-200 p-3 space-y-3">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-orange-400 flex-shrink-0" />
            <span className="text-xs font-medium text-gray-600 uppercase tracking-wide">QB B</span>
          </div>
          <QBSelector qbs={qbs} selectedId={qbBId} onChange={setQbBId} />
          <SeasonFilter selected={seasonB} onChange={setSeasonB} />
          {errorB && <p className="text-xs text-red-600">{errorB}</p>}
        </div>
      </div>

      {/* Empty state */}
      {!bothSelected && (
        <div className="flex items-center justify-center h-24 text-sm text-gray-400">
          Select a QB in both slots to see the comparison
        </div>
      )}

      {/* Loading */}
      {bothSelected && loading && (
        <div className="text-sm text-gray-500 py-4">Loading...</div>
      )}

      {/* Comparison content */}
      {bothSelected && !loading && (
        <div className="space-y-4">
          <CompareStatsGrid
            filteredA={filteredA}
            filteredB={filteredB}
            nameA={qbAName}
            nameB={qbBName}
            sameQB={sameQB}
            seasonA={seasonA}
            seasonB={seasonB}
          />

          {sharedRows.length === 0 ? (
            <div className="flex items-center justify-center h-20 text-sm text-gray-400 bg-white rounded-lg border border-gray-200">
              No shared matchups meet the {minPlays}+ play threshold
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <CompareBarChart rows={sharedRows} nameA={sameQB ? seasonA : qbAName} nameB={sameQB ? seasonB : qbBName} />
                <CompareScatter
                  rows={sharedRows}
                  nameA={qbAName}
                  nameB={qbBName}
                  sameQB={sameQB}
                  seasonA={seasonA}
                  seasonB={seasonB}
                />
              </div>
              <CompareTable
                rows={sharedRows}
                nameA={qbAName}
                nameB={qbBName}
                sameQB={sameQB}
                seasonA={seasonA}
                seasonB={seasonB}
              />
            </>
          )}
        </div>
      )}
    </div>
  )
}