# Declared study: does the market price the capex intensity rise

**Status: development only, declared before the run.** Both sealed windows are spent. T23 found capex
intensity running far above its own mean for the hyperscalers in the most recent quarters and left one
object open: whether the equity market prices that. This study answers it.

## The object

For every provider quarter with a measurable intensity change, the equity return from the filing date
forward, measured against the provider's own peer group. Positive association means the market pays for
the buildout, negative association means it charges for it, and no association means it ignores it until
the depreciation arrives. All three are facts worth having.

## Data

- Intensity: quarterly capex over quarterly revenue from `results/provider-capex-quarterly.csv` and
  `results/provider-revenue-quarterly.csv`, aligned within twenty days, year over year change in logs.
- Event date: the later of the two filing dates for that quarter, so the information is public by
  construction.
- Prices: `results/bar-cache/`, daily closes per ticker, read only.
- Peer groups: the groups declared in `results/market-panel.json` (hyperscaler, compute and AI, data
  center REIT). The excess return is the ticker return minus the equal weight return of its group over
  the same window.

## Tests, all reported

1. Pooled Spearman between year over year intensity change and forward excess return at five, twenty and
   sixty trading days.
2. The tercile spread: mean forward excess return of the top third of intensity change against the bottom
   third.
3. Per provider means, so one name cannot carry the result.

## Null

Permutation of the intensity labels across observations, five thousand draws per horizon.

## Falsifier

No association at any horizon, or the association is entirely carried by one provider.

## Ceiling

Six providers, short panels, overlapping return windows, one free price source. Development only, and
this does not open a sealed window.

## Reproduce

    python3 scripts/build_intensity_pricing_study.py

## Result, 2026-10-04

108 provider quarters across eight names. Intensity surprises are charged, not rewarded: rho -0.29
two-sided p 0.005 at five trading days, -0.24 at p 0.012 at twenty days, and -0.07 at p 0.49 by sixty
days. The tercile spread agrees: the top third of intensity change underperforms the bottom third by 2.2
percentage points over five days and 6.0 points over twenty, against peer group equal weight.

The effect is not one name: MSFT, EQIX and APLD sit slightly positive while CORZ, IREN and CRWV carry
most of the negative side, and the panel is small enough that either reading is fragile.

The fact this leaves: in this eight name panel, the market charges capital intensity over weeks rather
than months, which is the first priced link found in the provider family. Whether it generalises is the
next declared study, `docs/plan/intensity-factor-study.md`.
