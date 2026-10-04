# Connection index

Method owner: `docs/plan/deep-chaining.md`. Every node carries its own typed connections and
its chain hops. Inferred connections are questions with a type and a falsifier.

- Nodes indexed: **169,985** (725 core nodes from the manifest
  and the digs, 169,260 skeleton sub-nodes)
- Typed connections: **1,179,818**
- Core degree: min 49, median 74, max 150; **724 core nodes at 50+ connections (99.9%)**
- Skeleton degree: structural only, median 5
- Chains 74, hops 145, bridges 54

## Connection types

| Type | Count |
|---|---|
| `sibling_subnode` | 482,070 |
| `part_of` | 169,908 |
| `splits_into` | 169,258 |
| `refined_by` | 164,910 |
| `refines` | 164,904 |
| `co_layer_peer` | 18,143 |
| `ties_by_source` | 3,848 |
| `shares_semantics` | 1,616 |
| `ties_by_observable` | 1,007 |
| `candidate_for` | 914 |
| `same_dig_context` | 842 |
| `conditions` | 698 |
| `ties_by_player` | 672 |
| `contains` | 162 |
| `chain_precedes` | 143 |
| `chain_follows` | 143 |
| `requires` | 110 |
| `belongs_to` | 96 |

## Worked node record

`mechanism:capacity:transformer-bottleneck` (mechanism), degree 75. Statuses: {'proposed': 4, 'curated': 4, 'declared': 36, 'inferred': 31}.

| Connected to | Type | Status | Why | Falsifier |
|---|---|---|---|---|
| `claim:pricing:underreacts` | candidate_for | proposed | declared or curated edge | Keep the node inactive and do not promote it |
| `outcome:firm:cash-flow-revision` | conditions | proposed | declared or curated edge | Record the pair as unsupported rather than ranking it |
| `mechanism:capacity:interconnection-bottleneck` | part_of | proposed | declared or curated edge reverse | Remove the lineage edge when the shared mechanism is not documented |
| `mechanism:capacity:cooling-bottleneck` | part_of | proposed | declared or curated edge | Remove the lineage edge when the shared mechanism is not documented |
| `dig:power:lpt` | anchors | curated | declared or curated edge reverse | The dig contradicts the anchor and the anchor is updated. |
| `dig:switch:gear` | anchors | curated | declared or curated edge reverse | Switchgear lead times decouple from transformer lead times. |
| `sub:mechanism:capacity:transformer-bottleneck:trigger` | splits_into | declared | structural child | The decomposition dimension does not apply to this node. |
| `sub:sub:mechanism:capacity:transformer-bottleneck:trigger:composition` | refines | declared | grandchild refinement of this node | The grandchild refinement does not apply to this node. |
| `sub:sub:mechanism:capacity:transformer-bottleneck:trigger:inputs` | refines | declared | grandchild refinement of this node | The grandchild refinement does not apply to this node. |
| `sub:sub:mechanism:capacity:transformer-bottleneck:trigger:constraints` | refines | declared | grandchild refinement of this node | The grandchild refinement does not apply to this node. |
| `sub:sub:mechanism:capacity:transformer-bottleneck:trigger:observables` | refines | declared | grandchild refinement of this node | The grandchild refinement does not apply to this node. |
| `sub:sub:mechanism:capacity:transformer-bottleneck:trigger:substitutes` | refines | declared | grandchild refinement of this node | The grandchild refinement does not apply to this node. |
| `sub:mechanism:capacity:transformer-bottleneck:transmission-path` | splits_into | declared | structural child | The decomposition dimension does not apply to this node. |
| `sub:sub:mechanism:capacity:transformer-bottleneck:transmission-path:composition` | refines | declared | grandchild refinement of this node | The grandchild refinement does not apply to this node. |
| `sub:sub:mechanism:capacity:transformer-bottleneck:transmission-path:inputs` | refines | declared | grandchild refinement of this node | The grandchild refinement does not apply to this node. |
| `sub:sub:mechanism:capacity:transformer-bottleneck:transmission-path:constraints` | refines | declared | grandchild refinement of this node | The grandchild refinement does not apply to this node. |
| `sub:sub:mechanism:capacity:transformer-bottleneck:transmission-path:observables` | refines | declared | grandchild refinement of this node | The grandchild refinement does not apply to this node. |
| `sub:sub:mechanism:capacity:transformer-bottleneck:transmission-path:substitutes` | refines | declared | grandchild refinement of this node | The grandchild refinement does not apply to this node. |
| `sub:mechanism:capacity:transformer-bottleneck:rate-limiter` | splits_into | declared | structural child | The decomposition dimension does not apply to this node. |
| `sub:sub:mechanism:capacity:transformer-bottleneck:rate-limiter:composition` | refines | declared | grandchild refinement of this node | The grandchild refinement does not apply to this node. |
| `sub:sub:mechanism:capacity:transformer-bottleneck:rate-limiter:inputs` | refines | declared | grandchild refinement of this node | The grandchild refinement does not apply to this node. |
| `sub:sub:mechanism:capacity:transformer-bottleneck:rate-limiter:constraints` | refines | declared | grandchild refinement of this node | The grandchild refinement does not apply to this node. |
| `sub:sub:mechanism:capacity:transformer-bottleneck:rate-limiter:observables` | refines | declared | grandchild refinement of this node | The grandchild refinement does not apply to this node. |
| `sub:sub:mechanism:capacity:transformer-bottleneck:rate-limiter:substitutes` | refines | declared | grandchild refinement of this node | The grandchild refinement does not apply to this node. |
| `sub:mechanism:capacity:transformer-bottleneck:observable` | splits_into | declared | structural child | The decomposition dimension does not apply to this node. |
| `sub:sub:mechanism:capacity:transformer-bottleneck:observable:composition` | refines | declared | grandchild refinement of this node | The grandchild refinement does not apply to this node. |
| `sub:sub:mechanism:capacity:transformer-bottleneck:observable:inputs` | refines | declared | grandchild refinement of this node | The grandchild refinement does not apply to this node. |
| `sub:sub:mechanism:capacity:transformer-bottleneck:observable:constraints` | refines | declared | grandchild refinement of this node | The grandchild refinement does not apply to this node. |
| `sub:sub:mechanism:capacity:transformer-bottleneck:observable:observables` | refines | declared | grandchild refinement of this node | The grandchild refinement does not apply to this node. |
| `sub:sub:mechanism:capacity:transformer-bottleneck:observable:substitutes` | refines | declared | grandchild refinement of this node | The grandchild refinement does not apply to this node. |
| `sub:mechanism:capacity:transformer-bottleneck:lag-profile` | splits_into | declared | structural child | The decomposition dimension does not apply to this node. |
| `sub:sub:mechanism:capacity:transformer-bottleneck:lag-profile:composition` | refines | declared | grandchild refinement of this node | The grandchild refinement does not apply to this node. |
| `sub:sub:mechanism:capacity:transformer-bottleneck:lag-profile:inputs` | refines | declared | grandchild refinement of this node | The grandchild refinement does not apply to this node. |
| `sub:sub:mechanism:capacity:transformer-bottleneck:lag-profile:constraints` | refines | declared | grandchild refinement of this node | The grandchild refinement does not apply to this node. |
| `sub:sub:mechanism:capacity:transformer-bottleneck:lag-profile:observables` | refines | declared | grandchild refinement of this node | The grandchild refinement does not apply to this node. |
| `sub:sub:mechanism:capacity:transformer-bottleneck:lag-profile:substitutes` | refines | declared | grandchild refinement of this node | The grandchild refinement does not apply to this node. |
| `sub:mechanism:capacity:transformer-bottleneck:payer-incidence` | splits_into | declared | structural child | The decomposition dimension does not apply to this node. |
| `sub:sub:mechanism:capacity:transformer-bottleneck:payer-incidence:composition` | refines | declared | grandchild refinement of this node | The grandchild refinement does not apply to this node. |
| `sub:sub:mechanism:capacity:transformer-bottleneck:payer-incidence:inputs` | refines | declared | grandchild refinement of this node | The grandchild refinement does not apply to this node. |
| `sub:sub:mechanism:capacity:transformer-bottleneck:payer-incidence:constraints` | refines | declared | grandchild refinement of this node | The grandchild refinement does not apply to this node. |
| `sub:sub:mechanism:capacity:transformer-bottleneck:payer-incidence:observables` | refines | declared | grandchild refinement of this node | The grandchild refinement does not apply to this node. |
| `sub:sub:mechanism:capacity:transformer-bottleneck:payer-incidence:substitutes` | refines | declared | grandchild refinement of this node | The grandchild refinement does not apply to this node. |
| `entity:physical:transformer-facility` | shares_semantics | inferred | 2 shared meaning tokens across layers | The overlap is generic vocabulary and the nodes move separately. |
| `feature:equipment:transformer-backlog` | shares_semantics | inferred | 2 shared meaning tokens across layers | The overlap is generic vocabulary and the nodes move separately. |
| `feature:equipment:transformer-lead-days` | shares_semantics | inferred | 2 shared meaning tokens across layers | The overlap is generic vocabulary and the nodes move separately. |
| `dig:bess:systems` | co_layer_peer | inferred | same layer peer family | The layer label does not imply a comparable role. |
| `dig:compute:inventory-state` | co_layer_peer | inferred | same layer peer family | The layer label does not imply a comparable role. |
| `dig:compute:power-commitment` | co_layer_peer | inferred | same layer peer family | The layer label does not imply a comparable role. |
| `dig:compute:provider-capex` | co_layer_peer | inferred | same layer peer family | The layer label does not imply a comparable role. |
| `dig:compute:rental-to-revenue-link` | co_layer_peer | inferred | same layer peer family | The layer label does not imply a comparable role. |
| `dig:cool:liquid-cooling` | co_layer_peer | inferred | same layer peer family | The layer label does not imply a comparable role. |
| `dig:cool:load` | co_layer_peer | inferred | same layer peer family | The layer label does not imply a comparable role. |
| `dig:copper:concentrate` | co_layer_peer | inferred | same layer peer family | The layer label does not imply a comparable role. |
| `dig:copper:power-cost` | co_layer_peer | inferred | same layer peer family | The layer label does not imply a comparable role. |
| `dig:copper:scrap` | co_layer_peer | inferred | same layer peer family | The layer label does not imply a comparable role. |
| `dig:copper:smelters` | co_layer_peer | inferred | same layer peer family | The layer label does not imply a comparable role. |
| `dig:cycles:buildout` | co_layer_peer | inferred | same layer peer family | The layer label does not imply a comparable role. |
| `dig:cycles:overbuild` | co_layer_peer | inferred | same layer peer family | The layer label does not imply a comparable role. |
| `dig:cycles:second-wave` | co_layer_peer | inferred | same layer peer family | The layer label does not imply a comparable role. |
| `dig:cycles:shakeout` | co_layer_peer | inferred | same layer peer family | The layer label does not imply a comparable role. |

Chain memberships for this node: `chain:bridge:transformer-lpt-to-anchor` at hop:bridge:transformer-lpt-to-anchor:01, `chain:bridge:switchgear-to-anchor` at hop:bridge:switchgear-to-anchor:01.

## Worked chain, with hop addresses

`dig:fcc:catalyst-minerals` resolves hop by hop, so any node downstream carries its own sub-address:

| Hop | From | To | Relation | Condition | Falsifier |
|---|---|---|---|---|---|
| `hop:dig:fcc:catalyst-minerals:01` | `dig:fcc:gasoline-demand` | `dig:fcc:refinery-runs` | drives | Gasoline demand sets refinery utilisation within the capacity constraint. | Runs fall while gasoline demand rises. |
| `hop:dig:fcc:catalyst-minerals:02` | `dig:fcc:refinery-runs` | `dig:fcc:fcc-unit-throughput` | drives | FCC units take the marginal barrel because they make the highest value barrel. | Hydrocracking takes the marginal throughput instead. |
| `hop:dig:fcc:catalyst-minerals:03` | `dig:fcc:fcc-unit-throughput` | `dig:fcc:catalyst-inventory` | requires | Catalyst deactivates and must be made up at a rate tied to throughput. | Catalyst life extends without throughput loss. |
| `hop:dig:fcc:catalyst-minerals:04` | `dig:fcc:catalyst-inventory` | `dig:fcc:y-zeolite` | chain_precedes |  |  |
| `hop:dig:fcc:catalyst-minerals:05` | `dig:fcc:y-zeolite` | `dig:fcc:rare-earth-stabilisers` | chain_precedes |  |  |
| `hop:dig:fcc:catalyst-minerals:06` | `dig:fcc:rare-earth-stabilisers` | `dig:fcc:lanthanum-cerium-market` | chain_precedes |  |  |
| `hop:dig:fcc:catalyst-minerals:07` | `dig:fcc:lanthanum-cerium-market` | `dig:fcc:separation-plants` | chain_precedes |  |  |
| `hop:dig:fcc:catalyst-minerals:08` | `dig:fcc:separation-plants` | `dig:fcc:kaolin-and-alumina` | chain_precedes |  |  |
| `hop:dig:fcc:catalyst-minerals:09` | `dig:fcc:kaolin-and-alumina` | `dig:fcc:hydrotreating-catalysts` | chain_precedes |  |  |

The same chain in the captain's form: `dig:fcc:catalyst-inventory` holds `dig:fcc:y-zeolite` with the edge `requires`, and the zeolite node holds `dig:fcc:rare-earth-stabilisers` as chain step 5, resolvable from either end.

## Bridges, the cross-dig links

| Bridge | From | To | Relation | Condition | Falsifier |
|---|---|---|---|---|---|
| `bridge:fcc-moly-to-turbine-rhenium` | `dig:fcc:molybdenum-supply` | `dig:turbine:rhenium` | co_produces | Rhenium recovery stays tied to molybdenum roasting rather than dedicated circuits. | Rhenium supply decouples from molybdenum throughput. |
| `bridge:fcc-nickel-to-turbine-nickel` | `dig:fcc:nickel-cobalt-supply` | `dig:turbine:nickel` | competes_for | Both sides buy nickel at index-linked prices. | One side is fully hedged or substitutes away. |
| `bridge:transformer-windings-to-copper-stack` | `dig:power:windings-copper` | `dig:material:copper-stack` | draws_from | Grid and data center buildout remains copper intensive. | Aluminium substitution takes the winding share. |
| `bridge:sic-graphite-to-bess-graphite` | `dig:sic:graphite` | `dig:bess:graphite` | competes_for | Chinese export policy treats both products comparably. | Licences separate the two product lines. |
| `bridge:turbine-hafnium-to-nuclear-cladding` | `dig:turbine:hafnium` | `dig:nuc:cladding` | co_produces | Zirconium and hafnium continue to be split at the same plants. | Cladding moves to alternative materials. |
| `bridge:switchgear-fluorite-to-cooling-refrigerants` | `dig:switch:fluorite` | `dig:cool:refrigerants` | feeds | Fluorine chemistry remains the route for both products. | Alternative chemistries displace one side. |
| `bridge:sic-quartz-to-fiber-preform` | `dig:sic:quartz` | `dig:fiber:preform` | competes_for | Both industries keep needing the same grade of silica. | Synthetic silica displaces natural quartz on one side. |
| `bridge:fiber-helium-to-sic-crystal-growth` | `dig:fiber:helium` | `dig:sic:crystal-growth` | competes_for | Helium and rare gas supply stays tight. | Recovery projects loosen the market. |
| `bridge:bess-foil-to-copper-stack` | `dig:bess:copper-foil` | `dig:material:copper-stack` | draws_from | Foil demand grows with storage deployment. | Alternative current collectors take share. |
| `bridge:rare-earth-separation-to-fcc-separation` | `dig:ree:separation` | `dig:fcc:separation-plants` | competes_for | La and Ce separation capacity is shared with the heavy rare earth circuits. | Dedicated catalyst grade lines absorb the demand. |
| `bridge:labor-crews-to-turbine-casters` | `dig:labor:crews` | `dig:turbine:casters` | competes_for | Both sectors hire from the same training pipeline. | Programmes expand to cover both. |
| `bridge:cooling-load-to-datacenter-site` | `dig:cool:load` | `entity:datacenter:site` | anchors | Cooling load remains a material share of site engineering. | Cooling becomes a minor design line. |
| `bridge:nuclear-firm-power-to-datacenter-site` | `dig:nuc:firm-power` | `entity:datacenter:site` | supplies | Behind the meter and PPA structures keep growing. | Operators return to grid supply only. |
| `bridge:fcc-moly-to-copper-factor` | `dig:fcc:molybdenum-supply` | `factor:commodity:copper` | derives_from | Byproduct recovery stays economical. | Molybdenum becomes a primary mining product. |
| `bridge:transformer-lpt-to-anchor` | `dig:power:lpt` | `mechanism:capacity:transformer-bottleneck` | anchors | The anchor node remains the mechanism of record. | The dig contradicts the anchor and the anchor is updated. |
| `bridge:turbine-heavy-duty-to-anchor` | `dig:turbine:heavy-duty` | `mechanism:capacity:constraint` | anchors | Capacity constraint remains the governing mechanism. | Another bottleneck explains the same slips. |
| `bridge:hvdc-transfer-to-anchor` | `dig:hvdc:transfer` | `mechanism:capacity:interconnection-bottleneck` | anchors | Transfer additions remain gated by the bottleneck. | Transfer capacity expands freely. |
| `bridge:bess-systems-to-anchor` | `dig:bess:systems` | `mechanism:capacity:constraint` | anchors | Storage remains the marginal flexible resource. | Other flexibility dominates. |
| `bridge:sic-devices-to-anchor` | `dig:sic:power-devices` | `mechanism:capacity:constraint` | anchors | Semiconductors remain on the critical path. | Inventories cover project schedules durably. |
| `bridge:rare-earth-magnets-to-anchor` | `dig:ree:magnets` | `asset:equity:supplier-basket` | anchors | The basket remains the traded surface. | The expression changes instrument. |
| `bridge:cooling-load-to-anchor` | `dig:cool:load` | `mechanism:capacity:cooling-bottleneck` | anchors | Density growth continues. | Cooling stops binding site schedules. |
| `bridge:switchgear-to-anchor` | `dig:switch:gear` | `mechanism:capacity:transformer-bottleneck` | anchors | Both remain gated by the same equipment complex. | Switchgear lead times decouple from transformer lead times. |
| `bridge:fiber-interconnect-to-anchor` | `dig:fiber:interconnect` | `entity:datacenter:site` | anchors | Compute growth keeps pulling fiber. | Compute stops needing new interconnect. |
| `bridge:labor-crews-to-anchor` | `dig:labor:crews` | `mechanism:capacity:labor-bottleneck` | anchors | Labour remains a binding constraint in the regions of the buildout. | Crew supply clears and equipment becomes the only constraint. |
| `bridge:copper-demand-to-anchor` | `dig:copper:demand` | `factor:commodity:copper` | anchors | The factor remains the market reference. | Contract structures decouple physical from factor. |
| `bridge:nuclear-firm-power-to-anchor` | `dig:nuc:firm-power` | `mechanism:capacity:constraint` | anchors | Firm power remains the binding commitment for load growth. | Firm obligations loosen. |
| `bridge:fcc-catalyst-to-anchor` | `dig:fcc:catalyst-inventory` | `mechanism:capacity:constraint` | anchors | Catalyst supply remains a material constraint for refiners. | Catalyst is never supply constrained. |
| `bridge:compute-power-to-firm-capacity` | `dig:compute:power-commitment` | `dig:providers:firm-capacity` | draws_from | Firm capacity remains the product operators contract for. | Operators build their own generation entirely. |
| `bridge:compute-tokens-to-load-growth` | `dig:compute:token-demand` | `dig:grid:load-growth` | drives | Workload growth continues to convert into electricity demand. | Efficiency decouples workload from power. |
| `bridge:compute-inventory-to-overbuild` | `dig:compute:inventory-state` | `dig:cycles:overbuild` | marker_of | Listed prices and availability reflect inventory. | Prices are policy artifacts decoupled from utilisation. |
| `bridge:providers-firm-to-nuclear` | `dig:providers:firm-capacity` | `dig:nuc:firm-power` | competes_for | Nuclear remains a contracted firm source. | Nuclear capacity is allocated outside the market. |
| `bridge:providers-firm-to-turbines` | `dig:providers:firm-capacity` | `dig:turbine:heavy-duty` | requires | Turbines remain the marginal firm capacity technology. | Storage or imports satisfy firm obligations. |
| `bridge:grid-contracts-to-cooling-load` | `dig:grid:special-contracts` | `dig:cool:load` | prices | Large load tariffs remain the allocation mechanism. | Standard tariffs absorb the cost. |
| `bridge:grid-planning-to-transformers` | `dig:grid:transmission-planning` | `dig:power:lpt` | requires | Transmission and generation compete for the same equipment. | Transmission uses distinct equipment classes. |
| `bridge:cycles-buildout-to-transformers` | `dig:cycles:buildout` | `dig:power:lpt` | observed_in | Equipment bottlenecks recur in buildout phases. | Equipment supply keeps pace this time. |
| `bridge:cycles-fiber-to-interconnection` | `dig:cycles:fiber` | `mechanism:capacity:interconnection-bottleneck` | analogue_of | Interconnection capacity can be re-used by later projects. | Queue capacity is consumed immediately on award. |
| `bridge:cycles-second-wave-to-transmission-owner` | `dig:cycles:second-wave` | `dig:providers:transmission-owner` | same_shape | Regulated ownership remains the end state. | Political change breaks the regulated model. |
| `bridge:exec-timestamps-to-queue-milestones` | `dig:exec:event-stamp` | `event:power:queue-milestone` | observes | Queue updates are published with usable timestamps. | Queue updates are undated or retrospective. |
| `bridge:exec-entry-to-drift` | `dig:exec:entry-window` | `outcome:market:post-event-drift` | tests | Drift survives delayed entry. | Drift vanishes when entries are delayed. |
| `bridge:compute-capex-to-grid-plan` | `dig:compute:provider-capex` | `dig:grid:capex-plan` | drives | Provider projects reach utilities as committed load. | Projects stay behind the meter on self generation. |
| `bridge:cycles-colocation-to-datacenter-site` | `dig:cycles:colocation` | `entity:datacenter:site` | analogue_of | Site economics repeat the colocation pattern. | AI sites have fundamentally different contracts. |
| `bridge:providers-margin-to-cash-flow` | `dig:providers:provider-margin` | `outcome:firm:cash-flow-revision` | feeds | Contracted revenue remains the margin driver. | Margins are regulated to cost of service. |
| `bridge:grid-capex-to-anchor` | `dig:grid:capex-plan` | `outcome:firm:capex-level` | anchors | The outcome remains the measured object. | The dig contradicts the outcome construction. |
| `bridge:compute-rental-to-anchor` | `dig:compute:rental-change` | `feature:compute:rental-price` | anchors | The feature remains the measured object. | The dig contradicts the feature construction. |
| `bridge:providers-firm-to-anchor` | `dig:providers:firm-capacity` | `asset:equity:utility-basket` | anchors | The basket remains the traded surface. | The expression moves to credit or contracts. |
| `bridge:cycles-buildout-to-anchor` | `dig:cycles:buildout` | `mechanism:capacity:constraint` | anchors | Capacity constraint remains the governing mechanism. | Cycles stop repeating. |
| `bridge:exec-entry-to-anchor` | `dig:exec:entry-window` | `event:sec:8k-material-agreement` | anchors | Disclosures remain the event class. | The edge moves to non-disclosure events. |
| `bridge:hvdc-cable-to-copper-demand` | `dig:hvdc:copper-aluminium` | `dig:copper:demand` | feeds | Cable orders translate into conductor demand within the same procurement window. | Cable makers hold conductor inventory through the build cycle and orders do not reach the metal market. |
| `bridge:compute-capex-to-grid-capex` | `dig:compute:capex-intensity` | `dig:grid:capex-plan` | competes_for | Both are constrained by the same equipment and labor supply, so one raises the other's cost and lead time. | Equipment lead times and crew wages are flat while both capex lines rise. |
| `bridge:provider-capex-to-equity` | `dig:compute:provider-capex` | `dig:compute:equity-transmission` | drives | Capex is funded with debt or equity and its depreciation reaches reported earnings within two years. | Capex is fully expensed against revenue with no earnings footprint, or is so contracted that it carries no market risk. |
| `bridge:token-demand-to-provider-revenue` | `dig:compute:token-demand` | `dig:compute:provider-revenue-line` | drives | Demand growth shows up as utilisation first and revenue per megawatt second. | Provider revenue grows while token volume is flat, or falls while token volume grows. |
| `bridge:goes-to-compute-power` | `dig:power:goes` | `dig:compute:power-commitment` | competes_for | The same mills and casters serve both the grid equipment and the on site power equipment. | Data center power equipment is sourced from a supply base independent of grid transformer steel. |
| `bridge:core-stacking-to-nuclear-firm-power` | `dig:power:core-stacking` | `dig:nuc:firm-power` | feeds | Nuclear restarts and new builds order grid equipment from the same supply as everything else. | Nuclear projects source their electrical equipment outside the shared supply chain. |
| `bridge:lpt-to-sic-devices` | `dig:power:lpt` | `dig:sic:power-devices` | co_layer_peer | Both sit in the same substation and converter budgets, so their orders move together. | Substation budgets show one rising while the other falls for reasons of technology substitution. |

## Under-connected core nodes, the research queue

These core nodes do not yet reach fifty typed connections. The gap is the list of digs still
to write, not a licence to pad:

| Node | Degree |
|---|---|
| `concept:thesis:delivery-gap` | 49 |

