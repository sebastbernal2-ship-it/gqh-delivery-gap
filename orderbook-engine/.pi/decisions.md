# Project Decisions

Persistent decision log. Every decision here was made by the user.
Read this file at the start of every session to know what is already decided.
Do not re-ask what is already decided here.

---

## 2026-09-23: Implement the full hardening pass: separate replay from simulation, add event identity and sequence metadata, fix the synthetic generator, strengthen bitemporal behavior, and make benchmarks and regression tests pass.

**Decision:** Implement the full hardening pass: separate replay from simulation, add event identity and sequence metadata, fix the synthetic generator, strengthen bitemporal behavior, and make benchmarks and regression tests pass.
**Context:** The project needs both conceptual separation and code-level validation before real-data replay can be trusted.
**Alternatives considered:** A foundation-only pass would defer bitemporal and benchmark work; a real-data adapter first would require choosing a venue and feed before stabilizing the core.
**Source:** user: Full hardening

---
## 2026-09-23: Use SonarX public Hyperliquid L2 snapshots as the historical market-data source.

**Decision:** Use SonarX public Hyperliquid L2 snapshots as the historical market-data source.
**Context:** The goal is free historical perp order-book data; SonarX provides CC0 top-20 L2 snapshots without an API key, despite requester-pays S3 access.
**Alternatives considered:** Official Hyperliquid archive and Reservoir are also requester-pays; paid full-depth L4 data was not selected.
**Source:** captain: proceed on SonarX

---
## 2026-09-23: Use the public Hugging Face Hyperliquid L2 samples and HiPerGator capture instead of direct SonarX S3 downloads.

**Decision:** Use the public Hugging Face Hyperliquid L2 samples and HiPerGator capture instead of direct SonarX S3 downloads.
**Context:** The project must avoid requester-pays AWS charges while still getting historical L2 data and future L3 data.
**Alternatives considered:** Direct SonarX S3 is not guaranteed zero-cost; paid full-depth providers were not selected.
**Source:** captain: proceed then

---
## 2026-09-23: Focus the project on a venue-faithful order-book replay and execution engine, not trading strategies or strategy performance.

**Decision:** Focus the project on a venue-faithful order-book replay and execution engine, not trading strategies or strategy performance.
**Context:** The current strategy example is only a smoke test and distracts from the primary goal of accurate order-book backtesting.
**Alternatives considered:** Keep strategy runner as the main product; rejected until the market-data, replay, matching, timing, and accounting layers are solid.
**Source:** captain: true solid order book backtesting engine

---
## 2026-09-23: Treat incomplete NYSE captures as untrusted and fail closed at the pcap, packet, mapping, and symbol-sequence boundaries.

**Decision:** Treat incomplete NYSE captures as untrusted and fail closed at the pcap, packet, mapping, and symbol-sequence boundaries.
**Context:** The real NYSE PCAP has multiple UDP channels, missing symbol mappings, and packet gaps. Continuing replay would create false book state.
**Alternatives considered:** Continue with synthetic mappings or skip gaps, rejected because they would claim accuracy the capture cannot support.
**Source:** production-readiness research loop

---
## 2026-09-23: Treat the single public NYSE PCAP as a decoder and failure-handling fixture only, not as the primary validation dataset.

**Decision:** Treat the single public NYSE PCAP as a decoder and failure-handling fixture only, not as the primary validation dataset.
**Context:** A one-day incomplete capture cannot support broad venue-accuracy claims or production validation.
**Alternatives considered:** Using it as the main dataset was rejected because it lacks complete mappings and packets.
**Source:** captain clarification

---
## 2026-09-23: Use Binance Futures bookDepth files as multi-day perpetual-futures L2 fixtures, not as evidence for order-level FIFO accuracy.

**Decision:** Use Binance Futures bookDepth files as multi-day perpetual-futures L2 fixtures, not as evidence for order-level FIFO accuracy.
**Context:** The public Binance files are free and multi-day but contain aggregated depth snapshots without individual order identities.
**Alternatives considered:** Treating them as order-level history was rejected because it would overstate FIFO and lifecycle evidence.
**Source:** Binance data source inspection

---
## 2026-09-24: Deploy the live Binance collector to an Oracle Cloud Always Free VM using Docker Compose.

**Decision:** Deploy the live Binance collector to an Oracle Cloud Always Free VM using Docker Compose.
**Context:** The collector must run continuously outside the development machine without paid data or API credentials.
**Alternatives considered:** Managed free containers may sleep or lack durable storage; Cloudflare adds stateful WebSocket complexity.
**Source:** deployment target selection

---
## 2026-09-27: Use KDB-X as an optional analytical data layer beside the OCaml replay engine while retaining raw gzip evidence and OCaml as replay authority.

**Decision:** Use KDB-X as an optional analytical data layer beside the OCaml replay engine while retaining raw gzip evidence and OCaml as replay authority.
**Context:** The collector now runs continuously, and KDB-X is better suited to cross-day time-series queries without replacing strict venue-faithful replay.
**Alternatives considered:** Replacing the OCaml data and replay path with q would weaken the existing typed fail-closed validation and raw-evidence workflow.
**Source:** user clarification: data layer only

---
## 2026-09-28: Implement the KDB-X to OCaml Binance replay bridge and aggregated L2 replay path first, then add execution realism and capture quality controls.

**Decision:** Implement the KDB-X to OCaml Binance replay bridge and aggregated L2 replay path first, then add execution realism and capture quality controls.
**Context:** The project now has raw capture normalization and KDB-X storage, but no engine feed bridge and no faithful aggregated Binance replay path.
**Alternatives considered:** Starting with maker queue modeling was rejected because it depends on a validated replay path and trade data.
**Source:** user: Proceed after architecture gap review

---
## 2026-10-03: Use Tiger Cloud as the primary research store for Quanthacks, while keeping raw captures and the OCaml replay engine separate.

**Decision:** Use Tiger Cloud as the primary research store for Quanthacks, while keeping raw captures and the OCaml replay engine separate.
**Context:** The project now needs many heterogeneous data types and agent-queryable research workflows, while the replay engine must remain venue-faithful and auditable.
**Alternatives considered:** Replacing OCI immediately was rejected because the running VM may serve another competition; keeping Tiger as analytics-only was rejected because it would not solve the heterogeneous research-store requirement.
**Source:** socratic: Tiger role decision

---
## 2026-10-03: Accept the phased Quanthacks backtester plan owned by orderbook-engine/docs/quanthacks-backtester-plan.md: Tiger Cloud as the research store, OCaml as the correctness authority, an event-driven fixed-point execution kernel, and a Rust port only after profiling.

**Decision:** Accept the phased Quanthacks backtester plan owned by orderbook-engine/docs/quanthacks-backtester-plan.md: Tiger Cloud as the research store, OCaml as the correctness authority, an event-driven fixed-point execution kernel, and a Rust port only after profiling.
**Context:** The re-audit showed strong replay foundations but float-based account math, snapshot-driven backtesting, no order lifecycle latency, and no ingested Quanthacks fixtures. The captain wants a realistic backtester reusable and embeddable for Quanthacks.
**Alternatives considered:** A broad Rust or C++ rewrite was rejected because the correctness gap is in the model, not the language. Keeping KDB-X as the primary store was rejected in favor of Tiger Cloud. A snapshot-only backtest extension was rejected because it cannot model capital, liquidity, or latency.
**Source:** socratic: Quanthacks backtester architecture and scoping

---
## 2026-10-03: Use int64 fixed-point units in the execution kernel: price 1e-4 ticks, quantity 1e-6 units, money 1e-8 units, rate 1e-8 fraction, with checked overflow and half-away-from-zero rounding; decimals convert to units only at the ingestion boundary.

**Decision:** Use int64 fixed-point units in the execution kernel: price 1e-4 ticks, quantity 1e-6 units, money 1e-8 units, rate 1e-8 fraction, with checked overflow and half-away-from-zero rounding; decimals convert to units only at the ingestion boundary.
**Context:** Phase 1 of the Quanthacks backtester plan. The execution kernel must compute notionals, fees, funding, P&L, margin, and liquidation exactly, and the float-based legacy modules cannot be hashed into a reproducible fixture contract. Unit policy owner: orderbook-engine/docs/adr/ADR-007-execution-units.md.
**Alternatives considered:** Float arithmetic was rejected because rounding drift breaks reproducibility and fixture hashing. A 1e-8 quantity scale was rejected because the decomposed notional multiply would overflow for large positions. Zarith arbitrary-precision decimals were rejected as a heavy dependency for scales that fit int64.
**Source:** Quanthacks backtester Phase 1: canonical event contract and unit policy

---
## 2026-10-04: Use the existing Snowflake account (VECTOR_RESEARCH, warehouse COMPUTE_WH) plus its own ingestion pipeline as the Quanthacks research store, with Massive (api.massive.com) as the licensed market data source.

**Decision:** Use the existing Snowflake account (VECTOR_RESEARCH, warehouse COMPUTE_WH) plus its own ingestion pipeline as the Quanthacks research store, with Massive (api.massive.com) as the licensed market data source.
**Context:** The captain directed the existing account and pipeline instead of a Snowflake share or a separate account. Market data arrives from the licensed Massive API, whose plan covers US equity aggregates, tick trades with participant timestamps, tick NBBO quotes, snapshots, options, crypto, and reference data. Tiger Cloud keeps our Binance captures and stays available but is no longer the only research store.
**Alternatives considered:** A Snowflake share from a data provider, or a separate account. Rejected by the captain: the existing account, warehouse, and pipeline are already in place.
**Source:** captain instruction 2026-10-04, after verifying the account contents

---
