# Multi-session causal tape experiment

Follow-up to [the rejected short candidate](SYNCHRONIZED_TAPE.md). This is development-only
forecast engineering. It does not establish an economic trading edge, executable fill model,
liquidation specialist, queue reconstruction, or quantum advantage.

## Declared before acquisition/outcomes

At the same pinned public archive revision, choose the first two nonpartitioned files in each
book/trade family, ordered by numeric filename timestamp, on each of the first six shared UTC
filename dates. Inspect only names, sizes and publisher hashes for selection. A preliminary
10-second filename-pair tolerance failed on catalog offsets; no price data was involved. The
final rule chooses each family independently and audits actual clocks after downloading.
[The complete pinned plan](multisession_plan.json) totals 630,972,972 bytes, below the 750 MB cap.
The previously inspected five-minute candidate is retained as disclosed development data.

Hypothesis: merging the declared files yields enough valid causal cases across six sessions to
exercise the existing seven-view fitting/calibration/selection pipeline with distinct information
streams. Falsifiers: incompatible schema, conflicting duplicate identities, invalid clocks/books,
empty common coverage, gaps preventing causal cases, or an empty chronological role blocks training.
Missing coverage does not become a zero-trade assertion, and overnight gaps are not filled.

Use the recorded timestamp as an unverified availability proxy, explicitly labelled
`retrospective_assumption`. A contains spread/five-level depth imbalance; B contains reported
B-minus-A observed trade size imbalance and log observed volume over 30 seconds; C contains
five-second midpoint movement and trailing 30-second midpoint realized volatility.
No liquidation field is inferred from trade flow. Same instrument BTC and same target for all views.

Fixed target: midpoint change from the latest valid book known at decision to the latest valid
book known at decision+5 seconds, three bins with +/-1 bp boundaries, ties flat. Label availability
is the five-second horizon endpoint on the same proxy clock. Require a newly recorded future book
and a continuous book history through the endpoint. Decision spacing is six seconds; do not claim
independent cases because trailing histories overlap.

Assign the first two filename-date sessions to training, third to specialist calibration, fourth
to gate fitting, fifth to pool calibration and sixth to development evaluation. Never split a
session across roles. Purge labels that mature at/after the first following-role decision. No
architecture/budget changes after evaluation: existing 3-epoch tiny JevLike models and 100-step
numeric baselines, all seven A/B/C combinations, prevalence prior and equal opinion pools,
existing gate increment rule. Report every declared variant and class counts, regardless of results.
This development evaluation is not the competition holdout owned by the frozen brief.

Only public aggregate provenance, coverage and experiment receipts enter Git. Source objects,
normalized states, label audits, models and individual forecasts stay in local artifacts. Download
by the pinned plan, verify bytes/hash, and feed the adapter independently of Snowflake. This
establishes a source adapter; it does not populate or validate a production warehouse panel.
