

/*
    Fact Table: League Personnel Trends
    
    Shows league-wide personnel usage and performance trends.
    Useful for identifying which matchups are most common and
    what the league-average performance looks like.
    
    Grain: One row per Season + Personnel Matchup
*/

with qb_personnel_plays as (
    
    select * from main."int_qb_personnel_plays"
    
),

league_aggregates as (
    
    select
        -- Dimensions
        season,
        offense_personnel,
        defense_personnel,
        personnel_matchup,
        
        -- Play Volume
        count(*) as league_play_count,
        count(distinct qb_id) as qbs_used_matchup,
        
        -- League Average Performance
        avg(epa) as league_epa_per_play,
        stddev(epa) as league_epa_std_dev,
        avg(case when success = 1 then 1.0 else 0.0 end) as league_success_rate,
        
        -- Pass/Run Split
        avg(case when play_type = 'pass' then 1.0 else 0.0 end) as league_pass_rate,
        sum(case when play_type = 'pass' then 1 else 0 end) as league_pass_plays,
        sum(case when play_type = 'run' then 1 else 0 end) as league_run_plays,
        
        -- Yards
        avg(yards_gained) as league_avg_yards,
        
        -- CPOE
        avg(case when play_type = 'pass' then cpoe else null end) as league_avg_cpoe
        
    from qb_personnel_plays
    
    group by 1, 2, 3, 4
    
),

with_usage_rates as (
    
    select
        *,
        
        -- Calculate usage rate as % of all plays in that season
        100.0 * league_play_count / sum(league_play_count) over (partition by season) as usage_pct,
        
        -- Rank matchups by frequency within each season
        row_number() over (partition by season order by league_play_count desc) as usage_rank
        
    from league_aggregates
    
),

with_trends as (
    
    select
        *,
        
        -- Calculate year-over-year change in usage
        usage_pct - lag(usage_pct) over (
            partition by offense_personnel, defense_personnel 
            order by season
        ) as usage_pct_change_yoy,
        
        -- Calculate year-over-year change in EPA
        league_epa_per_play - lag(league_epa_per_play) over (
            partition by offense_personnel, defense_personnel 
            order by season
        ) as epa_change_yoy
        
    from with_usage_rates
    
)

select * from with_trends
order by season desc, league_play_count desc