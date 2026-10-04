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
