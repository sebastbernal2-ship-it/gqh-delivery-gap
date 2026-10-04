# Graph propagation and delineation

Method owner: `docs/plan/graph-propagation.md`. Classification is decomposed or not yet
decomposed. Nothing here grades a path as dead.

## The graph, expanded

- Nodes: **156,543**
- Typed connections: **1,093,132**
- Distributions written down: **86** samples
- Propagation paths: **1,500** from 155 seeds
- Hidden objects: **29** (nodes 1, edges 5, gaps 2, assumptions 21)

## Delineation

- Layers: `raw` 86,371, `mechanism` 41,063, `feature` 26,037, `asset` 1,023, `entity` 412, `dataset` 210, `event` 172, `outcome` 158
- Connection status: `declared` 1,065,650, `inferred` 24,870, `proposed` 2,058, `curated` 532, `blocked` 22
- Every connection carries a condition and a falsifier: 99.99% and 99.99%
- Components: 1, largest 156,543, unreachable from anchors 0

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
| hidden_gap | `concept:thesis:delivery-gap` | core node at degree 49, under the 50 connection target | add the missing connections as questions with falsifiers |
| hidden_gap | `strategy:monitor:scarcity-state` | core node at degree 48, under the 50 connection target | add the missing connections as questions with falsifiers |
| hidden_assumption | `index-wide` | 0 inferred connections lack a condition, 0 lack a falsifier | keep filling conditions and falsifiers as part of every deepening pass |

## Propagation paths, truth to payer

| Seed | Path | Hops | Floor | Data in hand | Greatest assumption |
|---|---|---|---|---|---|
| `dig:compute:depreciation` | `dig:compute:depreciation` -> `dig:compute:provider-capex` | 1 | E2 | compute-price-monthly.csv, provider-capex-quarterly.csv | Short useful lives turn capex into a recurring cash cost, changing the build economics. |
| `claim:pricing:underreacts` | `claim:pricing:underreacts` -> `strategy:expression:event-equity` -> `sub:sub:strategy:expression:event-equity:signal:composition` | 2 | E2 | capacity-strategy.csv, capacity-event-ledger.csv | The refinement chain from this node is valid. |
| `claim:pricing:underreacts` | `claim:pricing:underreacts` -> `strategy:expression:event-equity` -> `sub:sub:strategy:expression:event-equity:signal:inputs` | 2 | E2 | capacity-strategy.csv, capacity-event-ledger.csv | The refinement chain from this node is valid. |
| `claim:pricing:underreacts` | `claim:pricing:underreacts` -> `strategy:expression:event-equity` -> `sub:sub:strategy:expression:event-equity:signal:constraints` | 2 | E2 | capacity-strategy.csv, capacity-event-ledger.csv | The refinement chain from this node is valid. |
| `claim:pricing:underreacts` | `claim:pricing:underreacts` -> `strategy:expression:event-equity` -> `sub:sub:strategy:expression:event-equity:signal:observables` | 2 | E2 | capacity-strategy.csv, capacity-event-ledger.csv | The refinement chain from this node is valid. |
| `claim:pricing:underreacts` | `claim:pricing:underreacts` -> `strategy:expression:event-equity` -> `sub:sub:strategy:expression:event-equity:signal:substitutes` | 2 | E2 | capacity-strategy.csv, capacity-event-ledger.csv | The refinement chain from this node is valid. |
| `claim:pricing:underreacts` | `claim:pricing:underreacts` -> `strategy:expression:event-equity` -> `sub:sub:strategy:expression:event-equity:sizing:composition` | 2 | E2 | capacity-strategy.csv, capacity-event-ledger.csv | The refinement chain from this node is valid. |
| `claim:pricing:underreacts` | `claim:pricing:underreacts` -> `strategy:expression:event-equity` -> `sub:sub:strategy:expression:event-equity:sizing:inputs` | 2 | E2 | capacity-strategy.csv, capacity-event-ledger.csv | The refinement chain from this node is valid. |
| `claim:pricing:underreacts` | `claim:pricing:underreacts` -> `strategy:expression:event-equity` -> `sub:sub:strategy:expression:event-equity:sizing:constraints` | 2 | E2 | capacity-strategy.csv, capacity-event-ledger.csv | The refinement chain from this node is valid. |
| `claim:pricing:underreacts` | `claim:pricing:underreacts` -> `strategy:expression:event-equity` -> `sub:sub:strategy:expression:event-equity:sizing:observables` | 2 | E2 | capacity-strategy.csv, capacity-event-ledger.csv | The refinement chain from this node is valid. |
| `claim:pricing:underreacts` | `claim:pricing:underreacts` -> `strategy:expression:event-equity` -> `sub:sub:strategy:expression:event-equity:sizing:substitutes` | 2 | E2 | capacity-strategy.csv, capacity-event-ledger.csv | The refinement chain from this node is valid. |
| `claim:pricing:underreacts` | `claim:pricing:underreacts` -> `strategy:expression:event-equity` -> `sub:sub:strategy:expression:event-equity:costs:composition` | 2 | E2 | capacity-strategy.csv, capacity-event-ledger.csv | The refinement chain from this node is valid. |
| `claim:pricing:underreacts` | `claim:pricing:underreacts` -> `strategy:expression:event-equity` -> `sub:sub:strategy:expression:event-equity:costs:inputs` | 2 | E2 | capacity-strategy.csv, capacity-event-ledger.csv | The refinement chain from this node is valid. |
| `claim:pricing:underreacts` | `claim:pricing:underreacts` -> `strategy:expression:event-equity` -> `sub:sub:strategy:expression:event-equity:costs:constraints` | 2 | E2 | capacity-strategy.csv, capacity-event-ledger.csv | The refinement chain from this node is valid. |
| `claim:pricing:underreacts` | `claim:pricing:underreacts` -> `strategy:expression:event-equity` -> `sub:sub:strategy:expression:event-equity:costs:observables` | 2 | E2 | capacity-strategy.csv, capacity-event-ledger.csv | The refinement chain from this node is valid. |
| `claim:pricing:underreacts` | `claim:pricing:underreacts` -> `strategy:expression:event-equity` -> `sub:sub:strategy:expression:event-equity:costs:substitutes` | 2 | E2 | capacity-strategy.csv, capacity-event-ledger.csv | The refinement chain from this node is valid. |
| `claim:pricing:underreacts` | `claim:pricing:underreacts` -> `strategy:expression:event-equity` -> `sub:sub:strategy:expression:event-equity:capacity:composition` | 2 | E2 | capacity-strategy.csv, capacity-event-ledger.csv | The refinement chain from this node is valid. |
| `claim:pricing:underreacts` | `claim:pricing:underreacts` -> `strategy:expression:event-equity` -> `sub:sub:strategy:expression:event-equity:capacity:inputs` | 2 | E2 | capacity-strategy.csv, capacity-event-ledger.csv | The refinement chain from this node is valid. |
| `claim:pricing:underreacts` | `claim:pricing:underreacts` -> `strategy:expression:event-equity` -> `sub:sub:strategy:expression:event-equity:capacity:constraints` | 2 | E2 | capacity-strategy.csv, capacity-event-ledger.csv | The refinement chain from this node is valid. |
| `claim:pricing:underreacts` | `claim:pricing:underreacts` -> `strategy:expression:event-equity` -> `sub:sub:strategy:expression:event-equity:capacity:observables` | 2 | E2 | capacity-strategy.csv, capacity-event-ledger.csv | The refinement chain from this node is valid. |
| `claim:pricing:underreacts` | `claim:pricing:underreacts` -> `strategy:expression:event-equity` -> `sub:sub:strategy:expression:event-equity:capacity:substitutes` | 2 | E2 | capacity-strategy.csv, capacity-event-ledger.csv | The refinement chain from this node is valid. |
| `claim:pricing:underreacts` | `claim:pricing:underreacts` -> `strategy:expression:event-equity` -> `sub:sub:strategy:expression:event-equity:kill-switch:composition` | 2 | E2 | capacity-strategy.csv, capacity-event-ledger.csv | The refinement chain from this node is valid. |
| `claim:pricing:underreacts` | `claim:pricing:underreacts` -> `strategy:expression:event-equity` -> `sub:sub:strategy:expression:event-equity:kill-switch:inputs` | 2 | E2 | capacity-strategy.csv, capacity-event-ledger.csv | The refinement chain from this node is valid. |
| `claim:pricing:underreacts` | `claim:pricing:underreacts` -> `strategy:expression:event-equity` -> `sub:sub:strategy:expression:event-equity:kill-switch:constraints` | 2 | E2 | capacity-strategy.csv, capacity-event-ledger.csv | The refinement chain from this node is valid. |
| `claim:pricing:underreacts` | `claim:pricing:underreacts` -> `strategy:expression:event-equity` -> `sub:sub:strategy:expression:event-equity:kill-switch:observables` | 2 | E2 | capacity-strategy.csv, capacity-event-ledger.csv | The refinement chain from this node is valid. |

## Reproduce

    python3 scripts/build_graph_propagation.py
    python3 scripts/render_graph_propagation.py
