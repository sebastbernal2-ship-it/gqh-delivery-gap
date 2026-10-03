# Verdict on the forced liquidation chain, and what remains

## The chain, scored

| Gate | Result |
|---|---|
| 1 constrained counterparty | passes: a leveraged account closed by the venue's own maintenance margin rule |
| 2 price insensitive flow | passes: the close is mechanical and arrives whatever the price |
| 3 transfer concentration | passes: the instrument is the object the flow clears in, so dilution is zero |
| 4 instrument without dilution | passes: the perpetual itself, holdable, with measured capacity of 3.3m per side in BTC within ten basis points |
| 5 economics | **fails on the evidence available** |
| 6 barrier | plausible but untested: absorbing cascades needs fast disciplined execution, and the operation is the barrier |

## Why gate five fails, stated precisely

The fuel series, the flagged share of gross exposure by day, is real and it leads. It predicts the size of the
next move at a rank correlation of plus 0.292, and it peaked at 30 percent of gross exposure on 2025-10-09, the
day before the largest cascade on record. The date convention is settled by that same window: the row for a day
describes the state at its start, because the flag leads rather than follows.

The economics do not follow from the state. Measured on hourly bars from the signal, net of nine basis points
round trip: one hour minus 0.44 percent, four hours minus 0.79, twenty four hours minus 1.04, forty eight hours
minus 8.42. **There is no reversion to harvest, there is continued fall-through**, and the four largest hourly
drops in the window were followed by minus 1.54, minus 0.20, minus 1.92 and plus 1.84 percent, which is a coin
flip at short horizon.

## The binding limit is event count, not model quality

One spike in an eleven month panel. The median day flags 0.31 percent of gross exposure, and only a handful of
days cross ten percent. A state variable that fires a few times a year cannot be validated, only observed. No
additional modelling changes that.

## What the panel can and cannot answer

**Can**: who is leveraged, how leveraged, how much gross sits flagged, and how that changes by day.

**Cannot**: which asset each account holds. The panel is per account, not per position, so the cross sectional
test by asset is not available in it. That is a coverage fact, not a modelling choice.

## What remains, in order

1. **Forward collection**, which is running: the next spike gets measured live against a rule declared in advance,
   independently of the panel author's flag.
2. **The other four chains**, each blocked by a specific missing thing: queue history, option chains, a
   concentrated name set, or counterparty documents.
3. **The verdict itself as a result**: a forced flow with a direct instrument, a leading state variable, and no
   cost-surviving expression is a finding about this market at this size, and it is reportable.
