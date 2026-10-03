# Leg A: graph inventory coverage

The node inventory has one row for each of the 27 declarations. Table counts are the verified table totals, not counts of usable rows for each individual node. The source tables are shared across node families, so a full-table total must not be read as node-level coverage.

## Three largest coverage gains

- EIA generator vintages contain 3,387,221 rows, with vintage months from 2016-01 through 2026-08 and point-in-time `available_at` dates. The earlier inventory reported 87,303 rows in the TigerData state-vintage table. This adds generator-level detail, but the two tables have different grains, so their row-count difference is not a matched-row gain.
- Research acquisition rows contain 433,781 rows, compared with 151,198 in the earlier general source-record inventory. This is 282,583 more rows in a separate acquisition archive. The archive has no observation-time column, so these rows do not establish node-specific historical coverage.
- SEC filing documents contain 12,903 rows, compared with 11,892 in the earlier inventory, a net increase of 1,011 documents. Filed dates span 2016-01-21 through 2021-04-29 in the verified query. The table exposes documents and filing clocks, not extracted XBRL value series.

The AWS GPU spot table was also verified at 1,592,024 rows from 2022-05-31 through 2026-09-30. The earlier inventory already reported this archive, so it is confirmed coverage rather than a new gain. TigerData's source-record table currently has 153,527 rows, up 2,329 from the earlier 151,198 count. Its event-time field is heterogeneous, so the CSV date range covers only ISO-formatted event-time rows.

## Declared nodes with no suitable backing table

- `promise:power:interconnection-queue-position`: no queue data table.
- `water:drought:severity`: no drought observations landed in the checked source-record table.
- `price:compute:executed-rental`: no historical executed-rental table.
- `price:power:spot`: no ERCOT spot-price table.
- `positioning:perp:funding-rate`: no perpetual funding history table in the checked store.
- `price:options:implied-move`: no entitled historical option-chain table.
- `flow:index:reconstitution`: no provider announcement or historical fund-holdings table.
- `flow:dealer:hedge-demand`: no historical option-surface or open-interest table.
- `price:datacentre:lease-rate`: no structured lease-level rate table.
- `flow:project:financing-draw`: no project-level financing-draw table.

For these rows, `results/graph-inventory.csv` names `public.gqh_source_records` as the checked audit table and records zero node-specific rows. This audit table is not a backing data source for those nodes. Their declared node statuses remain unchanged. For the other nodes, the inventory names an existing source table and reports its complete verified row count. The `status` and `availability` fields flag that these are table totals, not node-level extracted observation counts. SEC document coverage therefore does not establish that the related XBRL features have been extracted.
