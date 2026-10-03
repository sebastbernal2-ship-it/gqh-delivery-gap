# The sealed tests, and who opens them

Two studies, two holdouts, both still closed. This file says exactly what opening one means, so that the
moment it happens is a decision rather than a drift.

## The rule

The most recent fifth of a study's history, or the most recent two years, whichever is shorter, is set aside
before any design work and opened **once**. It is opened by a named person, and whatever it says is reported,
including a null. Nothing else in the study may be changed afterwards.

## Study one: the mechanism and the aggregate capacity strategy

| | |
|---|---|
| History | 2015-07 to 2024-09 |
| Development, already used | 2015-07 to 2022-09 |
| Holdout, unopened | 2022-10 to 2024-09 |
| Opens with | `python scripts/run_capacity_strategy.py --open-sealed` |
| What it reports | monthly returns of the market neutral pair under both cost assumptions, the equity curve, drawdown, turnover and the hit rate |

## Study two: the compute era

| | |
|---|---|
| History | 2022-06 to 2024-09 |
| Development, already used | 2022-06 to 2024-03 |
| Holdout, unopened | 2024-04 to 2024-09 |
| Opens with | `python scripts/run_capacity_strategy.py --open-sealed` for the strategy window, and the scan's `--window compute-era --open-sealed` when that flag is added |
| What it reports | the same measurements, inside the compute era window |

## What opening cannot do

- It cannot change a threshold, a horizon, a universe or a signal definition. Those are frozen in
  `docs/variants.md` and in the protocol files.
- It cannot be re-opened for a second look, and a result that is unwelcome is still the result.
- It cannot be described as validation of a strategy that was never tested in development. Both development
  passes were null, and the honest summary of an opened holdout on a null strategy is that it stays null or
  becomes a candidate requiring a fresh holdout.

## Who opens it

The captain names the person. Until then both holdouts stay closed, and this file is the record that the
choice was deliberate rather than forgotten.
