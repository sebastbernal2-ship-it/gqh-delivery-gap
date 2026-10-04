# Leg B2: node distributions and scale stability

Monthly development-window observations only. Each row is one measurable node representation.
The rolling scale uses trailing twelve observations. Stability is the sample standard deviation
of rolling scales divided by the full-series standard deviation. Order-of-magnitude movement is
reported when the largest rolling scale is at least ten times the smallest. A series is too short to
judge when it has fewer than 24 monthly observations.

Most stable: `price:equity:scarcity` (scarcity_basket); n=57, ratio=0.0552567.
Least stable: `feature:equipment:lead-time-share` (delivery_time_index); n=105, ratio=0.320281.

## Scale moves by an order of magnitude
- `feature:equipment:lead-time-share` (supply_chain_pressure): minimum rolling scale 0.107825, maximum rolling scale 1.38942, ratio 12.8859.
- `price:commodity:gas` (monthly_gas_level): minimum rolling scale 0.134026, maximum rolling scale 1.64079, ratio 12.2423.

## Too short to judge
- `firm:obligation:remaining-performance` (reported_obligation_value): 19 monthly observations, 2018-05 to 2022-08.
- `firm:obligation:unapproved-change-orders` (change_over_abs_value): 13 monthly observations, 2015-03 to 2018-02.
- `price:compute:rental` (monthly_median_family_rebased_index): 22 monthly observations, 2022-06 to 2024-03.

## Limits

Only locally present node series are measured. The graph inventory's stated row totals are source-table totals, not node-level observations. Nodes without a usable local series are omitted rather than assigned fabricated values.
Development windows exclude the declared compute holdout and the mechanism holdout. The source panels do not provide monthly grid demand or generation series, so those nodes are not represented.
