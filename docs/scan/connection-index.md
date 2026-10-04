# Connection index

Method owner: `docs/plan/deep-chaining.md`. Every node carries its own typed connections and
its chain hops. Inferred connections are questions with a type and a falsifier.

- Nodes indexed: **23,791** (643 core nodes from the manifest
  and the digs, 23,148 skeleton sub-nodes)
- Typed connections: **206,757**
- Core degree: min 48, median 73, max 150; **641 core nodes at 50+ connections (99.7%)**
- Skeleton degree: structural only, median 6
- Chains 40, hops 89, bridges 27

## Connection types

| Type | Count |
|---|---|
| `sibling_subnode` | 96,450 |
| `part_of` | 23,796 |
| `splits_into` | 23,146 |
| `refined_by` | 19,290 |
| `refines` | 19,276 |
| `co_layer_peer` | 15,732 |
| `ties_by_source` | 3,716 |
| `shares_semantics` | 1,596 |
| `candidate_for` | 914 |
| `ties_by_observable` | 799 |
| `conditions` | 670 |
| `same_dig_context` | 428 |
| `ties_by_player` | 194 |
| `contains` | 162 |
| `belongs_to` | 96 |
| `requires` | 94 |
| `chain_precedes` | 87 |
| `chain_follows` | 87 |

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
| `dig:cool:liquid-cooling` | co_layer_peer | inferred | same layer peer family | The layer label does not imply a comparable role. |
| `dig:cool:load` | co_layer_peer | inferred | same layer peer family | The layer label does not imply a comparable role. |
| `dig:copper:concentrate` | co_layer_peer | inferred | same layer peer family | The layer label does not imply a comparable role. |
| `dig:copper:power-cost` | co_layer_peer | inferred | same layer peer family | The layer label does not imply a comparable role. |
| `dig:copper:scrap` | co_layer_peer | inferred | same layer peer family | The layer label does not imply a comparable role. |
| `dig:copper:smelters` | co_layer_peer | inferred | same layer peer family | The layer label does not imply a comparable role. |
| `dig:fcc:catalyst-inventory` | co_layer_peer | inferred | same layer peer family | The layer label does not imply a comparable role. |
| `dig:fcc:fcc-unit-throughput` | co_layer_peer | inferred | same layer peer family | The layer label does not imply a comparable role. |
| `dig:fcc:separation-plants` | co_layer_peer | inferred | same layer peer family | The layer label does not imply a comparable role. |
| `dig:fiber:interconnect` | co_layer_peer | inferred | same layer peer family | The layer label does not imply a comparable role. |
| `dig:hvdc:converters` | co_layer_peer | inferred | same layer peer family | The layer label does not imply a comparable role. |
| `dig:hvdc:transfer` | co_layer_peer | inferred | same layer peer family | The layer label does not imply a comparable role. |
| `dig:labor:apprenticeship` | co_layer_peer | inferred | same layer peer family | The layer label does not imply a comparable role. |
| `dig:labor:crews` | co_layer_peer | inferred | same layer peer family | The layer label does not imply a comparable role. |

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

## Under-connected core nodes, the research queue

These core nodes do not yet reach fifty typed connections. The gap is the list of digs still
to write, not a licence to pad:

| Node | Degree |
|---|---|
| `strategy:monitor:scarcity-state` | 48 |
| `concept:thesis:delivery-gap` | 49 |

