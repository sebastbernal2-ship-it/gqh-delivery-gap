# ADR-007: Execution Kernel Units

**Status:** Accepted
**Date:** 2026-10-03

## Context

The Quanthacks execution kernel must compute notionals, fees, funding, P&L, margin, and liquidation exactly.
The existing backtest and account modules use `float`, which accumulates rounding error and cannot be hashed into a reproducible fixture contract.
ADR-004 fixes order-book prices at 1e-4 ticks.
The kernel needs one declared unit policy covering price, quantity, money, and rates.

## Decision

Use int64 fixed-point units, one scale per quantity class.

| Class | Unit | Scale | Maximum |
| --- | --- | --- | --- |
| price | 1e-4 ticks | 10^4 | 214,748.3647 (ADR-004) |
| quantity | 1e-6 units | 10^6 | 9.2e12 |
| money | 1e-8 units | 10^8 | 9.2e10 |
| rate | 1e-8 fraction | 10^8 | 9.2e10 |

Price ticks match ADR-004 and `Price.t`, so the book engine and the kernel share one price scale.
`Exec_units` owns these conversions and the arithmetic.

Notional is `price_ticks * quantity_units / 100`.
The product is never formed directly: the multiply decomposes into a whole part and a remainder part, so intermediate values stay in int64 and the result stays exact.
Rounding is half away from zero at 1e-8 money granularity.
A fee at `b` basis points is `money * b / 10_000` under the same rule.

Decimal strings convert to units only at the ingestion boundary.
Conversion fails closed on over-precision, malformed digits, misplaced signs, or overflow.
`Binance_units` owns venue step and lot alignment; `Exec_units` owns the fixed engine scales.
Refusal to compute is always an error value, never a wrapped or truncated number.

## Consequences

- Arithmetic is exact, hashable, and reproducible across machines.
- Quantity precision of 1e-6 covers every Binance Futures lot step with margin.
- A notional beyond the declared range fails closed with an overflow error.
- Float remains only in legacy modules, display code, and ingestion adapters.
- The float-based `Binance_account`, `L2_execution`, and `L2_backtest` modules are replaced by the fixed-point kernel in Phase 4 of `orderbook-engine/docs/quanthacks-backtester-plan.md`.

## Alternatives

### Float
Rejected: rounding drift breaks reproducibility and fixture hashing.

### Quantity at 1e-8
Rejected: the decomposed notional multiply would overflow for large positions, and no venue lot step needs the extra digits.

### Arbitrary-precision decimal (Zarith)
Rejected: a heavy dependency for scales that fit int64 inside declared ranges.
