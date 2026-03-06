
    
    create view main."int_qb_personnel_plays" as
    

/*
    Intermediate model: QB Personnel Plays
    
    Enriches the staging QB plays with:
    - QB name handling (filling NULLs from rusher names)
    - Personnel matchup combinations
    - Play success categorization
    - Situational context
*/

with qb_plays as (
    
    select * from main."stg_qb_plays"
    
),

enriched as (
    
    select
        -- All original columns
        *,
        
        -- Create personnel matchup identifier
        concat(offense_personnel, ' vs ', defense_personnel) as personnel_matchup,
        
        -- Categorize EPA performance
        case
            when epa >= 0.5 then 'Great'
            when epa >= 0 then 'Good'
            when epa >= -0.5 then 'Poor'
            else 'Very Poor'
        end as epa_category,
        
        -- Down and distance situations
        case
            when down = 1 then '1st Down'
            when down = 2 and yards_to_go <= 3 then '2nd & Short'
            when down = 2 and yards_to_go between 4 and 7 then '2nd & Medium'
            when down = 2 and yards_to_go >= 8 then '2nd & Long'
            when down = 3 and yards_to_go <= 3 then '3rd & Short'
            when down = 3 and yards_to_go between 4 and 7 then '3rd & Medium'
            when down = 3 and yards_to_go >= 8 then '3rd & Long'
            when down = 4 then '4th Down'
        end as down_distance_category,
        
        -- Field position categories
        case
            when yards_from_own_goal >= 80 then 'Red Zone'
            when yards_from_own_goal >= 60 then 'Opponent Territory'
            when yards_from_own_goal >= 40 then 'Midfield'
            when yards_from_own_goal >= 20 then 'Own Territory'
            else 'Own Red Zone'
        end as field_position_category,
        
        -- Game situation
        case
            when abs(score_differential) <= 3 then 'One Score'
            when abs(score_differential) <= 8 then 'Two Score'
            when abs(score_differential) <= 16 then 'Three Score'
            else 'Blowout'
        end as game_situation
        
    from qb_plays
    
)

select * from enriched;