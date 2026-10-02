select
    strategy,
    distance_km,
    travel_time_min,
    fuel_cost_eur,
    wage_cost_eur,
    total_cost_eur
from {{ source('raw', 'route_results') }}