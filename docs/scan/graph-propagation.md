# Graph propagation and delineation

Method owner: `docs/plan/graph-propagation.md`. Classification is decomposed or not yet
decomposed. Nothing here grades a path as dead.

## The graph, expanded

- Nodes: **168,951**
- Typed connections: **1,173,112**
- Distributions written down: **86** samples
- Propagation paths: **632** from 171 seeds
- Hidden objects: **45** (nodes 1, edges 20, gaps 3, assumptions 21)

## Delineation

- Layers: `raw` 94,075, `mechanism` 44,834, `feature` 26,935, `asset` 1,024, `entity` 437, `dataset` 210, `event` 173, `outcome` 160
- Connection status: `declared` 1,144,418, `inferred` 26,018, `proposed` 2,058, `curated` 596, `blocked` 22
- Every connection carries a condition and a falsifier: 99.99% and 99.99%
- Components: 1, largest 168,951, unreachable from anchors 0

## Distributions, centre, spread, tails

Top samples by annualised monthly volatility:

| Sample | n | mean | sd | median | p90/median | skew | excess kurtosis |
|---|---|---|---|---|---|---|---|
| p6-b300 | 7 | 52.8356 | 23.3113 | 45.0591 | 1.937 | 0.539 | -1.148 |
| p3 | 46 | 4.4963 | 2.001 | 4.0419 | 1.749 | 1.236 | 1.241 |
| p5e | 14 | 20.6691 | 4.7639 | 22.4299 | 1.117 | -1.255 | 0.478 |
| p6-b200 | 11 | 33.2921 | 9.9747 | 36.488 | 1.202 | -0.756 | -0.559 |
| g6f | 11 | 0.1369 | 0.0383 | 0.1486 | 1.151 | -1.317 | 0.516 |
| g4dn | 49 | 0.9421 | 0.3276 | 0.7955 | 1.736 | 1.171 | 0.719 |
| g3 | 34 | 0.9283 | 0.2667 | 0.8856 | 1.539 | 0.241 | -0.377 |
| p4d | 49 | 11.5036 | 3.186 | 10.5709 | 1.63 | 0.881 | 0.072 |
| g5g | 49 | 0.3954 | 0.1732 | 0.3508 | 1.889 | 1.362 | 1.151 |
| g6e | 22 | 1.982 | 0.4365 | 1.9973 | 1.21 | -0.324 | 0.732 |
| p4de | 14 | 13.1953 | 5.1188 | 13.2756 | 1.598 | 0.367 | -0.51 |
| p5 | 35 | 38.0265 | 20.9406 | 29.2972 | 2.407 | 0.624 | -1.194 |

Top samples by tail ratio (p90 over median):

| Sample | dataset | n | p90/median | top 1 percent share |
|---|---|---|---|---|
| state=NJ | queue-panel.csv | 1245 | 35.0 | 0.151 |
| state=DE | queue-panel.csv | 154 | 22.482 | 0.07 |
| type_clean=Hydro | queue-panel.csv | 488 | 17.462 | 0.285 |
| state=ID | queue-panel.csv | 812 | 16.25 | 0.107 |
| state=MA | queue-panel.csv | 461 | 15.757 | 0.077 |
| state=RI | queue-panel.csv | 112 | 15.575 | 0.098 |
| type_clean=Other | queue-panel.csv | 1714 | 15.385 | 0.136 |
| state=MT | queue-panel.csv | 526 | 15.0 | 0.076 |
| state=PA | queue-panel.csv | 1953 | 15.0 | 0.124 |
| state=MD | queue-panel.csv | 573 | 14.513 | 0.154 |
| ORCL | provider-capex-quarterly.csv | 17 | 10.969 | 0.612 |
| state=ME | queue-panel.csv | 281 | 8.542 | 0.086 |

## Hidden layer

| Kind | Id | Reason | Action |
|---|---|---|---|
| hidden_node | `dig:material:copper-stack` | referenced but no node record | add the node record with meaning, observables and payer |
| hidden_assumption | `chain:power:transformer-scarcity-to-supplier-margin:02` | high-load link resting on weak evidence | test this link first, it decides the chain |
| hidden_assumption | `chain:power:transformer-scarcity-to-supplier-margin:03` | high-load link resting on weak evidence | test this link first, it decides the chain |
| hidden_assumption | `chain:power:transformer-scarcity-to-supplier-margin:05` | high-load link resting on weak evidence | test this link first, it decides the chain |
| hidden_assumption | `chain:power:goes-steel-to-transformer-output:02` | high-load link resting on weak evidence | test this link first, it decides the chain |
| hidden_assumption | `chain:power:turbine-slots-to-power-price:03` | high-load link resting on weak evidence | test this link first, it decides the chain |
| hidden_assumption | `chain:power:turbine-slots-to-power-price:04` | high-load link resting on weak evidence | test this link first, it decides the chain |
| hidden_assumption | `chain:power:upgrade-costs-to-withdrawals:03` | high-load link resting on weak evidence | test this link first, it decides the chain |
| hidden_assumption | `chain:power:upgrade-costs-to-withdrawals:04` | high-load link resting on weak evidence | test this link first, it decides the chain |
| hidden_assumption | `chain:power:cooling-water-to-siting:02` | high-load link resting on weak evidence | test this link first, it decides the chain |
| hidden_assumption | `chain:power:labor-to-schedules:02` | high-load link resting on weak evidence | test this link first, it decides the chain |
| hidden_assumption | `chain:power:aluminum-to-conductors:02` | high-load link resting on weak evidence | test this link first, it decides the chain |
| hidden_assumption | `chain:power:rates-to-schedules:01` | high-load link resting on weak evidence | test this link first, it decides the chain |
| hidden_assumption | `chain:power:rates-to-schedules:02` | high-load link resting on weak evidence | test this link first, it decides the chain |
| hidden_assumption | `chain:power:load-growth-to-rate-base:03` | high-load link resting on weak evidence | test this link first, it decides the chain |
| hidden_assumption | `chain:power:load-growth-to-rate-base:04` | high-load link resting on weak evidence | test this link first, it decides the chain |
| hidden_assumption | `chain:promise:revision-to-cash-flow:01` | high-load link resting on weak evidence | test this link first, it decides the chain |
| hidden_assumption | `chain:promise:revision-to-cash-flow:02` | high-load link resting on weak evidence | test this link first, it decides the chain |
| hidden_assumption | `chain:promise:revision-to-cash-flow:04` | high-load link resting on weak evidence | test this link first, it decides the chain |
| hidden_assumption | `chain:power:panama-drought-to-power:03` | high-load link resting on weak evidence | test this link first, it decides the chain |
| hidden_assumption | `chain:power:wildfire-insurance-to-utility-credit:02` | high-load link resting on weak evidence | test this link first, it decides the chain |
| hidden_edge | `dig:power:lpt -> dig:sic:power-devices` | cross-dig pair sharing ['power'] and observable tokens ['lead'] | add the typed edge or record why the shared observable stops here |
| hidden_edge | `dig:power:goes -> dig:nuc:firm-power` | cross-dig pair sharing ['power'] and observable tokens ['announcements'] | add the typed edge or record why the shared observable stops here |
| hidden_edge | `dig:power:goes -> dig:compute:power-commitment` | cross-dig pair sharing ['power'] and observable tokens ['announcements'] | add the typed edge or record why the shared observable stops here |
| hidden_edge | `dig:power:core-stacking -> dig:nuc:firm-power` | cross-dig pair sharing ['power'] and observable tokens ['announcements'] | add the typed edge or record why the shared observable stops here |
| hidden_edge | `dig:hvdc:copper-aluminium -> dig:copper:demand` | cross-dig pair sharing ['copper'] and observable tokens ['cable', 'commentary', 'maker'] | add the typed edge or record why the shared observable stops here |
| hidden_edge | `dig:compute:provider-capex -> dig:compute:equity-transmission` | cross-dig pair sharing ['compute'] and observable tokens ['capex'] | add the typed edge or record why the shared observable stops here |
| hidden_edge | `dig:compute:inference-cost -> dig:compute:rental-to-revenue-link` | cross-dig pair sharing ['compute'] and observable tokens ['provider'] | add the typed edge or record why the shared observable stops here |
| hidden_edge | `dig:compute:inference-cost -> dig:compute:family-exposure-map` | cross-dig pair sharing ['compute'] and observable tokens ['provider'] | add the typed edge or record why the shared observable stops here |
| hidden_edge | `dig:compute:inference-cost -> dig:compute:revenue-per-mw` | cross-dig pair sharing ['compute'] and observable tokens ['provider'] | add the typed edge or record why the shared observable stops here |

## Propagation paths, truth to payer

| Seed | Path | Hops | Floor | Data in hand | Greatest assumption |
|---|---|---|---|---|---|
| `dig:grid:capex-plan` | `dig:grid:capex-plan` -> `outcome:firm:capex-level` | 1 | E2 | provider-capex-quarterly.csv | The outcome remains the measured object. |
| `dig:providers:firm-capacity` | `dig:providers:firm-capacity` -> `asset:equity:utility-basket` | 1 | E2 | capacity-strategy.csv | The basket remains the traded surface. |
| `dig:providers:provider-margin` | `dig:providers:provider-margin` -> `outcome:firm:cash-flow-revision` | 1 | E2 | provider-capex-quarterly.csv, delivery-revisions.csv, cascade-tape.json | Contracted revenue remains the margin driver. |
| `dig:grid:rate-case` | `dig:grid:rate-case` -> `dig:grid:capex-plan` -> `outcome:firm:capex-level` | 2 | E2 | provider-capex-quarterly.csv | Capital recovery runs through the rate case process. |
| `dig:providers:credit` | `dig:providers:credit` -> `dig:providers:provider-margin` -> `outcome:firm:cash-flow-revision` | 2 | E2 | delivery-revisions.csv, cascade-tape.json, credit-deal-registry.csv | Margins support the credit that funds new supply. |
| `dig:providers:ppa-price` | `dig:providers:ppa-price` -> `dig:providers:provider-margin` -> `outcome:firm:cash-flow-revision` | 2 | E2 | delivery-revisions.csv, cascade-tape.json | Contract prices set provider margins. |
| `entity:issuer:company` | `entity:issuer:company` -> `outcome:market:post-event-drift` | 1 | E3 | capacity-event-ledger.csv | Both nodes read the same source. |
| `outcome:market:abnormal-return` | `outcome:market:abnormal-return` -> `outcome:market:post-event-drift` | 1 | E3 | capacity-event-ledger.csv | Both nodes read the same source. |
| `claim:pricing:underreacts` | `claim:pricing:underreacts` -> `outcome:firm:capex-level` | 1 | E4 | provider-capex-quarterly.csv | The node receives a verified representation and a declared role |
| `claim:pricing:underreacts` | `claim:pricing:underreacts` -> `outcome:firm:capex-timing` | 1 | E4 | provider-capex-quarterly.csv | The node receives a verified representation and a declared role |
| `claim:pricing:underreacts` | `claim:pricing:underreacts` -> `outcome:firm:free-cash-flow` | 1 | E4 | cascade-tape.json | The node receives a verified representation and a declared role |
| `claim:pricing:underreacts` | `claim:pricing:underreacts` -> `outcome:firm:revenue-level` | 1 | E4 | needs data | The node receives a verified representation and a declared role |
| `claim:pricing:underreacts` | `claim:pricing:underreacts` -> `outcome:firm:gross-margin` | 1 | E4 | needs data | The node receives a verified representation and a declared role |
| `claim:pricing:underreacts` | `claim:pricing:underreacts` -> `outcome:firm:operating-margin` | 1 | E4 | needs data | The node receives a verified representation and a declared role |
| `outcome:portfolio:net-pnl` | `outcome:portfolio:net-pnl` -> `asset:equity:sector-basket` | 1 | E4 | needs data | The cross-layer relation is supported by point-in-time evidence |
| `outcome:portfolio:net-pnl` | `outcome:portfolio:net-pnl` -> `asset:equity:market-index` | 1 | E4 | needs data | The cross-layer relation is supported by point-in-time evidence |
| `outcome:portfolio:net-pnl` | `outcome:portfolio:net-pnl` -> `asset:equity:supplier-basket` | 1 | E4 | needs data | The cross-layer relation is supported by point-in-time evidence |
| `outcome:portfolio:net-pnl` | `outcome:portfolio:net-pnl` -> `asset:equity:utility-basket` | 1 | E4 | needs data | The cross-layer relation is supported by point-in-time evidence |
| `outcome:portfolio:net-pnl` | `outcome:portfolio:net-pnl` -> `asset:options:defined-risk-spread` | 1 | E4 | needs data | The cross-layer relation is supported by point-in-time evidence |
| `dig:compute:depreciation` | `dig:compute:depreciation` -> `dig:compute:provider-capex` | 1 | E2 | compute-price-monthly.csv, provider-capex-quarterly.csv | Short useful lives turn capex into a recurring cash cost, changing the build economics. |
| `dig:compute:family-exposure-map` | `dig:compute:family-exposure-map` -> `dig:compute:rental-to-revenue-link` | 1 | E2 | compute-price-monthly.csv, exposure-panel.csv | Each provider's revenue is levered to specific families, so family level tests replace the aggregate. |
| `dig:compute:family-exposure-map` | `dig:compute:family-exposure-map` -> `dig:compute:revenue-per-mw` | 1 | E2 | compute-price-monthly.csv, exposure-panel.csv | With family price mapping retired, the transmission object is the level variable: revenue per contracted megawatt. |
| `dig:compute:financing-cost` | `dig:compute:financing-cost` -> `dig:compute:equity-transmission` | 1 | E2 | compute-price-monthly.csv | Funding cost sets the discount applied to capacity cash flows. |
| `dig:compute:financing-cost` | `dig:compute:financing-cost` -> `dig:compute:provider-revenue-line` | 1 | E2 | compute-price-monthly.csv, provider-capex-quarterly.csv | Securitised and debt funded capacity shows up as contracted revenue before it shows up as equity value. |
| `dig:compute:financing-cost` | `dig:compute:financing-cost` -> `sub:sub:dig:compute:financing-cost:composition:composition` | 1 | E2 | compute-price-monthly.csv | The refinement chain from this node is valid. |

## Reproduce

    python3 scripts/build_graph_propagation.py
    python3 scripts/render_graph_propagation.py
