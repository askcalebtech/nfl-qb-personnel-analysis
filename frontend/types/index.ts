export interface QB {
  qb_id: string
  qb_name: string | null
  first_season: number | null
  last_season: number | null
  seasons_played: number | null
  career_plays: number | null
  career_pass_attempts: number | null
  career_sacks: number | null
  career_scrambles: number | null
  career_qb_rushes: number | null
  career_epa_per_play: number | null
  career_success_rate: number | null
  career_total_epa: number | null
  career_total_yards: number | null
  unique_matchups_faced: number | null
  unique_offense_personnel: number | null
  unique_defense_personnel: number | null
  best_matchup_epa: number | null
  career_epa_percentile: number | null
  plays_rank: number | null
  is_starter: boolean | null
}

export interface QBStats {
  qb_id: string
  qb_name: string | null
  season: string | null
  team: string | null
  offense_personnel: string | null
  defense_personnel: string | null
  personnel_matchup: string | null
  play_count: number | null
  pass_attempts: number | null
  sacks: number | null
  scrambles: number | null
  qb_rushes: number | null
  epa_per_play: number | null
  total_epa: number | null
  success_rate: number | null
  avg_yards: number | null
  total_yards: number | null
  avg_cpoe: number | null
  avg_air_epa: number | null
  avg_yac_epa: number | null
  avg_wpa: number | null
  meets_min_threshold: boolean | null
  meets_starter_threshold: boolean | null
}

export interface LeaderboardEntry {
  qb_id: string
  qb_name: string | null
  season: string | null
  team: string | null
  play_count: number | null
  epa_per_play: number | null
  success_rate: number | null
  pass_attempts: number | null
  sacks: number | null
  scrambles: number | null
  avg_cpoe: number | null
  rank: number
  min_plays_threshold: number
}

export interface QBRanking {
  qb_id: string
  qb_name: string | null
  season: string
  total_plays: number | null
  epa_per_play: number | null
  success_rate: number | null
  pass_attempts: number | null
  is_starter: boolean | null
}

export interface LeagueTrend {
  season: string | null
  offense_personnel: string | null
  defense_personnel: string | null
  personnel_matchup: string | null
  league_play_count: number | null
  qbs_used_matchup: number | null
  league_epa_per_play: number | null
  league_epa_std_dev: number | null
  league_success_rate: number | null
  league_pass_rate: number | null
  league_pass_plays: number | null
  league_run_plays: number | null
  league_avg_yards: number | null
  league_avg_cpoe: number | null
  usage_pct: number | null
  usage_rank: number | null
  usage_pct_change_yoy: number | null
  epa_change_yoy: number | null
}

// ---- Projections (public/data/projections.json) ----
// Probabilities are 0-1. Margins and points are home-minus-away points
// (positive favors home). Ratings are points-style team strength units.

export interface GameComponents {
  home_matchup: number
  away_matchup: number
  matchup_points: number // points contribution from matchups
  hfa: number // home-field advantage, points
  nudge: number // points
  home_qb_adj_pts: number // points
  away_qb_adj_pts: number // points
}

export interface ProjectionTeam {
  team: string // code, e.g. "BUF"
  name: string
  conference: string // "AFC" | "NFC"
  division: string // e.g. "AFC East"
  record: string // "6-1" or "6-1-1"
  off: number | null // raw offense rating
  def: number | null // raw defense rating
  adj_off: number | null // adjusted offense rating
  adj_def: number | null // adjusted defense rating
  starter: string | null
  qb_adj: number | null
  rush_off: number | null
  rush_def: number | null
  avg_wins: number
  wins_p10: number
  wins_p90: number
  div: number // 0-1 probability
  playoffs: number // 0-1 probability
  seed1: number // 0-1 probability
}

export interface ProjectionGame {
  game_id: string
  week: number
  gameday: string | null // YYYY-MM-DD
  away: string
  home: string
  neutral: boolean
  stadium: string | null
  p_home: number // 0-1 home win probability
  margin: number // projected home margin, points
  nudge: number // points
  mkt_home: number | null // 0-1 market-implied home win probability
  spread: number | null // market spread line
  components: GameComponents
}

/** Actual result and closing market for a completed game, refreshed every run. */
export interface GameFinal {
  home_score: number | null
  away_score: number | null
  result: number | null // actual home margin, points
  close_mkt_home: number | null // 0-1 closing market home win probability
  close_spread: number | null // closing spread, positive favors home
}

/** A completed game: the pre-game prediction (frozen) plus the actual result. */
export interface CompletedGame extends ProjectionGame {
  final: GameFinal
  source: 'published' | 'backfill' // as published, or recomputed from earlier weeks' games only
  predicted_at: string | null // ISO UTC of the published file, null for backfill
  home_starter: string | null
  away_starter: string | null
}

export interface ProjectionsData {
  season: number
  through_week: number
  last_result_date: string | null // YYYY-MM-DD, latest completed game
  generated_at: string // ISO UTC
  league_anya: number | null
  model_version: string
  warnings: string[]
  teams: ProjectionTeam[]
  games: ProjectionGame[]
  completed?: CompletedGame[] // absent in files published before results were kept
}
