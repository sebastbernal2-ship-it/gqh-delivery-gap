# ADR-004: Price Representation (Integer × 10000)

**Status:** Accepted
**Date:** 2026-02-23

## Context

Market prices need exact arithmetic — floating-point rounding errors
are unacceptable for financial applications. The choice of
representation affects all price-sensitive computations.

## Decision

Represent prices as integers with a fixed decimal scale of 10,000
(four decimal places). `Price.of_float 100.50` becomes `1_005_000`.

The scale of 10,000 matches common exchange practice (e.g., CME
price increments of 0.0001 for many products). It avoids the
binary-rational issues of floating-point scales while keeping
arithmetic purely integer-based.

## Consequences

- All price arithmetic is exact (`+`, `-`, `*` on integers)
- Comparison is integer comparison — fast and exact
- Price range: 0.0001 to 214,748.3647 (32-bit signed int)
- Conversion to/from float for display and CSV I/O
- No support for sub-0.0001 increments (adequate for equities)

## Alternatives

### Float
Faster, but accumulates rounding errors. Unacceptable for
bid/ask spread comparison.

### Decimal string
Exact but slow for arithmetic. Common in accounting software
but awkward for an order book that needs frequent price compares.

### Custom fixed-point integer
Essentially the same as chosen, but with a different scale.
10,000 is standard for 4-decimal financial products.