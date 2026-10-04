# Declared study: the time split that decides whether the intensity charge is real

**Status: development only, declared before the run.** Both sealed windows are spent. The segment study
(T27) says the market charges capital intensity where capital is owned, on a second look at one dataset,
with modest p values. The only way that becomes evidence rather than a description is a different sample.

## The object

The same owned capital signal, split in time. The early sample trains the reading and the late sample
tests it. Nothing is fitted: the statistic is the same within-quarter correlation as before, so the split
is a sample change, not a model change.

## The declared split

- **Early**: filing dates from the start of the panel through 2024-12-31.
- **Late**: filing dates from 2025-01-01 onward.

The late window is the test. It contains the period in which intensity rose most, which is exactly when
the charge should be most visible if the mechanism is real, and it is also the period where a crowding
story would show up as the opposite sign.

## Tests

The mean within-quarter Spearman correlation between intensity change and forward group excess return,
computed separately in each window, at five, twenty and sixty trading days, with within-quarter
permutation nulls, five thousand draws, two sided. Both windows are reported either way, and the segment
breakdown is reported for the late window so one segment cannot carry it.

## Falsifier

The late window shows no negative association, or the sign flips relative to the early window.

## Ceiling

Two windows of one buildout, one price source, overlapping return windows, no volume. A late window
pass is encouraging, not sufficient; it is one more cut of the same underlying story.

## Reproduce

    python3 scripts/build_intensity_timesplit_study.py

## Result, 2026-10-04

The negative sign is stable across time. The early window (through 2024) shows -0.12 (p 0.21) at five
days, -0.18 (p 0.050) at twenty and -0.09 at sixty. The late window (2025 onward) shows -0.26 (p 0.043)
at five days, -0.09 (p 0.48) at twenty and +0.14 (p 0.30) at sixty. All four short-horizon estimates lean
negative.

The ownership mechanism does not survive the split. In the late window the leased and regulated segment
is also negative at five and twenty days (-0.22 and -0.19), so the charge is not confined to names that
own their capital. What looked like an ownership split in the pooled data reads in the later sample as a
broader short-horizon charge, with a possible recovery by sixty days.

The fact this leaves: the stable object is a broad negative association between intensity surprises and
relative equity returns over five to twenty trading days, with a reversal candidate at sixty days. The
ownership mechanism is downgraded, and the reversal is the next declared object.
