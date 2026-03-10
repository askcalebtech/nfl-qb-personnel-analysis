import type { QB, QBStats, QBRanking, LeaderboardEntry, LeagueTrend } from '@/types'

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

async function fetchJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`, { cache: 'no-store' })
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`)
  return res.json() as Promise<T>
}

export async function getQBs(): Promise<QB[]> {
  return fetchJSON<QB[]>('/qbs')
}

export async function getQBStats(
  qbId: string,
  season?: string,
  minPlays?: number
): Promise<QBStats[]> {
  const params = new URLSearchParams()
  if (season) params.set('season', season)
  if (minPlays != null) params.set('min_plays', String(minPlays))
  const qs = params.toString()
  return fetchJSON<QBStats[]>(`/qbs/${encodeURIComponent(qbId)}/stats${qs ? `?${qs}` : ''}`)
}

export async function getRankings(season: string, minPlays = 20): Promise<QBRanking[]> {
  return fetchJSON<QBRanking[]>(`/rankings?season=${season}&min_plays=${minPlays}`)
}

export async function getLeaderboard(season: string, matchup: string): Promise<LeaderboardEntry[]> {
  return fetchJSON<LeaderboardEntry[]>(`/leaderboard?season=${season}&matchup=${encodeURIComponent(matchup)}`)
}

export async function getTrends(season?: string): Promise<LeagueTrend[]> {
  const qs = season ? `?season=${season}` : ''
  return fetchJSON<LeagueTrend[]>(`/trends${qs}`)
}

export async function getMatchup(matchup: string, season?: string): Promise<QBStats[]> {
  const qs = season ? `?season=${season}` : ''
  return fetchJSON<QBStats[]>(`/matchup/${encodeURIComponent(matchup)}${qs}`)
}
