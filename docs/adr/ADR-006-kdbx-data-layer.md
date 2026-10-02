# ADR-006: KDB-X data layer beside the OCaml engine

## Decision

Use KDB-X as an analytical time-series store beside the OCaml replay engine.

Keep the hourly Binance gzip JSONL files as immutable raw evidence.
Validate captures before KDB-X ingestion.
Keep OCaml authoritative for strict sequence validation, replay, and execution.

## Context

The live collector now produces continuous Binance Futures depth data on an OCI ARM VM.
KDB-X is well suited to indexed cross-day time-series queries.
It is not a replacement for the venue-faithful replay rules already implemented in OCaml.

## Data flow

```text
Binance public streams
  -> hourly gzip JSONL raw evidence
  -> capture validation and normalization
  -> KDB-X analytical tables
  -> metrics and research queries
```

Each normalized row keeps the source path and SHA-256 digest.
KDB-X data must remain rebuildable from the raw capture.

## Constraints

KDB-X Community Edition requires a KX Developer Center license.
The OCI ARM VM supports the KDB-X ARM64 build, subject to that license.
KDB-X runtime binaries and license material must not enter this repository.

## Consequences

Queries become fast and convenient across symbols and days.
Raw capture replay remains portable and auditable.
The project maintains two representations and must keep their provenance linked.
