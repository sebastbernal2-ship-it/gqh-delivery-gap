# ADR-001: Custom Incremental Engine

**Status:** Accepted
**Date:** 2026-02-23

## Context

The order book needs to recompute derived values (snapshots, stats)
efficiently when events arrive. A naive approach recomputes everything
on every event. An incremental engine tracks dependencies and only
recomputes what changed.

Jane Street's Incremental library is the obvious choice — it's
battle-tested, efficient, and idiomatic. However:

1. This is an educational project meant to demonstrate understanding
   of incremental computation.
2. The Incremental library has complex dependencies and is tightly
   coupled to Jane Street's Core library.
3. The order book's dependency graph is small (one Var, two Map nodes)
   — far simpler than a full UI or spreadsheet.

## Decision

Implement a minimal custom incremental engine (~200 lines) with:

- Wave-based stabilization for correct topological ordering
- Physical equality cut-off (`==`) by default
- Customizable cut-off via the `cutoff` combinator
- Var → map → snapshot/stats DAG pattern

The engine stores children as direct thunks (closures) rather than
using a node table. This avoids `Obj.t` casts entirely — only one
safe `Obj.magic` in `bind` for forward reference.

## Consequences

- No dependency on Incremental or Core libraries
- 28 tests cover all combinators: map, map2, map3, bind, if_, cutoff
- Wave-based processing ensures topo order: nodes at depth N are
  processed before depth N+1
- Not suitable for large DAGs (work queue is O(n) per stabilize)
- Not thread-safe (single work queue, mutable flags)

## Alternatives considered

### Jane Street's Incremental library
Pros: production-tested, efficient, feature-rich.
Cons: heavy dependency, overkill for a 3-node DAG.

### No incremental (recompute everything)
Pros: simpler implementation.
Cons: O(n) on every event even when nothing changes.

### Event-sourced snapshotting
Pros: naturally bitemporal.
Cons: must replay entire log on restart.