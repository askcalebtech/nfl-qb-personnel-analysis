
  
    
    
    create  table main."dim_qbs"
    as
        

/*
    Dimension Table: QBs
    
    One row per QB with career aggregates across all personnel matchups.
    Useful for QB comparisons and filtering in the frontend.
    
    Grain: One row per QB
*/

with qb_stats as (
    
    select * from main."fct_qb_personnel_stats"
    
),

qb_career_stats as (
    
    select
        qb_id,
        -- Use the first non-null name found
        max(qb_name) as qb_name,
        
        -- Career span
        min(season) as first_season,
        max(season) as last_season,
        count(distinct season) as seasons_played,
        
        -- Total plays across all matchups and seasons
        sum(play_count) as career_plays,
        sum(pass_attempts) as career_pass_attempts,
        sum(qb_rushes) as career_qb_rushes,
        
        -- Weighted averages (weighted by play count)
        sum(epa_per_play * play_count) / sum(play_count) as career_epa_per_play,
        sum(success_rate * play_count) / sum(play_count) as career_success_rate,
        
        -- Total production
        sum(total_epa) as career_total_epa,
        sum(total_yards) as career_total_yards,
        
        -- Personnel diversity
        count(distinct personnel_matchup) as unique_matchups_faced,
        count(distinct offense_personnel) as unique_offense_personnel,
        count(distinct defense_personnel) as unique_defense_personnel,
        
        -- Best matchup
        max(case when play_count >= 20 then epa_per_play else null end) as best_matchup_epa
        
    from qb_stats
    
    group by 1
    
),

with_rankings as (
    
    select
        *,
        
        -- Career EPA percentile
        percent_rank() over (order by career_epa_per_play) as career_epa_percentile,
        
        -- Volume rank
        row_number() over (order by career_plays desc) as plays_rank,
        
        -- Qualify as "starter" if 500+ plays
        case when career_plays >= 500 then true else false end as is_starter
        
    from qb_career_stats
    
)

select * from with_rankings
order by career_plays desc

  