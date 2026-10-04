# Jane Street Readiness Assessment

## Status as of v0.2.0

The following gaps from the original audit (recorded during v0.1.0 development)
have been **resolved**:

- **Missing .mli files**: 15 of 16 modules have interfaces (only cli.ml, the
  executable entry point, lacks one — acceptable convention).
- **`wrapped false` in dune**: never present in current code.
- **Event loop O(n²) via List.nth**: uses `Array.of_list` + O(1) index access
  since v0.2.0.
- **WebSocket JSON hand-rolled**: uses `Yojson` since v0.2.0.
- **Incr engine uses `Obj.t`**: engine uses typed nodes, no `Obj.t`, no
  `Hashtbl`, no unsafe operations.
- **Deprecated `allow_approximate_merlin`**: never present.
- **Order book O(n) per price level**: uses `Order_id.Map` per level (O(log n)).
- **No README, ADR, CONTRIBUTING**: all exist with 4 ADRs.
- **Incr `cutoff` combinator**: implemented.
- **No expect tests**: `ppx_expect` tests exist in `test/expect_test.ml`.
- **Spread/mid code duplication**: `compute_spread_mid` extracted as shared
  helper.
- **`module List` shim in cli.ml**: removed in v0.2.0.
- **Benchmark lacks structure**: has warmup, iterations, min/max/mean/stddev.
- **Sexpr serialization gaps**: fixed for `BookSnapshot` and `StatsUpdate`.
- **`take` duplicated**: extracted into `List_utils` shared module.
- **dune-workspace present**: exists.

## Remaining gaps

### P1 — Would be fixed during first month

1. **Order-book incremental engine scope**: resolved by capturing a fresh
   `Incr.make()` instance inside each `Order_book.create` call.
2. **Bitemporal queries O(n)**: full-list iteration for most queries.
   `index_by_order_id` exists but is only used when `--order-id` flag is
   passed to the CLI `query` command. Range queries remain O(n). Acceptable
   for moderate data volumes.
3. **Stdlib vs Base usage**: inconsistent. A few modules use qualified `Base`
   calls (`market_data.ml`, `market_types.ml`) but most use stdlib `List`,
   `Printf`, `String`. Not a blocker — it's pragmatic for a project that
   depends on Lwt, Cmdliner, and other stdlib-oriented libraries.
4. **Error handling via Serror**: used pervasively in library modules but
   `cli.ml` still hand-matches `Ok`/`Error` patterns. Acceptable for a
   CLI entry point.
5. **Event loop mutable state**: `position`, `running`, `speed`, `handlers`
   are mutable fields. Acceptable for a side-effect-driven event loop.

### P2 — Senior polish

6. **No LICENSE file**: resolved with MIT license in v0.2.1. (✓ Resolved)
7. **Bitemporal index wired into CLI**: resolved — `--order-id` flag uses
   `index_by_order_id` + `history_of_order`. (✓ Resolved)
8. **CLI.mli**: added in v0.2.1. (✓ Resolved)
9. **No git repo**: initialized in v0.2.1 with initial commit. (✓ Resolved)
10. **Version in dune-project**: added to both packages. (✓ Resolved)
11. **README badges**: CI, license, OCaml version badges added. (✓ Resolved)

### Verdict

The project is **Jane-Street-interview-ready**. No P0 items remain.
A reviewer would see well-structured OCaml with disciplined patterns:
module interfaces, ADR-driven architecture, multiple test methodologies,
immutable state, DAG-based incremental computation, bitemporal model.
The remaining gaps (Base consistency, mutable event loop state) are
recognizable as pragmatic tradeoffs in a small project, not design flaws.

## Checklist

- [x] Every `src/*.ml` has a corresponding `.mli` (except cli.ml)
- [x] Zero build warnings
- [x] `wrapped false` not present
- [x] Incr has `cutoff` combinator, safe bind, no Obj.t, no global state
- [x] Each order book owns an independent `Incr.Make()` instance
- [x] Event loop uses indexed array, not List.nth
- [x] WebSocket uses Yojson
- [x] Bitemporal has order_id index (wired into CLI)
- [x] Order book uses OrderMap per price level
- [x] Expect tests exist (ppx_expect)
- [x] No code duplication (take, spread helpers extracted)
- [x] Error handling uses Serror.t in library code
- [x] README.md, 4 ADRs, CONTRIBUTING.md, CHANGES.md exist
- [x] Benchmark supports warmup + iteration
- [x] LICENSE file (MIT)
- [x] Git repo initialized with initial commit
- [x] dune-project has version (both packages)
- [ ] Full Base/Core migration (partial — qualified calls where needed)