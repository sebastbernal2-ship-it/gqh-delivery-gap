# The regime state machine

**Status: development only, declared before the run.** Both sealed windows are spent. This is layer 2 of
the system spec: one dated row per month with the cycle phase and the gate readings, so the sizing layer of
each thesis can read the state instead of guessing it. It gates sizing and never direction.

## Why

The analogue cycle work (nine infrastructure cycles, five phases) says phases are legible from paired
markers. The queue and compute studies gave us two of those markers with measured behaviour: the queue
withdrawal hazard and the compute rental level, the second leading the first by about two quarters (T34).
The bottleneck panel gives construction spend, supply chain pressure, delivery times and rates. Together
they can be reduced to a dated state.

## Inputs, all point in time

| Reading | Source | Coverage |
|---|---|---|
| Data centre construction spend, monthly | `results/bottleneck-factors.csv` | 2014-01 onward |
| Power and equipment construction spend | same | same |
| Supply chain pressure index, z | same | same |
| Delivery times, months | same | same |
| Ten year rate | same | same |
| Compute rental level against trailing twelve month mean | `results/compute-price-monthly.csv` | 2022-05 onward |
| Queue withdrawal hazard, trailing three months | `results/queue-panel.csv` | 2015 onward |
| Median age of live queue projects | same | same |

## Declared phase rules, version 1

Each month is scored against the five phases by named markers. The phase is the one with the most markers
agreeing, and the file reports the agreement share so a reader can re-map with different thresholds.

- **Shortage**: rental level above trend, supply chain pressure high, delivery times above their median,
  hazard below its median.
- **Buildout**: construction spend growth positive in at least two of the three spend lines, rental level
  above trend, hazard below its median.
- **Overbuild**: construction spend growth positive while rental level below trend, hazard at or above its
  median.
- **Shakeout**: hazard above its upper quartile, rental level below trend, construction spend growth
  falling.
- **Second wave**: hazard falling for three months, rental level recovering from below trend, construction
  spend growth turning positive.

Thresholds: trend is the trailing twelve month mean, medians and quartiles are computed on the full
available history of each reading and stated in the output.

## Output

`results/regime-state-daily.csv`, one row per month from 2014-01 to 2024-12: the readings, the phase, the
agreement share, and the markers that drove it. `results/regime-state-summary.json` carries the phase
prevalence, the transitions and the current reading.

No sizing rule is applied here. The phase to stance map stays in the strategy memo, and any sizing effect
will be measured separately before it is used.

## Falsifier

If the phase labels do not co-move with the analogue cycle markers (for example a buildout label through
the 2023-2024 rental decline), then the rule set is wrong and the machine is rebuilt, not patched.

## Ceiling

One version of judgment-based thresholds, readings of differing quality, and a compute sensor that only
exists from 2022. Development only.

## Result, 2026-10-04

132 monthly rows from 2014-01 to 2024-12. Version 1 of the rules gives a legible sequence with 15
transitions: buildout 79 months, overbuild 39, shakeout 8, shortage 6. Before 2022 the machine runs on
construction spend and the withdrawal hazard alone (no rental sensor), and those rows say so in the
markers column.

The relevant stretch: buildout from 2022-11 onward with an overbuild reading appearing in 2024 as rental
levels fell below trend and the withdrawal hazard rose, then a wobble between the two labels in late 2024
as the rental reading crossed back over its trend. The wobble is the honest sign that the two bands are
close, and the raw readings ship in the file so a reader can re-map with different thresholds.

The compute sensor is what makes this legible: rental levels lead the hazard by about two quarters (T34),
so the 2024 overbuild reading is the first place the machine says something the queue alone would not.
