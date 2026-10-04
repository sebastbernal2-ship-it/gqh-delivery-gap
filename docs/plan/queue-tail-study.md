# Declared study: does queue timing order the delivery tail?

**Status: development only, declared before the result.** Both sealed windows are spent and are not
touched. Nothing in this study may be called out of sample, and nothing here is an instrument test.
The protocol is committed before the run; the result is reported whatever it says.

## The question

Among queue projects matched to EIA generators, does the time a project spent from interconnection
request to signed agreement order the delivery tail (a slip of six months or more) and exits
(cancellation)? The first probe showed a weak positive rank correlation on 65 joined pairs. This
study declares the test in advance so the probe's choices cannot become the result.

## Population and matching rule

- EIA plants matched in `results/queue-crosswalk.csv` with `match = yes`.
- One queue record per plant: the record with the earliest `q_date`, because that is the project's
  original queue entry. Its `days_ir_to_ia` is the feature.
- Outcomes from `results/promise-survival.csv` (per generator, aggregated to the plant by maximum
  slip) and `results/delivery-revisions.csv` (a cancellation row for the plant).
- Plants without a queue duration or without a survival row are excluded, and the excluded count is
  reported.

## Declared features, outcomes and split

- Feature: `days_ir_to_ia`.
- Primary outcome: tail, the plant has any generator slip of six months or more.
- Secondary outcome: exit, the plant carries a cancellation or postponement row.
- Split: the population median of `days_ir_to_ia`, fixed at the median and nothing else. The study
  reports the tail share in the slower and faster halves.

## Null and multiplicity

- Null: the same test with queue durations permuted within state groups, 5,000 draws. The state
  conditioning matters because queue waits differ by region.
- Two tests are declared, the tail and the exit, and both are reported. No other split, threshold or
  subset may be searched; anything else would be a new study.

## Ceiling

Descriptive only. The design measures an association between a procedural wait and a later outcome.
It does not identify a payer, does not test an instrument, and does not charge costs, so causal
language and tradability claims are both refused.

## Falsifier

The tail share does not rise with queue duration in the slower half, or the observed difference sits
inside the state-conditioned permutation null.

## What this cannot conclude

Who holds the exposure, whether any expression survives costs, and whether the association holds out
of sample. All three need things this study does not have.

## Reproduce

    python3 scripts/build_queue_tail_study.py
