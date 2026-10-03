# t-delivery-gap: announced capacity is not energized capacity

- **Status.** parked (the team's direction moved; kept because the measurement is real and the
  thesis may return as a component of something else)
- **Owner.** sebastbernal2-ship-it
- **Written.** 2026-10-02, parked 2026-10-03

## The claim

The AI capex complex is priced on announced capacity. Capacity is only deliverable when it is
energized, and power is the binding constraint, so the announced schedule slips in a way that is
published monthly and unread. Trade the spread between the names that can deliver and the names
priced as if they already had.

## Who pays

The momentum and index buyer who must own the announcement, the developer capitalizing an
unpublishable pipeline, and the option seller who prices a disclosure window as continuation.

## The state variable

The MW weighted transport cost between the promised and realized energization date distributions,
per balancing authority, from monthly EIA-860M vintages. Measured, not assumed:
`results/e0_state.json`. Three comparable cohorts give W1 of 3.11, 2.70 and 2.74 months, median 1
to 2 months, cancellation share 2.4 to 4.4 percent, with ERCOT the widest gap.

## Falsifiers

1. The gas-and-nuclear versus solar-and-storage factor explains the pair, so it is a technology
   spread and not a delivery claim.
2. Market beta explains it.
3. It is already priced because the power-bottleneck theme is well known and the constraint names
   trade rich. This is the most serious objection: the edge must be the measurement, not the theme.
4. Rising regional transport cost does not predict the regional pair's underperformance net of
   costs.

## Evidence

`results/e0_state.json`. Code in `src/delivery/`. Reproduce with `make all`.

## Known limits

EIA's own note says the data is preliminary, not fully verified, and that status and commercial
operation date can disagree. Facilities under 1 MW are excluded. Behind-the-meter turbines at data
centers are not in the dataset. 184 to 211 units per cohort are still censored, so the delay is a
lower bound. MISO and PJM reporting zero cancellations needs a check before the cross-region spread
is trusted.

## Why it is parked, not deleted

The measurement pipeline is tested and reproducible, and the constraint logic (a promised schedule
against a physically deliverable one) is reusable even if the trade expression changes. Delete it
only if the new direction makes the measurement irrelevant, and say so in the ledger.
