# Data

Nothing here is committed. Data is fetched, cached locally, and rebuilt from code.

## Hard rules

1. No credentials in this repo, ever. Keys stay in the environment or the hooking up is done with a
   local `.env` that `.gitignore` already excludes.
2. No point-in-time leaks. Every fetch records the vintage or the publication date of what it pulled.
   Freeze vintages and never revise a frozen vintage after use.
3. The manifest is the single owner of what was pulled: source, coverage start, coverage end, fetch
   date, and availability policy. It is written by W0 as `data/manifest.json` and it is committed.

## Sources

| Need | Source |
|---|---|
| Planned and realized generation, monthly vintages | EIA-860M, EIA-860 annual |
| Interconnection queues | LBNL Queued Up, ISO queue files |
| Equity and options bars | Databento, or the sponsor feeds |
| Options chains around events | Massive, or FMP or Databento OPRA |
| 8-K filings and categories | Massive, or SEC EDGAR full text search |
| Compute price | Ornn OCPI, plus the ICE OCPI H100 future curve |
| Macro and power | FRED, EIA |
| Factor benchmarks | Ken French library |
| Perp funding and L4 book | Hyperliquid S3 archive |
