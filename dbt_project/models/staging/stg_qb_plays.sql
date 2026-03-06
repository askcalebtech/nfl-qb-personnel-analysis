{{
  config(
    materialized='view'
  )
}}

/*
    Staging model for QB plays
    
    This model loads the filtered QB plays from our Spark processing
    and applies basic cleaning and standardization.
    
    Source: data/processed/qb_plays_2022_2024.parquet (created by Spark)
*/

with source_data as (
    
    select * from qb_plays_raw
    
),

cleaned as (
    
    select
        -- Identifiers
        game_id,
        old_game_id,
        play_id,
        
        -- QB Information
        coalesce(passer_player_id, passer_id) as qb_id,
        passer_player_name as qb_name,
        passer_id as qb_id_alt,
        
        -- Game Context
        season,
        week,
        season_type,
        game_date,
        home_team,
        away_team,
        posteam as team,
        defteam as opponent,
        
        -- Play Details
        play_type,
        down,
        ydstogo as yards_to_go,
        yardline_100 as yards_from_own_goal,
        goal_to_go,
        qtr as quarter,
        
        -- Personnel
        offense_personnel_std as offense_personnel,
        defense_personnel_std as defense_personnel,
        
        -- Performance Metrics
        epa,
        wpa,
        success,
        cpoe,
        air_epa,
        yac_epa,
        
        -- Play type flags (from nflfastR binary columns)
        pass_attempt,
        sack,
        qb_scramble,

        -- Additional Context
        score_differential,
        ep as expected_points,
        wp as win_probability,
        yards_gained
        
    from source_data
    
),

final as (
    
    select
        *,
        
        -- Create a unique play identifier
        concat(old_game_id, '_', cast(play_id as string)) as play_key,
        
        -- Flag for whether this is a pass or run
        case 
            when play_type = 'pass' then true
            when play_type = 'run' then true
            else false
        end as is_dropback,
        
        -- Situational flags
        case when down = 3 then true else false end as is_third_down,
        case when down = 4 then true else false end as is_fourth_down,
        case when yards_to_go >= 10 then true else false end as is_long_distance,
        case when score_differential between -8 and 8 then true else false end as is_close_game
        
    from cleaned
    
)

select * from final