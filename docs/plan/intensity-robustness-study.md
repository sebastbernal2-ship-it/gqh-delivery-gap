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
