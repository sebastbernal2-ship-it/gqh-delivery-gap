# Graph propagation and delineation

Method owner: `docs/plan/graph-propagation.md`. Classification is decomposed or not yet
decomposed. Nothing here grades a path as dead.

## The graph, expanded

- Nodes: **175,978**
- Typed connections: **1,225,856**
- Distributions written down: **86** samples
- Propagation paths: **1,486** from 263 seeds
- Hidden objects: **39** (nodes 1, edges 15, gaps 2, assumptions 21)

## Delineation

- Layers: `raw` 97,791, `mechanism` 46,193, `feature` 28,024, `asset` 1,024, `assumption` 545, `entity` 529, `force` 356, `dataset` 210
- Connection status: `declared` 1,196,114, `inferred` 26,950, `proposed` 2,058, `curated` 712, `blocked` 22
- Every connection carries a condition and a falsifier: 99.99% and 99.99%
- Components: 1, largest 175,978, unreachable from anchors 0

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

## The conceptual layer

- Forces: **89** across 13 domains
- Interactions: **149** typed pushes, mean assumption load 3.13, 41 at load four or five, 14 with phase dependent signs
- Assumptions as nodes: **59**
- Conceptual chains: **11** carrying 53 hops

Relations in use: drives 49, dampens 34, reveals 12, gates 11, conditions 8, complements 6, substitutes 6, amplifies 5, crowds_in 5, accelerates 3, competes_for 2, bounds 2.

### The heaviest links

| From | Relation | To | Load | Channel | Kill |
|---|---|---|---|---|---|
| `force:grid:transformer-lead-time` | gates | `force:power:energization-delay` | 5 | No transformer means no energization, whatever the queue says. | Sites energize without transformers or with substitutes. |
| `force:cycles:capacity-overbuild` | drives | `force:cycles:price-collapse` | 4 | Excess capacity clears at prices below full cost. | Prices hold while utilisation falls. |
| `force:cycles:capacity-overbuild` | dampens | `force:grid:utility-capex-plan` | 4 | Excess capacity defers the next wave of grid spend. | Capex plans accelerate through an overbuild. |
| `force:cycles:capital-inflow` | drives | `force:cycles:capacity-overbuild` | 4 | Funded capacity gets built, and it arrives in herds. | Capacity additions track demand without overshoot. |
| `force:cycles:price-collapse` | drives | `force:cycles:shakeout-consolidation` | 4 | Distress transfers assets to the strongest balance sheets. | Distress appears with no consolidation. |
| `force:cycles:price-collapse` | dampens | `force:providers:neocloud-funding` | 4 | Funding closes when the price signal breaks. | Funding opens wider during a price collapse. |
| `force:demand:inference-price-elasticity` | conditions | `force:providers:rental-spread` | 4 | Elasticity is the moderator that decides whether rental prices fall on new supply. | Prices collapse on new supply even with elastic demand. |
| `force:demand:model-efficiency` | dampens | `force:power:energization-delay` | 4 | Cheaper tokens per wait soften the urgency of new connections. | Efficiency improves and power demand for the same workload rises. |
| `force:demand:model-efficiency` | dampens | `force:providers:rental-spread` | 4 | Cheaper tokens per watt reduce capacity per unit of output. | Spreads hold while efficiency improves sharply. |
| `force:demand:token-volume` | competes_for | `force:demand:model-efficiency` | 4 | More tokens can be served by better models, so efficiency substitutes for raw capacity. | Capacity demand falls in absolute terms while token volume rises. |
| `force:demand:token-volume` | crowds_in | `force:silicon:hbm-supply` | 4 | More served tokens pull memory bits through the same fabs. | Accelerator shipments rise while HBM supply is flat. |
| `force:demand:token-volume` | drives | `force:power:firm-capacity-scarcity` | 4 | Continuous inference load raises the peak and the floor of power demand at once. | Firm capacity prices stay flat while data centre load grows. |
| `force:financing:abs-capacity` | finances | `force:providers:neocloud-funding` | 4 | Securitisation lets lessors fund fleets against contracted cash flows. | Lessors fund only with equity and their growth stalls. |
| `force:financing:abs-capacity` | amplifies | `force:cycles:capacity-overbuild` | 4 | Securitisation lets the marginal builder keep building past the point of sense. | Issuance closes before the overbuild arrives. |
| `force:financing:credit-spreads` | accelerates | `force:cycles:price-collapse` | 4 | Spread widening forces the marginal owner to sell into weakness. | Spread widening has no effect on asset sales. |
| `force:financing:depreciation-schedule` | drives | `force:providers:equity-multiple` | 4 | The schedule decides reported earnings for the same cash flow. | Multiples are unchanged by depreciation policy changes. |
| `force:financing:policy-rate` | conditions | `force:providers:capex-intensity` | 4 | Rate direction decides whether intensity is punished or ignored. | Intensity is rewarded in every rate regime. |
| `force:financing:vendor-financing` | reveals | `force:silicon:accelerator-lead-time` | 4 | Vendor credit terms are a read on end demand strength. | Terms tighten while lead times lengthen. |
| `force:grid:rate-case-lag` | dampens | `force:grid:utility-capex-plan` | 4 | A long lag to recovery makes utilities sequence spend carefully. | Plans accelerate while recovery lags. |
| `force:grid:transformer-lead-time` | dampens | `force:grid:utility-capex-plan` | 4 | Equipment scarcity forces plans to stretch and rephase. | Plans accelerate while lead times lengthen. |

### Conceptual chains

| Chain | Hops | Intuition | Greatest assumption |
|---|---|---|---|
| `chain:concept:capex-absorption` | rental-spread -> capex-intensity -> depreciation-schedule -> equity-multiple | Wide rental spreads invite capacity spending; the spending arrives as depreciation before it arrives as revenue, and the market charges the gap in the multiple first and the earnings later. | Depreciation and interest land inside the measurement window rather than after the revenue arrives. |
| `chain:concept:power-chain` | interconnection-queue -> energization-delay -> rental-spread -> capex-intensity -> transformer-lead-time | The queue and then the transformer gate energization; while gates bind, installed capacity is scarce and spreads stay wide, which is the provider's window and the equipment maker's pricing power. | The queue and equipment gates bind for years rather than clearing through price. |
| `chain:concept:equipment-scarcity` | token-volume -> gas-turbine-slot -> turbine-casters -> transformer-lead-time -> goes-steel | Demand pulls on turbines and transformers at once; castings and core steel gate the makers, so lead times extend and the pricing power sits with whoever already has slots and mill capacity. | The gates are capacity rather than price, so the margin accrues to incumbents for years. |
| `chain:concept:policy-pull-forward` | investment-credits -> capital-inflow -> capacity-overbuild -> price-collapse -> shakeout-consolidation | Credits raise after tax returns, capital floods in, capacity overshoots and the adjustment is deeper than it would have been without the subsidy; the analogue is merchant power and telecom fibre. | Subsidised capital is less disciplined than equity funded capital. |
| `chain:concept:water-cooling` | cooling-water-availability -> water-rights -> evaporative-limits -> closed-loop-retrofit -> capex-intensity | Water stress turns into rules, rules force closed loop retrofits, and the retrofit spend lands on the provider's capex line, tightening the absorption chain. | Water constraints bind locally before they bind globally, so the effect is site by site. |
| `chain:concept:labour-gate` | epc-backlog -> electricians -> utility-capex-plan -> rate-case-lag -> energy-price-caps | Backlogs pull crews, wage pressure raises installed cost, utilities stretch plans, recovery lags, and the political response shows up as price caps that remove the next cycle's signal. | The political channel binds before the capital channel does. |
| `chain:concept:financing-flip` | policy-rate -> capital-inflow -> neocloud-funding -> capacity-overbuild -> price-collapse | Cheap money funds the marginal builder; expensive money removes the marginal buyer exactly when capacity is arriving, which is how cycles turn without a demand shock. | The marginal entrant is funded, not retained earnings funded. |
| `chain:concept:demand-elasticity` | inference-price-elasticity -> token-volume -> model-efficiency -> agentic-workloads -> accelerator-resale-value | Cheaper inference pulls new workloads; always on agents lift the utilisation floor; the floor is what keeps old silicon economically alive, which is what holds resale values and financing terms. | Unused use cases exist below the current price and get adopted within quarters. |
| `chain:concept:tenant-power` | tenant-concentration -> rental-spread -> revenue-per-mw -> capex-intensity -> abs-capacity | A few large tenants negotiate hard, spreads compress, revenue per megawatt stalls while capex keeps running, and the funding window depends on the contracts those same tenants sign. | The largest tenants have a credible self build threat at all times. |
| `chain:concept:margin-incidence` | firm-capacity-scarcity -> transformer-lead-time -> rental-spread -> revenue-per-mw -> equity-multiple | Scarcity runs from power to equipment to capacity rent; the question the chain asks is who keeps it. Equipment keeps it through lead time pricing, providers keep it only while tenants cannot self build, and the multiple is where the market decides which of the two it believes. | The margin is retained by whoever has the least substitutable position. |
| `chain:concept:forced-flow-micro` | forced-deleveraging -> depth-liquidity -> reversion-candidate -> options-positioning | A leveraged account is forced out, the order consumes displayed depth, the dislocation is measurable, and the reversal is available to whoever is already there without needing to be first. | The forced seller is finite, and the reversal is larger than the cost of providing liquidity. |

### Assumptions as first class nodes

| Assumption | Statement | Kill | Load |
|---|---|---|---|
| `queue-is-a-queue` | Grid interconnection is a queue rather than a price. | Projects buy their way forward and energization order stops matching queue order. | 5 |
| `equipment-is-capacity-gated` | Heavy equipment lead times are capacity gates rather than price signals. | Prices clear the backlog and lead times fall while order books stay full. | 5 |
| `firm-load` | Data centre load is firm and does not curtail at system peaks. | Load curtails voluntarily or under contract at peaks. | 4 |
| `elasticity-above-one` | Inference demand is elastic at current prices. | Usage is flat or falls when unit prices fall. | 4 |
| `depreciation-lands-first` | Capacity spending lands in earnings before it lands in revenue. | Revenue arrives with the capex or ahead of it. | 5 |
| `tenants-can-self-build` | The largest tenants have a credible self build alternative. | Tenants sign long deals at posted prices with no own build programme. | 4 |
| `forced-seller-is-finite` | A forced seller is finite and identifiable after the fact. | Dislocations arrive with no identifiable forced side. | 4 |
| `reversal-exceeds-cost` | The post flow reversal is larger than the round trip cost of taking it. | Reversion is smaller than costs at every level. | 5 |
| `subsidy-discipline` | Subsidised capital is less disciplined than equity funded capital. | Subsidised projects cancel at lower rates. | 3 |
| `water-binds-locally` | Water constraints bind locally before globally. | Constraints appear as a global rule rather than site by site. | 3 |
| `core-steel-gate` | Transformer core steel is the binding input rather than labour. | Lead times shorten while steel stays tight or vice versa. | 4 |
| `measured-truth-can-lie` | Every measured association can be an artifact of sample, timing or specification. | A finding holds across samples, periods and specifications. | 4 |
| `graph-is-the-object` | The graph is the research object and the trade is a path through it. | Trades are proposed without a path or a kill. | 3 |
| `elasticity-is-the-moderator` | The sign of the rental spread response to new supply depends on elasticity. | Rental prices fall on new supply in every elasticity regime. | 4 |
| `rate-regime-decides-intensity` | The punishment of capex intensity depends on the rate direction in the window. | Intensity is charged identically across rate directions. | 4 |
| `permits-versus-equipment` | Permitting reform only helps if permits were the binding clock. | Lead times fall when permits fall. | 3 |
| `self-build-threat-is-live` | The self build threat from large tenants is live at every negotiation. | Tenants sign long contracts while building nothing. | 4 |
| `public-markets-cannot-fund-it` | The cycle cannot be funded by public equity alone at this scale. | Issuance covers the announced build. | 3 |
| `link:demand:token-volume->demand:model-efficiency` | Efficiency gains are absorbed by new uses rather than reducing capacity demand. | Capacity demand falls in absolute terms while token volume rises. | 4 |
| `link:demand:token-volume->silicon:hbm-supply` | HBM capacity is the binding constraint on accelerator shipments. | Accelerator shipments rise while HBM supply is flat. | 4 |
| `link:demand:token-volume->power:firm-capacity-scarcity` | Data centre load does not curtail at system peaks. | Firm capacity prices stay flat while data centre load grows. | 4 |
| `link:demand:model-efficiency->power:energization-delay` | Efficiency gains are not immediately absorbed by new demand. | Efficiency improves and power demand for the same workload rises. | 4 |
| `link:silicon:accelerator-lead-time->power:energization-delay` | Silicon and power lead times are comparable and not substitutable. | Clusters energise with siloed silicon or idle powered sites without silicon. | 4 |
| `link:silicon:asic-substitution->silicon:accelerator-resale-value` | ASIC programmes replace rather than complement merchant parts. | Resale values hold while substitution scales. | 4 |
| `link:power:interconnection-queue->power:energization-delay` | Queue positions are real and not reordered by policy. | Projects jump the queue without paying or a rule change. | 4 |
| `link:power:energization-delay->providers:rental-spread` | The bottleneck is real rather than announced. | Spreads narrow while energization delays lengthen. | 4 |
| `link:grid:transformer-lead-time->power:energization-delay` | The transformer is a true gate rather than a schedulable input. | Sites energize without transformers or with substitutes. | 5 |
| `link:grid:transformer-lead-time->grid:utility-capex-plan` | Utilities cannot substitute equipment or buy second hand at scale. | Plans accelerate while lead times lengthen. | 4 |
| `link:grid:rate-case-lag->grid:utility-capex-plan` | Utilities cannot fund indefinite working capital gaps. | Plans accelerate while recovery lags. | 4 |
| `link:grid:wildfire-hardening->grid:utility-capex-plan` | Hardening is mandatory and cannot be deferred. | Growth capex accelerates while hardening spend rises. | 4 |

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
| hidden_edge | `dig:power:goes -> dig:nuc:firm-power` | cross-dig pair sharing ['power'] and observable tokens ['announcements'] | add the typed edge or record why the shared observable stops here |
| hidden_edge | `dig:compute:inference-cost -> dig:compute:rental-to-revenue-link` | cross-dig pair sharing ['compute'] and observable tokens ['provider'] | add the typed edge or record why the shared observable stops here |
| hidden_edge | `dig:compute:inference-cost -> dig:compute:family-exposure-map` | cross-dig pair sharing ['compute'] and observable tokens ['provider'] | add the typed edge or record why the shared observable stops here |
| hidden_edge | `dig:compute:inference-cost -> dig:compute:revenue-per-mw` | cross-dig pair sharing ['compute'] and observable tokens ['provider'] | add the typed edge or record why the shared observable stops here |
| hidden_edge | `dig:compute:inference-cost -> dig:compute:contracted-share` | cross-dig pair sharing ['compute'] and observable tokens ['provider'] | add the typed edge or record why the shared observable stops here |
| hidden_edge | `dig:compute:inference-cost -> dig:compute:lease-spread` | cross-dig pair sharing ['compute'] and observable tokens ['provider'] | add the typed edge or record why the shared observable stops here |
| hidden_edge | `dig:compute:inference-cost -> dig:compute:tenant-concentration` | cross-dig pair sharing ['compute'] and observable tokens ['provider'] | add the typed edge or record why the shared observable stops here |
| hidden_edge | `dig:compute:inference-cost -> dig:compute:equity-transmission` | cross-dig pair sharing ['compute'] and observable tokens ['provider'] | add the typed edge or record why the shared observable stops here |
| hidden_edge | `dig:compute:token-demand -> dig:compute:family-exposure-map` | cross-dig pair sharing ['compute'] and observable tokens ['disclosures'] | add the typed edge or record why the shared observable stops here |

## Propagation paths, truth to payer

| Seed | Path | Hops | Floor | Data in hand | Greatest assumption |
|---|---|---|---|---|---|
| `dig:grid:capex-plan` | `dig:grid:capex-plan` -> `outcome:firm:capex-level` | 1 | E2 | provider-capex-quarterly.csv | The outcome remains the measured object. |
| `dig:providers:firm-capacity` | `dig:providers:firm-capacity` -> `asset:equity:utility-basket` | 1 | E2 | capacity-strategy.csv | The basket remains the traded surface. |
| `dig:providers:provider-margin` | `dig:providers:provider-margin` -> `outcome:firm:cash-flow-revision` | 1 | E2 | provider-capex-quarterly.csv, delivery-revisions.csv, cascade-tape.json | Contracted revenue remains the margin driver. |
| `dig:grid:capacity-auction` | `dig:grid:capacity-auction` -> `dig:providers:firm-capacity` -> `asset:equity:utility-basket` | 2 | E2 | capacity-strategy.csv | The basket remains the traded surface. |
| `dig:grid:rate-case` | `dig:grid:rate-case` -> `dig:grid:capex-plan` -> `outcome:firm:capex-level` | 2 | E2 | provider-capex-quarterly.csv | Capital recovery runs through the rate case process. |
| `dig:providers:credit` | `dig:providers:credit` -> `dig:providers:provider-margin` -> `outcome:firm:cash-flow-revision` | 2 | E2 | delivery-revisions.csv, cascade-tape.json, credit-deal-registry.csv | Margins support the credit that funds new supply. |
| `entity:issuer:company` | `entity:issuer:company` -> `outcome:market:post-event-drift` | 1 | E3 | capacity-event-ledger.csv | Both nodes read the same source. |
| `outcome:market:abnormal-return` | `outcome:market:abnormal-return` -> `outcome:market:post-event-drift` | 1 | E3 | capacity-event-ledger.csv | Both nodes read the same source. |
| `claim:pricing:underreacts` | `claim:pricing:underreacts` -> `outcome:firm:capex-level` | 1 | E4 | provider-capex-quarterly.csv | The node receives a verified representation and a declared role |
| `claim:pricing:underreacts` | `claim:pricing:underreacts` -> `outcome:firm:capex-timing` | 1 | E4 | provider-capex-quarterly.csv | The node receives a verified representation and a declared role |
| `dig:grid:allowed-return` | `dig:grid:allowed-return` -> `dig:providers:firm-capacity` -> `asset:equity:utility-basket` | 2 | E2 | capacity-strategy.csv | The basket remains the traded surface. |
| `dig:providers:load-growth` | `dig:providers:load-growth` -> `dig:providers:firm-capacity` -> `asset:equity:utility-basket` | 2 | E2 | capacity-strategy.csv | Load growth raises the firm capacity requirement. |
| `dig:providers:ppa-price` | `dig:providers:ppa-price` -> `dig:providers:firm-capacity` -> `asset:equity:utility-basket` | 2 | E2 | capacity-strategy.csv | Scarcity of firm capacity sets the price of contracts. |
| `dig:turbine:heavy-duty` | `dig:turbine:heavy-duty` -> `dig:providers:firm-capacity` -> `asset:equity:utility-basket` | 2 | E2 | capacity-strategy.csv | Turbines remain the marginal firm capacity technology. |
| `claim:pricing:underreacts` | `claim:pricing:underreacts` -> `outcome:firm:revenue-level` | 1 | E4 | needs data | The node receives a verified representation and a declared role |
| `claim:pricing:underreacts` | `claim:pricing:underreacts` -> `outcome:firm:gross-margin` | 1 | E4 | needs data | The node receives a verified representation and a declared role |
| `claim:pricing:underreacts` | `claim:pricing:underreacts` -> `outcome:firm:operating-margin` | 1 | E4 | needs data | The node receives a verified representation and a declared role |
| `outcome:portfolio:net-pnl` | `outcome:portfolio:net-pnl` -> `asset:equity:sector-basket` | 1 | E4 | needs data | The cross-layer relation is supported by point-in-time evidence |
| `outcome:portfolio:net-pnl` | `outcome:portfolio:net-pnl` -> `asset:equity:market-index` | 1 | E4 | needs data | The cross-layer relation is supported by point-in-time evidence |
| `outcome:portfolio:net-pnl` | `outcome:portfolio:net-pnl` -> `asset:equity:supplier-basket` | 1 | E4 | needs data | The cross-layer relation is supported by point-in-time evidence |
| `outcome:portfolio:net-pnl` | `outcome:portfolio:net-pnl` -> `asset:equity:utility-basket` | 1 | E4 | needs data | The cross-layer relation is supported by point-in-time evidence |
| `outcome:portfolio:net-pnl` | `outcome:portfolio:net-pnl` -> `asset:options:defined-risk-spread` | 1 | E4 | needs data | The cross-layer relation is supported by point-in-time evidence |
| `dig:compute:capex-intensity` | `dig:compute:capex-intensity` -> `dig:compute:provider-revenue-line` | 1 | E2 | compute-price-monthly.csv, provider-capex-quarterly.csv | Investment outruns revenue before it either lifts revenue or compresses margin. |
| `dig:compute:capex-intensity` | `dig:compute:capex-intensity` -> `dig:compute:depreciation-policy` | 1 | E2 | compute-price-monthly.csv, provider-capex-quarterly.csv | High intensity becomes depreciation and interest inside reported earnings. |
| `dig:compute:capex-intensity` | `dig:compute:capex-intensity` -> `dig:compute:intensity-charge` | 1 | E2 | compute-price-monthly.csv, provider-capex-quarterly.csv | A capex intensity surprise relative to revenue is charged in the equity over weeks. |

## Reproduce

    python3 scripts/build_graph_propagation.py
    python3 scripts/render_graph_propagation.py
