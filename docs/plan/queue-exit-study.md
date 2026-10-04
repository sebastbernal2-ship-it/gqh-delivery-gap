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
