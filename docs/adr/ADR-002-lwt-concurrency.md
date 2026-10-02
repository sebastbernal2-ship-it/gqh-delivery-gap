# ADR-002: Lwt over Async/Eio for Concurrency

**Status:** Accepted
**Date:** 2026-02-23

## Context

The simulator needs concurrent I/O: a WebSocket server and an
event replay loop. OCaml has three main concurrency libraries:
Lwt, Async, and Eio.

## Decision

Use Lwt because:
- Simplest API for basic concurrent I/O (WebSocket + replay)
- Works with OCaml 5.2.0 without domain support
- Lightweight integration with Lwt_unix for raw socket operations

## Consequences

- Not suitable for multi-core parallelism (no Domainslib support)
- Lwt_list.iter_p for fan-out to multiple WebSocket clients
- No benefit from OCaml 5.x domains

## Alternatives

### Async
Comparable to Lwt but slightly heavier.

### Eio
OCaml 5.x native, better for multi-core, but less mature ecosystem.