select
    strategy as route_strategy,
    round(distance_km, 3) as distance_km,
    round(travel_time_min, 2) as travel_time_min,
    round(total_cost_eur, 2) as total_operating_cost_eur,
    round(extra_distance_km, 3) as extra_distance_km,
    round(time_diff_min, 2) as time_diff_min,
    round(fuel_cost_diff_eur, 3) as fuel_cost_diff_eur,
    round(wage_cost_diff_eur, 3) as wage_cost_diff_eur,
    round(cost_diff_eur, 3) as total_cost_diff_eur,
    round(cost_saving_pct, 1) as cost_saving_pct,

    case
        when strategy = 'shortest_distance'
            then 'Baseline: shortest-distance route'
        when cost_diff_eur < 0
            and extra_distance_km > 0
            and wage_cost_diff_eur < 0
            then 'Cheaper despite longer distance: driver-time savings outweigh added distance cost'
        when cost_diff_eur < 0
            then 'Cheaper than shortest-distance route'
        when cost_diff_eur > 0
            then 'More expensive than shortest-distance route'
        else 'Same estimated cost as shortest-distance route'
    end as business_explanation

from {{ ref('int_route_comparison') }}

order by total_cost_eur