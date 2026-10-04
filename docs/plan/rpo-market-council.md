# Declared: the council over two distinct data bundles on the RPO panel

Status: development only. Owner: sebas. Date: 2026-10-04. Runner:
`scripts/run_rpo_market_council.py`. Artifact: `results/rpo-market-council.json`.
Recorded with its first result on the same day the comparison was designed in code.

## Question

On the point-in-time RPO panel, does a council over two genuinely distinct data families beat every
single family and naive concatenation, and does each family carry unique information?

## Bundles, not architectures

`issuer_facts` reads what the issuer disclosed about its own obligations: the declared seasonal
history features and the filing metadata features. `market_state` reads the tape into the
disclosure: trailing returns at 60 and 252 days, realised 60-day volatility, the 5-day pre-event
drift, distance from the 252-day high, and both returns measured against the issuer's peer-group
median. The two bundles share no input.

Point-in-time rule: every market feature uses bars strictly before the decision date, so the
decision-day close, the disclosure reaction and anything later are excluded by construction.
Insufficient history is a null, never a zero.

## Split and fusion

Five chronological blocks, 42/10/10/10 percent for training, specialist calibration, gate fit and
pool calibration, the remainder for evaluation, with no boundary splitting a shared timestamp.
Linear opinion pool. The concatenation reference is one specialist over the union of the features,
trained on the same 42 percent, so the data budget is identical.

## Diagnostics, all declared before the run

1. Incremental information: council log loss against the best single bundle and against
   concatenation, each with an issuer-blocked bootstrap interval, 1,000 resamples.
2. Redundancy: total-variation distance between the bundle distributions, the correlation of their
   top probabilities, and their argmax agreement.
3. Marginal contribution: the leave-one-out council log loss when a bundle is dropped.
4. Decision view: the ordinal-payoff utility of the council under the declared cost grid.

## Ceiling

RPO names only, quarterly disclosures, price-based market bundle, no text and no option-implied
state in this comparison. Both sealed windows are spent. This measures disclosure surprises, not
returns.
