# Declared study: robustness of the intensity charge

**Status: development only, declared before the run.** Both sealed windows are spent. The charge is sign
consistent across regimes and fragile in each. This study asks the two questions that decide whether it is
a name effect or a quarter effect.

## The object

1. **Out of the discovery set**: the eight provider names that produced the first result (T25) are removed
   entirely. The statistic is recomputed on the remaining names only. If the charge lives on those eight,
   this catches it.
2. **Per quarter win rate**: the sign of the within-quarter correlation in every quarter, not only the
   average, plus the sign of the tercile spread per quarter. A result resting on two quarters is visible
   here and not in an average.

## Tests

Both at five, twenty and sixty days, on the group excess benchmark, with the within-quarter permutation
null for the reduced panel.

## Falsifier

The charge disappears once the discovery names are removed, or it appears in fewer than half the quarters.

## Ceiling

Same panel, same price source, overlapping windows. This is a robustness pass, not new evidence.

## Reproduce

    python3 scripts/build_intensity_robustness_study.py

## Result, 2026-10-04

Two facts, both uncomfortable for the charge.

Without the discovery names, the effect halves and loses significance: 498 observations across 49 names
show -0.042 (p 0.44) at five days, -0.026 (p 0.63) at twenty and +0.001 at sixty, against the full panel's
-0.087 (p 0.064), -0.072 (p 0.13) and -0.017.

The per quarter record is close to a coin: across 39 quarters the correlation is negative in 56 percent
at five days, 62 percent at twenty and 56 percent at sixty, and the tercile spread is negative in 56, 67
and 56 percent.

The fact this leaves: the intensity charge is directionally consistent, economically motivated, and
statistically fragile, with about half of it living in the ten names that produced the first result.
Further cuts of this panel are not evidence. The next real evidence is a disjoint sample and a capacity
and cost check, and until then it is a candidate, not an edge.
