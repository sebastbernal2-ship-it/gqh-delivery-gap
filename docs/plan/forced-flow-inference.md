# Forced flow inference from trade prints

**Status: development only, declared before the run.** Both sealed windows are spent. The venue publishes no
liquidation flag on trades (confirmed by the capability test), so forced flow has to be inferred. This
declares the inference rule and its falsifier before any candidate is counted.

## Why inference rather than a flag

The trade payload carries coin, side, price, size, time, hash, trade id and two user addresses. It does not
carry a liquidation marker. So "forced seller" is a claim we build from the prints, and it must be labelled
as an inference everywhere it is used.

## The declared rule, version 1

A forced flow candidate is a burst of aggressive trades meeting all of:

1. **Window**: prints within ten seconds of each other.
2. **One side**: every aggressive print in the burst is on the same side (taker buys or taker sells).
3. **Size**: burst notional at or above five times the trailing median burst notional over the previous
   thirty minutes, and at least 250,000 dollars for BTC and ETH, at least 20,000 for the thin markets.
4. **Move**: mid moves at or beyond two trailing standard deviations of ten second returns over the burst.
5. **Repeat**: a taker address in this burst also appears as an aggressor in an earlier burst within the
   previous twenty four hours. Reported as a flag rather than a requirement, because one forced account can
   appear once.

The candidate record carries the burst start and end, side, notional, print count, price move in basis
points, the taker addresses, the repeat flag, and the open interest change across the window.

## What the inference is not

It is not a venue confirmed liquidation, and it is not evidence of reversion. It is a set of prints that
look like forced flow under a stated rule. The economic test comes after: candidates against random times
at the same horizons, net of costs, exactly as the reversion study already does.

## Falsifier

If candidate bursts do not revert more than random times at the same horizons, then either the rule does not
capture forced flow or forced flow does not revert, and the inference is retired rather than tuned.

## Ceiling

Ten second bursts on public prints, no account level margin data, no venue liquidation feed. Repeat
identification is address level and public, so it only sees accounts that trade through the same address
twice. Development only.
