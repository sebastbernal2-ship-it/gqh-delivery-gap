# ADR-003: Bitemporal Model with Closed-Open Intervals

**Status:** Accepted
**Date:** 2026-02-23

## Context

The order book records facts along two time axes: valid time (when
the fact is economically effective) and transaction time (when the
fact was recorded). The interval boundaries need a representation.

## Decision

Use closed-open intervals: `[from, until)`.

- `valid_at` is included if `valid_from <= t < valid_until`
- `tx_at` is included if `tx_from <= t < tx_until`

This is the standard in temporal databases (see Snodgrass,
"Developing Time-Oriented Database Applications"). It avoids
double-counting at interval boundaries and simplifies range queries.

## Consequences

- "Now" is represented as a far-future sentinel (100 years ahead)
- Queries use simple `<` and `<=` comparisons
- No ambiguity at interval endpoints
- Data model matches exchange practice: a trade is valid from fill
  time until superseded, not including the superseding moment

## Alternatives

### Closed-closed [from, until]
Pros: intuitive.
Cons: double-counting at boundaries, harder to sequence correctly.

### Open-open (from, until)
Pros: clean interval math.
Cons: counter-intuitive for temporal queries ("when did it start?").