{{
  config(
    materialized='table'
  )
}}

/*
    Fact Table: QB Performance by Personnel Matchup

    Aggregates play-level QB data into per-season, per-matchup summaries.
    Core table powering QB vs personnel analysis.

    Grain: One row per QB + Season + Personnel Matchup
*/

with plays as (

    select * from {{ ref('int_qb_personnel_plays') }}

),

aggregated as (

    select
        -- Dimensions
        qb_id,
        max(qb_name)        as qb_name,
        season,
        max(team)           as team,
        offense_personnel,
        defense_personnel,
        personnel_matchup,

        -- Volume
        count(*)                                                        as play_count,
        sum(case when pass_attempt = 1 and sack = 0 then 1 else 0 end)  as pass_attempts,
        sum(sack)                                                       as sacks,
        sum(qb_scramble)                                                as scrambles,
        sum(case when play_type = 'run' and coalesce(qb_scramble, 0) = 0 then 1 else 0 end) as qb_rushes,

        -- Performance
        avg(epa)                                                        as epa_per_play,
        sum(epa)                                                        as total_epa,
        avg(case when success = 1 then 1.0 else 0.0 end)               as success_rate,
        avg(yards_gained)                                               as avg_yards,
        sum(yards_gained)                                               as total_yards,

        -- Passing metrics (pass plays only)
        avg(case when play_type = 'pass' then cpoe       else null end) as avg_cpoe,
        avg(case when play_type = 'pass' then air_epa    else null end) as avg_air_epa,
        avg(case when play_type = 'pass' then yac_epa    else null end) as avg_yac_epa,

        -- Win probability added
        avg(wpa)                                                        as avg_wpa

    from plays

    group by qb_id, season, offense_personnel, defense_personnel, personnel_matchup

),

final as (

    select
        *,
        case when play_count >= 20 then true else false end as meets_min_threshold,
        case when play_count >= 50 then true else false end as meets_starter_threshold
    from aggregated

)

select * from final
order by season desc, qb_id, play_count desc
