with routes as (

    select *
    from {{ ref('stg_route_results') }}

),

baseline as (

    select
        distance_km,
        travel_time_min,
        fuel_cost_eur,
        wage_cost_eur,
        total_cost_eur
    from routes
    where strategy = 'shortest_distance'

),

compared as (

    select
        r.strategy,
        r.distance_km,
        r.travel_time_min,
        r.fuel_cost_eur,
        r.wage_cost_eur,
        r.total_cost_eur,

        r.distance_km - b.distance_km
            as extra_distance_km,

        r.travel_time_min - b.travel_time_min
            as time_diff_min,

        r.fuel_cost_eur - b.fuel_cost_eur
            as fuel_cost_diff_eur,

        r.wage_cost_eur - b.wage_cost_eur
            as wage_cost_diff_eur,

        r.total_cost_eur - b.total_cost_eur
            as cost_diff_eur,

        (b.total_cost_eur - r.total_cost_eur)
            / b.total_cost_eur * 100
            as cost_saving_pct

    from routes r
    cross join baseline b

)

select *
from compared