# Snowflake research workspace

Owner: vshnu1. This is the historical research layer, not the live execution path.

`bootstrap.sql` is mirrored into the Snowflake personal workspace as
`VECTOR_snowflake_bootstrap.sql`. Review it before execution. It creates the `VECTOR_RESEARCH`
database and raw/features/research table contracts but deliberately does not create a warehouse.

The intended boundary is:

```text
TigerData/q -> curated exports -> Snowflake research panels -> Parquet/q -> C++/OCaml backtest
```

Do not query Snowflake per tick or per order. Keep raw source files immutable and preserve
`event_time`, `available_at`, `ingested_at`, source version and checksum. A feature may only use
rows available by the decision timestamp. Start with a small AWS compute + equity + Massive filing
panel and compare the output with the TigerData/q-only baseline before adding ML services.

No Snowflake credentials belong in this repository.
