# Declared study: forced flow reversion at zero latency advantage

**Status: development only, declared before the run.** Both sealed windows are spent. This study reads a
recorded tape and says so.

## The link

The cascade family claims: a forced seller creates a dislocation, and the dislocation reverts far enough
to pay for entering after the flow, without being first. That claim has two parts and this study tests
the second: the reversion net of costs, entered on the bar close after the condition, at no speed
advantage. The first part, finding the forced seller, is the identity problem, and it stays open.

## Data

The recorded tape in `data/tape`, six files, four markets (BTC, ETH, GAS, SPX), roughly fifteen second
cadence, 7.3 hours of nominal window. Fields used: mid, spread in basis points, ten basis point depth,
funding, open interest. The tape is local and ignored by git, so this is a description of one window and
not a backtest.

## Declared condition ladder

All levels reported, including the ones that fire rarely.

- **L1**: the frozen cascade rule, a three trailing sigma move with a one percent open interest fall.
- **L2**: the largest one percent of absolute one minute moves within the market.
- **L3**: the largest five percent.
- **L4**: funding beyond two trailing standard deviations.
- **L5**: depth inside ten basis points below its twentieth trailing percentile.
- **L6**: L2 and L5 together, a dislocation with a thin book.

## Entry and accounting

Entry is the close of the condition bar, so no speed advantage is used. Horizons are one, five and
fifteen minutes in bars. Costs are the taker fee plus half the measured spread, charged on both sides,
reported at base and doubled. Direction is reversion against the move for L2, L3 and L6, and against the
extreme funding side for L4. L5 is a filter and is reported with and without direction.

## Statistic and null

Mean and median net reversion per market and pooled. The null shuffles event times within each market,
five thousand draws. Event counts and median depth at the events are reported so the trigger rate and the
capacity are visible, not implied.

## Falsifier

No declared level shows positive net reversion beyond its null.

## Ceiling

One recorded window, four markets, one venue. A positive result here is a candidate, not an edge. A null
result is a fact about this window and this condition ladder.

## Reproduce

    python3 scripts/build_cascade_reversion_study.py

## Result, 2026-10-04

Run as declared over all six tape files, four markets, one venue, 7.3 nominal hours.

The percentile levels do not clear costs. Top one percent moves (103 events), top five percent (490
events), funding beyond two sigma (769 events) and thin books (2,139 events) all land between -8 and
-22 basis points net of base costs, with gross means of at most +3.9 basis points at fifteen minutes,
and every one of them sits inside its random-time null.

The frozen conjunction is the exception. It fired six times (BTC 1, ETH 1, GAS 2, SPX 2). Gross
reversion at fifteen minutes is +17.9 basis points, +6.9 net of base costs and -4.0 net of doubled
costs, with a permutation p of 0.085. Six events decide nothing on their own, and the doubled cost line
is negative.

Reversion is market specific: on the same top one percent level, SPX shows +14.7 basis points gross at
fifteen minutes and GAS shows -4.0. The binding constraint in this family is the cost hurdle, which sits
near ten basis points round trip, and the conjunction is the only condition whose gross clears it.

The next objects are therefore more events and cheaper entry: a maker fill candidate tested against the
recorded book, not wider level ladders.
