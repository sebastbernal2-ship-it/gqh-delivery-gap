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
