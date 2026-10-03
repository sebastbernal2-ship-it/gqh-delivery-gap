# Pre-registered protocol: forced deleveraging on a perpetual venue

**Committed before any tape was collected.** The git commit that adds this file precedes the first sample in
`data/tape/`. Nothing here may be changed after data arrives; a change would be written as a new protocol
with its own commit and its own collection window.

## Why this object

A leveraged position is closed by the venue's engine when maintenance margin is crossed, so the resulting
flow is price insensitive by rule rather than by opinion. The candidate edge is not speed. It is the
conditional distribution of the path **after** the threshold fires, which is a modelling question, while
speed is only what lets a participant be present. The measurement therefore asks a distribution question
about a mechanical event.

## What is collected, and only this

| Field | Source | Cadence |
|---|---|---|
| Best bid, best ask, and the ten levels each side with sizes | public order book endpoint | every 15 seconds |
| Funding rate, open interest, oracle price, mark price | public asset context endpoint | every 15 seconds |

Markets, declared in advance: **BTC, ETH, GAS, SPX**. Nothing else is added to the tape after collection
starts, and no field is added retroactively.

## Trigger, declared

A **cascade trigger** in a market is one sample where both hold:

1. the mid price return exceeds **3 times** the trailing 60 sample standard deviation of returns (15 minutes),
   in absolute value; and
2. open interest falls by at least **1 percent** against its trailing 60 sample median.

The conjunction is required because a large move alone is an announcement, and an open interest fall alone is
a quiet unwind. Neither is a cascade.

## Measurements after a trigger

Mid price path at **+1, +5, +15 and +60 samples** (15 seconds, 75 seconds, 4 minutes, 15 minutes), funding
change, basis change (mark minus oracle), and book imbalance change. Reported as distributions, not means
alone.

## Two structural tests, declared

1. **Clustering.** Trigger counts per hour are compared against a Poisson null with the same rate. Overdispersion
   is evidence for self excitation and the threshold story; Poisson counts would falsify it.
2. **Refractoriness.** The distribution of inter-trigger intervals is compared against the exponential
   distribution implied by Poisson arrivals. Fewer short intervals than exponential implies a refractory
   period, which is what a threshold population produces.

## Costs and capacity, declared

- **Taker cost: 4.5 basis points per side**, used in every net figure and doubled in a second pass. This is an
  assumption to verify against the venue's published schedule before any conclusion is drawn.
- **Capacity is measured, not assumed.** Each book snapshot gives the notional available within 10 basis
  points of mid, which bounds how large a position could be taken without moving the price beyond that.

## Falsifiers, declared

- Post-trigger reversion is indistinguishable from the same market's unconditional 60 sample returns.
- Trigger counts are Poisson, so there is no clustering and no threshold structure.
- The notional available within 10 basis points is too small to matter after costs.

## What this protocol cannot conclude

A tape of hours is a description of that window, not a backtest. No result from it may be described as a
strategy, and any conclusion drawn from it must name its sample length. The historical archive, which is
separate and currently unreachable from this checkout, is what would support a longer study.
