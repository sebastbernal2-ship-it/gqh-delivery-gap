# Declared study: the exit object, crowding and withdrawal

**Status: development only, declared before the run.** Both sealed windows are spent. Nothing here is an
instrument test. The protocol is committed before the analysis runs.

## Why this object

T14 says an exit is more predictable than a revision, and the earlier queue study died on a censoring
problem: the queue duration feature exists only for projects that reached an agreement, which is the
survivor subset. The exit outcome has no such hole. Every project in the snapshot either withdrew or
did not, so the whole panel carries the label. This study rebuilds the question on the object that can
actually be measured.

## The question

Does queue crowding at the moment of a request order the chance the project later withdraws? The
declared expectation from `docs/plan/object-redefinition.md` is positive: more planned capacity ahead
of a project raises its cost of staying, so it withdraws more often.

## Data and declared point-in-time features

- Population: all 36,441 projects in `results/queue-panel.csv`, snapshot through February 2025.
- Outcome: `q_status == withdrawn` (20,921 projects, 57.4 percent). Everything else is the no side.
- **Primary feature, crowding**: the cumulative nameplate MW of requests in the same state with a
  strictly earlier `q_date`. Point-in-time safe: only earlier requests are used, never later ones and
  never outcomes.
- **Secondary features**: project size (`mw1`) and technology (`type_clean`), both observable at the
  request.
- Excluded: `days_ir_to_ia` and every other duration that exists only for projects that reached an
  agreement, because that is the censoring that killed the earlier study.

## Tests, all reported

1. **Crowding (primary)**: Spearman correlation between log cumulative preceding state MW and the
   withdrawal label, pooled.
2. **Size**: the same correlation with log project MW.
3. **Technology**: withdrawal share by technology, summarised by the spread between the top and bottom
   technology among those with at least 200 projects.

## Null

Outcomes are permuted **within state-year blocks**, 5,000 draws, and each statistic is recomputed. The
conditioning matters: withdrawal rates move with cohort and region, and only within-cell variation is
informative. Reported p-values are permutation p-values.

## Falsifier

The crowding correlation is not positive, or it sits inside the state-year permutation null.

## Ceiling

Development only. An association here orders a state variable; it does not identify an instrument, and
the queue panel has no position to hold. Even a clean result is a ranking input for the delivery tail,
not a trade.

## Reproduce

    python3 scripts/build_queue_exit_study.py

## Result, 2026-10-04

Run as declared on all 36,441 projects. Crowding is falsified: the pooled correlation between preceding
state MW and withdrawal is -0.171, and the within-state-year high-low gap is +0.0003 (p 0.49), which is
a dead zero. The pooled negative number is a cohort artifact: later requests have more capacity ahead of
them and are also younger, so they have not had time to withdraw. Once cohort and state are held fixed,
crowding orders nothing.

Two other results land. Size has no positive effect within state-year blocks (rho -0.023, p 1.00 in the
declared positive direction). Technology does: the spread between the highest and lowest withdrawal
share among technologies with at least 200 projects is 27.9 points (p 0.018), offshore wind 72.3 percent
against hydro 44.5 percent. The object that T14 hoped would be more predictable is predictable through
what the project is, not through how crowded the queue was when it asked.

p-values here are one-sided for the declared positive direction. A p of 1.00 means the observation sits
at the extreme low tail of the null, and it is reported that way rather than rounded into significance.
