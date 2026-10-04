# Declared study: the intensity surprise split by who owns the capital

**Status: development only, declared before the run.** Both sealed windows are spent. The cross-section
study found the intensity effect does not generalise across 58 names, and left a sign-consistent structure:
negative in the segments that own capital, positive where capacity is leased or regulated. This study
declares that split before measuring it.

## The object

Two segments, defined from the already declared market panel groups.

- **Owned capital**: hyperscaler, compute and AI, buildout. These names buy the equipment and carry the
  depreciation, so an intensity surprise raises future depreciation and funding needs.
- **Leased or regulated**: data center REIT, power, fuel and nuclear. These names lease capacity, pass
  capital into a rate base with an allowed return, or sell fuel, so an intensity surprise is closer to
  demand evidence than to a charge.

## The declared expectation

Negative association in owned capital, zero or positive association in leased or regulated. Both are
reported either way, and a null in either segment is a fact.

## Tests

The same two tests, one per segment: the mean within-quarter Spearman correlation between intensity
change and forward excess return, first against the complex benchmark, then against own group. Horizons
five, twenty and sixty trading days. This is a two-test design and both are reported with their nulls:
within-quarter permutation, five thousand draws, two sided.

## Falsifier

The owned capital segment shows no negative association, or the leased and regulated segment shows the
same negative association, which would make ownership of capital irrelevant.

## Ceiling

The same 640 observations re cut, so this is a declared second look at one dataset rather than fresh
evidence, and it is labelled that way. Overlapping return windows, one free price source, no volume data,
so capacity is unknown. Development only.

## Reproduce

    python3 scripts/build_intensity_segment_study.py

## Result, 2026-10-04

The split is as declared. Owned capital, 33 names and 334 observations: rho -0.16 (p 0.031) at five
days, -0.15 (p 0.048) at twenty, -0.03 (p 0.75) at sixty, with tercile spreads of -1.9 and -5.2
percentage points. Leased or regulated, 25 names and 306 observations: -0.05 (p 0.46), +0.006 (p 0.94),
+0.03 (p 0.58), with tercile spreads at or slightly above zero.

The p values are modest and this is a declared second look at one dataset, so the honest reading is a
supported hypothesis with a mechanism, not an established factor. The market charges the intensity
surprise where the capital is owned and carries it into depreciation and funding, and does not charge it
where capacity is leased or returns flow through a rate base.

The next evidence must be a different sample: the declared time split, training on the early quarters and
testing on the later ones, follows in `docs/plan/intensity-timesplit-study.md`.
