select *
from {{ ref('int_route_comparison') }}
where abs(
    cost_diff_eur - (fuel_cost_diff_eur + wage_cost_diff_eur)
) > 0.000001