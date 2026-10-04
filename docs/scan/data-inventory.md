# Data inventory

Every dataset this repository has looked at: **162** entries, **2 GB** on disk, 24 with coverage notes and 23 wired to the graph nodes they measure.

| Source | Datasets |
|---|---|
| `source:internal` | 124 |
| `source:sec` | 11 |
| `source:market` | 6 |
| `source:lbnl` | 5 |
| `source:edgar` | 5 |
| `source:hyperliquid` | 3 |
| `source:mixed` | 3 |
| `source:options` | 2 |
| `source:rental-marketplace` | 1 |
| `source:rating-agency` | 1 |
| `source:eia` | 1 |

## The sets that matter, with coverage

| Dataset | Source | Coverage | Rows | Measures | Notes |
|---|---|---|---|---|---|
| `credit-deal-registry.csv` | source:edgar | data centre and related deals | 1752 | `dig:compute:financing-cost` | deal terms, tranches, covenants where filed |
| `credit-panel.csv` | source:edgar | issuer level credit rows | 70779 | `dig:compute:financing-cost` | parent and deal panels |
| `dscr-thresholds.csv` | source:edgar | covenant thresholds | 2 | `dig:compute:financing-cost` | covenant levels extracted from indentures |
| `indenture-covenants.csv` | source:edgar | deal level | 17 | `force:financing:abs-capacity` | maintenance and incurrence covenants |
| `cascade-tape.json` | source:hyperliquid | four markets, 7.3 nominal hours at the last write |  | `force:micro:forced-deleveraging`, `force:micro:depth-liquidity` | mid, spread, depth, funding, open interest, basis; local only |
| `run-manifest.json` | source:internal | suite and artifact registry |  |  | tracks producers and results |
| `queue-panel.csv` | source:lbnl | 36,441 projects, requests to 2024-12-31 | 36855 | `mechanism:capacity:interconnection-bottleneck`, `dig:grid:utility-economics` | projects, statuses, dates, MW, technology, developer, cluster |
| `delivery-revisions.csv` | source:lbnl | 6,407 generators tracked monthly | 7945 | `promise:power:planned-capacity-revision` | truths T1 to T4 |
| `market-panel.json` | source:market | 89 series across nine groups |  | `dig:compute:equity-transmission` | groups: hyperscaler, compute and AI, data centre REIT, buildout, power, fuel, rates, market, commodity |
| `universe-adv-monthly.csv` | source:market | 59 names, 2017-06 to 2026-10 | 5889 | `factor:liquidity` | median dollar volume per name-month, the capacity input |
| `fuel-daily.csv` | source:market | daily fuel series | 299 | `factor:commodity:gas` | input to the gas thesis |
| `bottleneck-factors.csv` | source:mixed | supply chain factors | 105 | `mechanism:capacity:constraint` | transformers, turbines, labour |
| `exposure-panel.csv` | source:mixed | firm exposure to bottlenecks | 2181 | `factor:exposure` | used by the delivery model |
| `implied-vol-test.csv` | source:options | short window | 12 | `outcome:market:post-event-drift` | entitlement limited |
| `option-snapshots/index.json` | source:options | few snapshots |  | `outcome:market:post-event-drift` | no historical chains entitlement |
| `agency-universe.csv` | source:rating-agency | deal universe with ratings | 164 | `dig:compute:financing-cost` | per site and per deal securitisations |
| `compute-price-monthly.csv` | source:rental-marketplace | 18 families, 566 rows, 2022-05 to 2026-09 | 566 | `feature:compute:rental-price`, `dig:cloud:compute-index` | median usd per instance hour, multiple zones |
| `provider-capex-quarterly.csv` | source:sec | 10 providers, 192 rows | 192 | `outcome:firm:capex-level`, `dig:compute:provider-capex` | cash flow capex concepts, quarterly durations, filed dates |
| `provider-revenue-quarterly.csv` | source:sec | 10 providers, 355 rows | 355 | `dig:compute:provider-revenue-line` | preferred contract revenue concept with fallback |
| `complex-capex-quarterly.csv` | source:sec | 59 names across the declared groups | 1079 | `dig:compute:capex-intensity` | one row per quarter fact |
| `complex-revenue-quarterly.csv` | source:sec | 62 names | 2666 | `dig:compute:provider-revenue-line` | as above |
| `complex-assets-quarterly.csv` | source:sec | 63 names, 3,324 instant facts | 3324 | `factor:asset-growth` | used for the asset growth control |
| `capacity-event-ledger.csv` | source:sec | 8-K and material agreement events | 748 | `event:sec:8k-material-agreement` | rule dated events |
| `capacity-strategy.csv` | source:sec | per firm capacity decisions | 222 | `outcome:firm:capex-level` | candidate panel |

## Everything else in hand

| Dataset | Path | Rows | Kind |
|---|---|---|---|
| `bar-cache` | `results/bar-cache` |  | cache |
| `bar-volume` | `results/bar-volume` |  | cache |
| `edgar-cache` | `results/edgar-cache` |  | cache |
| `eia-cache` | `results/eia-cache` |  | cache |
| `factors` | `data/factors` |  | cache |
| `hyperliquid` | `data/hyperliquid` |  | cache |
| `promise-series` | `data/promise-series` |  | cache |
| `queues` | `data/queues` |  | cache |
| `results-agency-only-deals` | `results/agency-only-deals.csv` | 164 | artifact |
| `results-agency-only-deals` | `results/agency-only-deals.json` |  | artifact |
| `results-agency-universe` | `results/agency-universe.json` |  | artifact |
| `results-capacity-expectations` | `results/capacity-expectations.csv` | 943 | artifact |
| `results-capacity-strategy-summary` | `results/capacity-strategy-summary.json` |  | artifact |
| `results-capex-revenue-gap` | `results/capex-revenue-gap.json` |  | artifact |
| `results-cascade-reversion-study` | `results/cascade-reversion-study.json` |  | artifact |
| `results-compute-issuer-segments` | `results/compute-issuer-segments.csv` | 16 | artifact |
| `results-compute-lead-study` | `results/compute-lead-study.json` |  | artifact |
| `results-credit-deal-registry` | `results/credit-deal-registry.json` |  | artifact |
| `results-credit-gauntlet` | `results/credit-gauntlet.csv` | 48 | artifact |
| `results-credit-gauntlet` | `results/credit-gauntlet.json` |  | artifact |
| `results-credit-gauntlet-long` | `results/credit-gauntlet-long.csv` | 24 | artifact |
| `results-credit-gauntlet-long` | `results/credit-gauntlet-long.json` |  | artifact |
| `results-credit-panel` | `results/credit-panel.json` |  | artifact |
| `results-credit-response-test` | `results/credit-response-test.csv` | 8 | artifact |
| `results-credit-response-test` | `results/credit-response-test.json` |  | artifact |
| `results-credit-stability` | `results/credit-stability.csv` | 6 | artifact |
| `results-credit-stability` | `results/credit-stability.json` |  | artifact |
| `results-crosswalk-review` | `results/crosswalk-review.csv` | 1 | artifact |
| `results-deal-diligence` | `results/deal-diligence.csv` | 125 | artifact |
| `results-deal-diligence` | `results/deal-diligence.json` |  | artifact |
| `results-deal-operation-metrics` | `results/deal-operation-metrics.csv` | 15 | artifact |
| `results-deal-ratings` | `results/deal-ratings.csv` | 24 | artifact |
| `results-deal-ratings` | `results/deal-ratings.json` |  | artifact |
| `results-deal-structure` | `results/deal-structure.csv` | 324 | artifact |
| `results-deal-structure` | `results/deal-structure.json` |  | artifact |
| `results-delivery-model-bottleneck-coefficients` | `results/delivery-model-bottleneck-coefficients.csv` | 14 | artifact |
| `results-delivery-model-coefficients` | `results/delivery-model-coefficients.csv` | 16 | artifact |
| `results-delivery-model-exposure-coefficients` | `results/delivery-model-exposure-coefficients.csv` | 7 | artifact |
| `results-delivery-model-object-large` | `results/delivery-model-object-large.csv` | 14 | artifact |
| `results-delivery-model-object-move` | `results/delivery-model-object-move.csv` | 14 | artifact |
| `results-delivery-model-object-withdraw` | `results/delivery-model-object-withdraw.csv` | 14 | artifact |
| `results-delivery-model-panel` | `results/delivery-model-panel.csv` | 27069 | artifact |
| `results-delivery-panel-bottleneck` | `results/delivery-panel-bottleneck.csv` | 27069 | artifact |
| `results-delivery-panel-objects` | `results/delivery-panel-objects.csv` | 27708 | artifact |
| `results-delivery-realizations` | `results/delivery-realizations.csv` | 721 | artifact |
| `results-dscr-thresholds` | `results/dscr-thresholds.json` |  | artifact |
| `results-entity-matching` | `results/entity-matching.csv` | 1070 | artifact |
| `results-filings-register` | `results/filings-register.csv` | 776 | artifact |
| `results-fuel-vs-bars` | `results/fuel-vs-bars.csv` | 299 | artifact |
| `results-gate-scorecard` | `results/gate-scorecard.csv` | 60 | artifact |
| `results-gate-scorecard` | `results/gate-scorecard.json` |  | artifact |
| `results-graph-inventory` | `results/graph-inventory.csv` | 27 | artifact |
| `results-graph-propagation-summary` | `results/graph-propagation-summary.json` |  | artifact |
| `results-group-event-placebo` | `results/group-event-placebo.csv` | 50 | artifact |
| `results-group-event-study` | `results/group-event-study.csv` | 50 | artifact |
| `results-imagery-probe` | `results/imagery-probe.csv` | 8 | artifact |
| `results-imagery-probe-40` | `results/imagery-probe-40.csv` | 24 | artifact |
| `results-implied-vol-test` | `results/implied-vol-test.json` |  | artifact |
| `results-indenture-covenants` | `results/indenture-covenants.json` |  | artifact |
| `results-indenture-layer` | `results/indenture-layer.csv` | 20 | artifact |
| `results-indenture-layer` | `results/indenture-layer.json` |  | artifact |
| `results-index-mandate-events` | `results/index-mandate-events.csv` | 339 | artifact |
| `results-index-mandate-study` | `results/index-mandate-study.csv` | 10 | artifact |
| `results-intensity-factor-study` | `results/intensity-factor-study.json` |  | artifact |
| `results-intensity-preboom-study` | `results/intensity-preboom-study.json` |  | artifact |
| `results-intensity-pricing-study` | `results/intensity-pricing-study.json` |  | artifact |
| `results-intensity-robustness-study` | `results/intensity-robustness-study.json` |  | artifact |
| `results-intensity-segment-study` | `results/intensity-segment-study.json` |  | artifact |
| `results-intensity-timesplit-study` | `results/intensity-timesplit-study.json` |  | artifact |
| `results-intensity-vs-assetgrowth-study` | `results/intensity-vs-assetgrowth-study.json` |  | artifact |
| `results-issuer-exposure-ledger` | `results/issuer-exposure-ledger.csv` | 97 | artifact |
| `results-leg-b-node-distributions` | `results/leg-b-node-distributions.csv` | 15 | artifact |
| `results-leg-c2-association-edges` | `results/leg-c2-association-edges.csv` | 56 | artifact |
| `results-maker-entry-study` | `results/maker-entry-study.json` |  | artifact |
| `results-market-control-panel` | `results/market-control-panel.csv` | 86 | artifact |
| `results-market-control-stress` | `results/market-control-stress.csv` |  | artifact |
| `results-obligation-panel` | `results/obligation-panel.csv` | 130 | artifact |
| `results-ownership-crosswalk` | `results/ownership-crosswalk.csv` | 20 | artifact |
| `results-parent-bond-panel` | `results/parent-bond-panel.csv` | 1723 | artifact |
| `results-parent-bond-panel` | `results/parent-bond-panel.json` |  | artifact |
| `results-physical-observation-ledger` | `results/physical-observation-ledger.csv` | 16 | artifact |
| `results-promise-survival` | `results/promise-survival.csv` | 6407 | artifact |
| `results-provider-family-tests` | `results/provider-family-tests.json` |  | artifact |
| `results-provider-family-tests-relative` | `results/provider-family-tests-relative.json` |  | artifact |
| `results-provider-transmission-study` | `results/provider-transmission-study.json` |  | artifact |
| `results-queue-crosswalk` | `results/queue-crosswalk.csv` | 36446 | artifact |
| `results-queue-crosswalk-summary` | `results/queue-crosswalk-summary.json` |  | artifact |
| `results-queue-exit-study` | `results/queue-exit-study.json` |  | artifact |
| `results-queue-panel` | `results/queue-panel.json` |  | artifact |
| `results-queue-slip-probe` | `results/queue-slip-probe.json` |  | artifact |
| `results-queue-summary` | `results/queue-summary.json` |  | artifact |
| `results-queue-tail-study` | `results/queue-tail-study.json` |  | artifact |
| `results-revision-events` | `results/revision-events.csv` | 84 | artifact |
| `results-rpo-events` | `results/rpo-events.csv` | 5663 | artifact |
| `results-rpo-universe` | `results/rpo-universe.csv` | 1285 | artifact |
| `results-scan-compute-dev` | `results/scan-compute-dev.csv` | 74 | artifact |
| `results-scan-compute-sealed` | `results/scan-compute-sealed.csv` | 74 | artifact |
| `results-scan-mechanism-dev` | `results/scan-mechanism-dev.csv` | 74 | artifact |
| `results-scan-mechanism-sealed` | `results/scan-mechanism-sealed.csv` | 74 | artifact |
| `results-scan-pairs` | `results/scan-pairs.csv` | 74 | artifact |
| `results-scan-pairs-compute-era` | `results/scan-pairs-compute-era.csv` | 74 | artifact |
| `results-scan-pairs-mechanism` | `results/scan-pairs-mechanism.csv` | 74 | artifact |
| `results-sealed-scan-mechanism` | `results/sealed-scan-mechanism.csv` | 74 | artifact |
| `results-site-labels` | `results/site-labels.csv` | 31 | artifact |
| `results-spillover-study` | `results/spillover-study.json` |  | artifact |
| `results-tradeability-panel` | `results/tradeability-panel.csv` | 86 | artifact |
| `results-tranche-table` | `results/tranche-table.csv` | 17 | artifact |
| `results-tranche-table` | `results/tranche-table.json` |  | artifact |
| `results-variant-ledger` | `results/variant-ledger.csv` | 9 | artifact |
| `scan-analogue-cycles` | `docs/scan/analogue-cycles.jsonl` | 9 | artifact |
| `scan-assumptions` | `docs/scan/assumptions.jsonl` | 59 | artifact |
| `scan-conceptual-chains` | `docs/scan/conceptual-chains.jsonl` | 11 | artifact |
| `scan-conceptual-summary` | `docs/scan/conceptual-summary.json` |  | artifact |
| `scan-connection-chain-candidates` | `docs/scan/connection-chain-candidates.json` |  | artifact |
| `scan-connection-chains` | `docs/scan/connection-chains.jsonl` | 13 | artifact |
| `scan-connection-index-summary` | `docs/scan/connection-index-summary.json` |  | artifact |
| `scan-credit-layer-nodes` | `docs/scan/credit-layer-nodes.jsonl` | 14 | artifact |
| `scan-decomposition-summary` | `docs/scan/decomposition-summary.json` |  | artifact |
| `scan-deep-bridges` | `docs/scan/deep-bridges.jsonl` | 54 | artifact |
| `scan-deep-digs` | `docs/scan/deep-digs.jsonl` | 20 | artifact |
| `scan-distributions` | `docs/scan/distributions.jsonl` | 86 | artifact |
| `scan-forces` | `docs/scan/forces.jsonl` | 89 | artifact |
| `scan-graph-delineation` | `docs/scan/graph-delineation.json` |  | artifact |
| `scan-hidden-objects` | `docs/scan/hidden-objects.jsonl` | 39 | artifact |
| `scan-interactions` | `docs/scan/interactions.jsonl` | 149 | artifact |
| `scan-node-measurements` | `docs/scan/node-measurements.jsonl` | 36 | artifact |
| `scan-nodes` | `docs/scan/nodes.jsonl` | 27 | artifact |
| `scan-positioning-nodes` | `docs/scan/positioning-nodes.jsonl` | 29 | artifact |
| `scan-propagation` | `docs/scan/propagation.jsonl` | 1500 | artifact |
| `scan-provider-family-map` | `docs/scan/provider-family-map.jsonl` | 10 | artifact |
| `scan-quantgraph` | `docs/scan/quantgraph.jsonl` | 1903 | artifact |
| `sec-capex` | `results/sec-capex` |  | cache |
| `sec-complex` | `results/sec-complex` |  | cache |
| `sec-instances` | `data/sec-instances` |  | cache |
| `sec-revenue` | `results/sec-revenue` |  | cache |
| `tape` | `data/tape` |  | cache |
| `usdm-cache` | `results/usdm-cache` |  | cache |
| `vintage-aggregates` | `results/vintage-aggregates` |  | cache |