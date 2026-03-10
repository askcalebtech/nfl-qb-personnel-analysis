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
