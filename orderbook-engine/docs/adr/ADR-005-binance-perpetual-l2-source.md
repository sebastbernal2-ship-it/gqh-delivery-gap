# ADR-005: Binance perpetual L2 validation source

## Decision

Use Tardis Binance Futures incremental L2 data as the primary free perpetual-futures replay source.

Use its generated depth snapshots to establish a book and its raw depth updates to advance the book.

Use the public sample dates that require no API key.

Keep Binance L2 evidence separate from order-level FIFO evidence.

## Evidence

The Tardis Binance Futures feed exposes BTCUSDT perpetual incremental book data from 2019-11-17.

The raw feed includes update IDs, previous update IDs, exchange timestamps, receive timestamps, bid changes, and ask changes.

A public sample request for January 1, 2024 returned 1,086 depth updates and a generated top-1000 snapshot.

The replay check reached final update ID 3751162949582 without a sequence gap.

## Consequences

This source supports multi-day perpetual L2 replay, depth behavior, spread behavior, and gap validation.

It does not expose individual order identities, so it cannot prove FIFO priority.

FIFO and order-lifecycle tests remain deterministic order-level fixtures.
