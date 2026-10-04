# Declared: does the disclosure-surprise forecast predict returns?

Status: development only. Owner: sebas. Date: 2026-10-04. Runner:
`scripts/run_surprise_alpha.py`. Artifact: `results/surprise-alpha.json`.

## Question

The council and the RPO model predict a disclosure surprise. Does that forecast, made only from
information available before the disclosure, predict the return that follows it?

## Entry rule

Enter at the close of the first session strictly after the disclosure's availability date, matching
the strategy's repaired next-session convention. Exit at the close H sessions later, H in 1, 5, 20.
Every feature was available before the disclosure, so the rule is tradable as declared.

## Out-of-sample discipline

The 70/30 chronological split already published for the RPO panel. Only the later 30 percent is
measured, 833 rows and 188 issuers, 96.6 percent with returns in the cached price source. No sealed
rows exist in this panel. Both sealed windows are spent, so this is development evidence.

## Three return variants, because the confound is obvious

1. Raw close to close.
2. Demeaned inside the entry month, which removes the complex-wide trend that lifted every name.
3. Demeaned inside the entry month crossed with the peer group, which also removes a group tilt.

The first result was raw and the neutralised variants were added the same hour after seeing it. That
is recorded here rather than presented as pre-registered.

## Statistics

Mean return by predicted bin, mean return by confidence quintile, Spearman information coefficient
between the expected bin and the realised return, and a long-short spread between the top and bottom
predicted bins at declared round-trip costs of 0, 10, 20 and 40 basis points, each with an
issuer-blocked bootstrap interval over 1,000 resamples.

## First measured result, 2026-10-04

Twenty sessions: raw spread 8.88 percent, interval 1.54 to 16.78; month neutral 5.77 percent,
interval -1.32 to 12.83; month and group neutral 4.71 percent, interval -1.81 to 12.04. The
neutralised bins are the informative shape: the top bin gains 3.24 percent and the bottom bin loses
2.53 percent while the middle bins sit near zero, so the effect lives in the tails, not in a
monotone ladder. The rank information coefficient is near zero at twenty sessions and positive but
small at five, so the signal is not linear in the surprise.

## Falsifier and ceiling

The declared falsifier is a neutralised spread whose interval contains zero, which is the current
state. About 89 traded issuers and overlapping quarterly windows keep the intervals wide. No borrow
cost, no tradeable short availability test, no capacity model, no sizing. A surprise forecast is not
a strategy.
