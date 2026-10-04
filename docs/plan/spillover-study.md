# Declared study: cross market behaviour at dislocation events

**Status: development only, declared before the run.** Both sealed windows are spent. Every cascade test
so far traded the same market that moved. This study asks what the other markets do at that moment, and
whether a dislocation in one is cleaner to express in another.

## The object

At a dislocation event in market X, the forward behaviour of market Y. Two readings are possible and both
are informative: the dislocation spills over and continues in Y, or Y mean reverts with X. Either way, the
cross market expression is measured on its own terms, with its own depth and spread.

## Data and levels

The recorded tape, four markets (BTC, ETH, GAS, SPX), events at the top one percent and top five percent
of one minute moves per market, the same levels as the reversion study. Timestamps are matched to the
nearest sample within thirty seconds.

## Accounting

Entry in market Y is a taker entry at the sample nearest the event, in the reversion direction of X's
move, and the exit is a taker exit at four, twenty and sixty bars of Y. Costs are the taker fee plus half
the measured spread on both sides, base and doubled. Depth inside ten basis points at entry is reported,
because capacity decides whether a result is usable at all.

## Statistic and null

Mean and median net basis points for every ordered pair X to Y, with the same market pair included as the
baseline, and event counts per pair. The null draws random entry times per market with the same direction
rule, five thousand times, and the p value compares the observed mean against it.

## Falsifier

No ordered pair shows positive net basis points beyond its null.

## Ceiling

One venue, one window, fifteen second snapshots. Only BTC and ETH carry meaningful depth, so GAS and SPX
results describe direction rather than capacity.

## Reproduce

    python3 scripts/build_spillover_study.py

## Result, 2026-10-04

Every entry into BTC or ETH nets negative at both levels, between -7.0 and -10.3 basis points on the
median, and the same market cells are negative too. Cross market entry does not rescue the family.

The only positive cells enter the thin markets. At the top five percent level, ETH events followed by an
SPX position net +5.9 basis points on 126 events (p 0.013), and at the top one percent level ETH followed
by GAS nets +5.4 on 28 events (p 0.0016). The median depth at those entries is 3,400 and 1,489 dollars.

The sign convention matters here: the target is entered against the source's move, so these positive
cells mean the thin targets move against the source dislocation over the following fifteen minutes.

Two facts follow. Cross market entry into the liquid markets is retired as an expression of this family,
and the thin market cells are recorded as structure with trivial capacity, which needs a larger venue
before they are anything more than a monitor.
