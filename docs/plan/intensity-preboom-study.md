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
