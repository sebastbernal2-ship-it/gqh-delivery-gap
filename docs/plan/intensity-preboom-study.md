# Declared study: the intensity charge before the boom

**Status: development only, declared before the run.** Both sealed windows are spent. The intensity charge
is sign stable across 2022 to 2024 and 2025 onward, on one buildout. This study asks whether the charge
exists in the pre-boom regime, 2018 through 2021, which is a different macro and a different capex story.

## The object

The same statistic, the mean within-quarter Spearman correlation between year over year capex intensity
change and forward group excess return, computed on filing dates from 2018-01-01 to 2021-12-31, across the
same declared complex. If the charge appears there, it is a property of capex surprises rather than of the
AI buildout. If it does not, then the charge is regime specific and that is the fact.

## Tests

Three windows side by side: pre-boom (2018 to 2021), buildout (2022 to 2024), late (2025 onward), at five,
twenty and sixty trading days, with within-quarter permutation nulls, five thousand draws, two sided. The
provider panel is reported separately where coverage allows.

## Falsifier

No negative association in the pre-boom window.

## Ceiling

The pre-boom window has fewer capex heavy names, and the 2018 to 2021 regime contains a different rate
environment, so a null there does not kill the buildout reading. It bounds it.

## Reproduce

    python3 scripts/build_intensity_preboom_study.py

## Result, 2026-10-04

All three windows lean negative at five and twenty days, so the direction of the charge is not a
property of the AI buildout alone.

- Pre-boom (2018 to 2021, 142 observations, 24 names): -0.077 (p 0.54), -0.110 (p 0.37), -0.046 (p 0.74),
  tercile spreads -2.1, -3.8 and -1.9 percentage points.
- Buildout (2022 to 2024, 87 observations, 25 names): -0.164 (p 0.23), -0.263 (p 0.054), -0.146 (p 0.30),
  tercile spreads -2.5, -8.0 and -10.2 points.
- Late (2025 onward, 105 observations, 32 names): -0.261 (p 0.043), -0.092 (p 0.48), +0.135 (p 0.30),
  tercile spreads -3.2, -2.3 and +12.4 points.

The fact this leaves: the charge is sign consistent across three regimes and six short-horizon estimates,
strongest in the buildout window and weakest in the only genuinely different regime, and it is
statistically fragile everywhere except the late five day cell. Sixty day readings are mixed, with the
late window turning positive. This stays a candidate with a mechanism, and the next objects are capacity
and costs rather than more cuts of the same panel.
