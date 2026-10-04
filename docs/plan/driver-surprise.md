# Declared: expectation gaps on the strategy's own drivers

Status: development only. Owner: sebas. Date: 2026-10-04. Runners:
`scripts/build_driver_vintages.py`, `scripts/run_driver_surprise.py`. Artifacts:
`results/revenue-surprise.json`, `results/capex-surprise.json`.

## Question

The RPO concept proved the vintage machinery on names the strategy does not trade, and only 17 of
the strategy's 88 names appear in that panel. Does the same point-in-time seasonal expectation gap
exist on the strategy's own quarterly drivers, capex and revenue, and does the forecast predict the
return that follows the disclosure?

## Method

Same declared machinery: same-quarter mean of prior changes as the expectation, minimum two prior
same-quarter observations, relative surprise as the label in five declared bins, prior-history
features only, 70/30 chronological split, entry at the close of the first session after the
disclosure, exits at 1, 5 and 20 sessions, costs at 0 and 20 basis points round trip, and the three
return variants from `docs/plan/surprise-alpha.md`: raw, month neutral, month and group neutral,
each with an issuer-blocked bootstrap interval.

Availability is the earliest filing that reported the quarter, median lag 34 days for capex and 36
for revenue. The corrected panels are described in `docs/plan/intensity-clock-test.md`.

## First measured result, 2026-10-04

Revenue, 509 out-of-sample rows over 55 issuers, log loss 1.5667 against the prevalence 1.5868,
accuracy 0.332. Twenty sessions, long-short by predicted bin: raw +9.35 percent, interval +3.19 to
+18.21; month neutral +11.35, interval +6.59 to +17.06; month and group neutral +4.75, interval
+1.13 to +9.28. Five sessions +1.80 with an interval crossing zero; one session nil.

Capex, 239 rows over 55 issuers, log loss 1.2438 against 1.2614. Twenty sessions, month and group
neutral: **-4.87 percent**, interval -10.51 to -1.34. The sign is the strategy's own: a capex
surprise is bad for the near-term return, which is why the intensity expression is short high
intensity names.

## Falsifier and ceiling

The declared falsifier is a neutralised spread whose interval contains zero. Revenue and capex both
clear it at twenty sessions. The ceiling is unchanged: 55 issuers, overlapping quarterly windows,
one price source, no borrow and no capacity model. This measures an event reaction, not a strategy.
