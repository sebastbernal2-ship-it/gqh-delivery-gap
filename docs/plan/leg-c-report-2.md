# Leg C2: directional associations

Command: `python3 scripts/leg_c2_directional_scan.py --draws 200`

The scan used the mechanism-and-strategy development window only, 2015-07 through 2022-09. It used one canonical representation per node, changes rather than levels, and the existing three-month block shuffle. Each shuffled series was tested at lags zero through three, and the null statistic was the largest absolute correlation across those lags. Benjamini-Hochberg controlled the full ordered-pair grid at 10% FDR.

Ten canonical node series were available. Fifty-six ordered pairs had at least twelve aligned development months. Eight rows survived FDR, against 2.8 nominal 5% crossings expected across 56 tests. At 10% FDR, the estimated false count among survivors is 0.8. The eight rows form four reciprocal relationships. All eight are within-family; zero cross-family rows survived.

## Survivors, strongest first

The top two relationships are shown in both directions. Both selected lag zero, so these are contemporaneous associations, not evidence of a lead.

| From | To | Months | Best lag | Correlation | Null 95th percentile | q-value | Family |
|---|---|---:|---:|---:|---:|---:|---|
| `price:equity:buildout` | `price:equity:scarcity` | 57 | 0 | +0.5447 | 0.3612 | 0.0697 | within |
| `price:equity:scarcity` | `price:equity:buildout` | 57 | 0 | +0.5447 | 0.3174 | 0.0464 | within |
| `price:commodity:uranium` | `price:equity:buildout` | 87 | 0 | +0.4944 | 0.2872 | 0.0464 | within |
| `price:equity:buildout` | `price:commodity:uranium` | 87 | 0 | +0.4944 | 0.2749 | 0.0697 | within |
| `price:commodity:copper` | `price:commodity:uranium` | 87 | 0 | +0.4721 | 0.2667 | 0.0464 | within |
| `price:commodity:uranium` | `price:commodity:copper` | 87 | 0 | +0.4721 | 0.2947 | 0.0697 | within |
| `price:commodity:copper` | `price:equity:buildout` | 87 | 0 | +0.4361 | 0.2924 | 0.0464 | within |
| `price:equity:buildout` | `price:commodity:copper` | 87 | 0 | +0.4361 | 0.2625 | 0.0464 | within |

The commodity rows use the canonical node ids shown in the table.

## Cross-family result

The strongest cross-family relationship by absolute correlation was `price:equity:scarcity` to `firm:obligation:remaining-performance`: 55 months, lag 1, correlation +0.3469, null 95th percentile 0.3714, q=0.3184. In reverse, the selected direction was lag 1 with correlation -0.2377 and q=0.9505. Neither direction survived.

## Scale stability limit

Leg B reports scale stability ratios of 0.1667 for the buildout basket and 0.0553 for the scarcity basket. Neither is high against Leg B's observed range, and neither supports a fixed threshold claim from this scan. Leg B has no scale-stability rows for copper or uranium, so their ratios are unknown. No fixed threshold should be asserted for those surviving relationships. A high scale-stability ratio would rule out a fixed threshold rather than serve as a minor caveat.

The eight directional rows reduce to familiar, within-family co-movement. They do not identify a mechanism, a tradable lead, or a position. The 10 available series also include representations that yielded no eligible 12-month pair in this window. The graph inventory reports source-table totals, not node-level usable observations, so its counts do not expand the measured panel.
