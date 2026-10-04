## Pricing the Buildout

**Testing whether power-and-infrastructure delivery changes contain usable information for equity investors.**

### Inspiration

AI and data-center expansion depends on projects that take years to plan and build: generators, substations, electrical equipment, and data-center infrastructure. Announced capacity is not the same as delivered capacity. Projects can be delayed, revised, or cancelled—and the economic consequences depend on which companies have exposure and when investors learn about it.

We wanted to test whether those real-world changes connect to issuer disclosures and subsequent stock returns, while being honest about the difference between an interesting pattern and a tradeable strategy.

### What it does

Pricing the Buildout assembles dated generator-plan vintages, issuer filings, point-in-time financial data, and daily equity prices to study infrastructure delivery and candidate equity signals. The research keeps source documents and availability times so observations can be evaluated against what was actually knowable at the time.

The project also tests portfolio construction and walk-forward results, compares candidates with baselines, and preserves negative findings. The equity research uses daily data; it does not claim to use equity Level 2 order books.

### Current results—and limitations

The current development run reports a walk-forward conditioned candidate with a 14.09% annualized return, 1.793 Sharpe, and −5.3% maximum drawdown. These are **exploratory development results, not validated alpha or live performance**. The run is marked as not ready for a performance claim, and its drawdown-state timing needs an audit for possible same-day lookahead. The candidate also trails the equal-weight long-basket reference in raw return over the comparison window.

The delivery-revision study found substantial schedule movement, but its tests did not establish a robust equity edge from delivery revisions alone. We include that negative result rather than present project activity as proof of profitability. See the [latest research artifacts and reproducible judge path (https://github.com/sebastbernal2-ship-it/pricing-the-buildout/commit/b5d8621f9d1971a92bf92409925b410c989be44b)](<https://github.com/sebastbernal2-ship-it/pricing-the-buildout/commit/b5d8621f9d1971a92bf92409925b410c989be44b>).

### How we built it

- **Snowflake** is the shared historical research layer for source records, filing material, point-in-time panels, and versioned results. Optional Cortex retrieval helps reviewers find relevant filing passages; it does not alter signals, fills, or reported P\&L.
- **TigerData** stores shared source landings and operational time-series telemetry, including collector health, event counts, sequence quality, latency, throughput, and compact execution summaries.
- **Vultr** hosts the collector and replay workload.
- **OCaml** powers a separate order-book replay engine using explicit event and receive timestamps, integer-scaled prices and quantities, source hashes, and quality flags. This component studies execution mechanics; it does not generate the equity signal.
- **Massive and public source data** support filing and market-data retrieval, with original SEC documents retained for review.

### Reproducibility

From the repository root, run:

```
python3 docs/inbox/vishnu-2026-10-03/visualization/culmination.py
```

This renders the dashboard from committed result artifacts and daily ledgers. Use `--all` to render every candidate. Use `--rebuild` only to recompute the strategy and regenerate cached ledgers. The latest judge-path update added titled figure exports and fresh-clone support; it does not turn exploratory results into validated performance.

### What’s next

Audit and correct the conditioned strategy’s information timing, synchronize the research note with the latest candidate results, and evaluate the prospective forward window without tuning against it. Further work must address borrow, capacity, and implementation costs before any claim of tradability.

### Built with

Snowflake, TigerData / TimescaleDB, Vultr, OCaml, Python, Massive, SEC EDGAR, and EIA-860M.
