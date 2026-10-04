# Decomposition: the graph at sub-node resolution

Method owner: `docs/plan/decomposition.md`. Every node decomposes into at least six children
along the dimensions of its layer, and every child decomposes again. The skeleton is written
out and labelled `proposed_unverified`; the curated digs are where domain knowledge fills the
levels with named minerals, suppliers, observables and payers.

**Written graph: 168,281 nodes** (569 declared + 162,204 skeleton children + 5,508 children of curated dig nodes), 167,712 split edges.

- Manifest nodes decomposed: 569, minimum children per node: 6

- Curated dig nodes: 153, digs: 20

## The dimensions

| Layer | Six sub-items |
|---|---|
| source | access path, update cadence, revision behavior, entity key, point-in-time guarantee, licensing |
| dataset | schema, coverage universe, clock, vintage archive, join keys, missingness pattern |
| feature | construction inputs, measurement clock, normalization, lookahead risk, stability, economic meaning |
| mechanism | trigger, transmission path, rate limiter, observable, lag profile, payer incidence |
| factor | measurement proxy, horizon, conditioning state, transmission, crowding, payer incidence |
| entity | legal structure, segment mapping, identifiers, exposure map, counterparties, disclosure clock |
| asset | instrument mechanics, liquidity, borrow and short constraints, option surface, credit terms, financing |
| outcome | measurement window, benchmark, sign convention, accounting bridge, revision behavior, falsifier |
| event | detection rule, timestamp source, confirmation lag, agenda ambiguity, clustering, placebo design |
| assumption | test design, failure mode, blast radius, owner, monitoring cadence, kill threshold |
| claim | mechanism link, evidence requirement, null, multiplicity, horizon, cost ceiling |
| experiment | design, sample, power, null, placebo, stopping rule |
| evidence | provenance, extraction method, precision, timestamp, source agreement, decay |
| rule | statement, scope, override, enforcement point, violation handling, audit trail |
| contract | obligation, trigger, notice, penalty, assignment, term |
| strategy | signal, sizing, costs, capacity, kill switch, funding |
| implementation | interface, state, failure mode, test, observability, rollout |
| physical and raw | composition, inputs, constraints, observables, substitutes, payers |

## The skeleton, sampled

Six rows from `docs/scan/decomposition.jsonl.gz`, one per manifest node family, to show the
schema and the status honesty:

| Child id | Parent | Dimension | Meaning | Status |
|---|---|---|---|---|
| `sub:source:sec:edgar:access-path` | `source:sec:edgar` | access path | the access path of Original SEC filings and exhibits | proposed_unverified |
| `sub:sub:source:sec:edgar:access-path:composition` | `sub:source:sec:edgar:access-path` | composition | the composition of the access path of Original SEC filings and exhibits | proposed_unverified |
| `sub:sub:source:sec:edgar:access-path:inputs` | `sub:source:sec:edgar:access-path` | inputs | the inputs of the access path of Original SEC filings and exhibits | proposed_unverified |
| `sub:sub:source:sec:edgar:access-path:constraints` | `sub:source:sec:edgar:access-path` | constraints | the constraints of the access path of Original SEC filings and exhibits | proposed_unverified |
| `sub:sub:source:sec:edgar:access-path:observables` | `sub:source:sec:edgar:access-path` | observables | the observables of the access path of Original SEC filings and exhibits | proposed_unverified |
| `sub:sub:source:sec:edgar:access-path:substitutes` | `sub:source:sec:edgar:access-path` | substitutes | the substitutes of the access path of Original SEC filings and exhibits | proposed_unverified |

## The curated digs

### Gasoline demand to the minerals under the FCC catalyst

`dig:fcc:catalyst-minerals` · root `mechanism:capacity:constraint` · ceiling **testable** · nodes 15 · edges 8

**Why.** The crack spread is the visible end. The load path runs through the refinery's fluid catalytic cracking unit, into the catalyst, into the zeolite, into the rare earths that stabilise it, and out to a small set of separation plants. Almost none of that is in any cross-asset model.

**Chain.** `dig:fcc:gasoline-demand` -> `dig:fcc:refinery-runs` -> `dig:fcc:fcc-unit-throughput` -> `dig:fcc:catalyst-inventory` -> `dig:fcc:y-zeolite` -> `dig:fcc:rare-earth-stabilisers` -> `dig:fcc:lanthanum-cerium-market` -> `dig:fcc:separation-plants` -> `dig:fcc:kaolin-and-alumina` -> `dig:fcc:hydrotreating-catalysts`

**Greatest assumption.** Rare earth and molybdenum demand from refining catalysts is material enough at the margin to move the mineral markets before the refining margin moves them.

**Kill test.** Refinery catalyst demand is flat or shrinking (catalyst life extensions, lower gasoline runs) while mineral prices move for unrelated reasons.

| Node | Layer | Players | Observables | Payer | Evidence | Source |
|---|---|---|---|---|---|---|
| **US gasoline demand** `dig:fcc:gasoline-demand` | factor | none named | EIA weekly petroleum status report | refiners | E2 | EIA |
| **Refinery utilisation and crude runs** `dig:fcc:refinery-runs` | factor | none named | EIA refinery utilisation | refiners | E2 | EIA |
| **FCC unit throughput** `dig:fcc:fcc-unit-throughput` | mechanism | none named | refinery capacity reports; 10-K unit descriptions | refiners | E2 | EIA refinery capacity report |
| **Fresh catalyst additions and inventory** `dig:fcc:catalyst-inventory` | mechanism | Albemarle, W.R. Grace, BASF, Honeywell UOP, Sinopec Catalyst | catalyst maker segment revenue and volumes; 10-Q commentary | refiners | E2 | company filings |
| **Y-zeolite** `dig:fcc:y-zeolite` | raw | Honeywell UOP, Zeolyst (Ecovyst), Tosoh, Albemarle | catalyst composition patents; supplier product literature | catalyst makers | E2 | industry literature and patents |
| **Rare earth stabilisers of the zeolite** `dig:fcc:rare-earth-stabilisers` | raw | China Northern Rare Earth, Shenghe Resources, Lynas, MP Materials | USGS Mineral Commodity Summaries; China export quota announcements | catalyst makers | E2 | USGS, MOFCOM |
| **Lanthanum and cerium market** `dig:fcc:lanthanum-cerium-market` | factor | China Northern Rare Earth, Lynas | Argus and Fastmarkets rare earth assessments; USGS | catalyst and glass makers | E2 | price reporting agencies |
| **Rare earth separation capacity** `dig:fcc:separation-plants` | mechanism | Lynas (Malaysia, Mt Weld), MP Materials (Mountain Pass), Shenghe, Energy Fuels, Neo Performance | company commissioning updates; DOE and DPA awards | magnets, catalysts, defence | E2 | company releases, DOE |
| **Kaolin clay and alumina matrix** `dig:fcc:kaolin-and-alumina` | raw | Imerys, KaMin, BASF (Burgess), Alcoa, Rio Tinto, Chalco | USGS clay and bauxite statistics; supplier shipments | catalyst makers | E2 | USGS |
| **Silica sol binder** `dig:fcc:silica-sol` | raw | W.R. Grace, Ecolab (Nalco), Evonik | supplier product lines | catalyst makers | E3 | industry literature |
| **Hydrotreating catalysts** `dig:fcc:hydrotreating-catalysts` | raw | Albemarle, ART (Chevron), Honeywell UOP, Shell Catalysts and Technologies | catalyst maker disclosures; USGS molybdenum and cobalt | refiners | E2 | company filings, USGS |
| **Molybdenum supply** `dig:fcc:molybdenum-supply` | raw | Freeport-McMoRan, Molymet, Codelco, China Molybdenum | USGS molybdenum; LME and oxide prices | steel and catalyst makers | E2 | USGS |
| **Nickel and cobalt supply** `dig:fcc:nickel-cobalt-supply` | raw | Glencore, CMOC, Vale, Indonesian nickel producers | LME nickel; Fastmarkets cobalt; USGS | stainless, batteries, catalysts | E2 | USGS, LME |
| **FCC additives** `dig:fcc:additive-catalysts` | raw | Albemarle, W.R. Grace, BASF | supplier product literature; refiner air permits for additive use | refiners | E3 | industry literature |
| **Refining margin (crack spread)** `dig:fcc:refinery-margin` | outcome | independent refiners | futures crack spreads; EIA margins | refiners | E2 | futures and EIA |

Sub-items to fetch for every node above: composition, inputs, constraints, observables, substitutes, payers.

| Edge | Relation | Condition | Falsifier |
|---|---|---|---|
| `dig:fcc:gasoline-demand` -> `dig:fcc:refinery-runs` | drives | Gasoline demand sets refinery utilisation within the capacity constraint. | Runs fall while gasoline demand rises. |
| `dig:fcc:refinery-runs` -> `dig:fcc:fcc-unit-throughput` | drives | FCC units take the marginal barrel because they make the highest value barrel. | Hydrocracking takes the marginal throughput instead. |
| `dig:fcc:fcc-unit-throughput` -> `dig:fcc:catalyst-inventory` | requires | Catalyst deactivates and must be made up at a rate tied to throughput. | Catalyst life extends without throughput loss. |
| `dig:fcc:catalyst-inventory` -> `dig:fcc:rare-earth-stabilisers` | requires | Modern FCC catalysts carry rare earth exchange for stability. | Catalyst formulations move to rare earth free grades at scale. |
| `dig:fcc:rare-earth-stabilisers` -> `dig:fcc:separation-plants` | requires | La and Ce come from separated light rare earth oxide, from a handful of plants. | Unseparated or recycled sources cover demand. |
| `dig:fcc:catalyst-inventory` -> `dig:fcc:hydrotreating-catalysts` | co_moves | Cleaner fuels regulation raises hydrotreating intensity alongside cracking. | Fuel specifications loosen or hydrotreating intensity falls. |
| `dig:fcc:hydrotreating-catalysts` -> `dig:fcc:molybdenum-supply` | requires | Ni-Mo sulphide catalysts need byproduct molybdenum at scale. | Catalyst formulations substitute away from molybdenum. |
| `dig:fcc:refinery-margin` -> `dig:fcc:catalyst-inventory` | does_not_observe | The margin moves on product cracks and crude differentials, not on catalyst purchase economics. | Catalyst cost becomes a named driver of refiner results. |

### Transformer to the steel and copper inside it

`dig:power:transformer-core` · root `mechanism:capacity:transformer-bottleneck` · ceiling **testable** · nodes 8 · edges 6

**Why.** We already know transformers gate energization. The sub-parts decide who can actually ship them: core steel, windings, tap changers and bushings each come from a short list of plants.

**Chain.** `dig:power:lpt` -> `dig:power:goes` -> `dig:power:core-stacking` -> `dig:power:windings-copper` -> `dig:power:tap-changers` -> `dig:power:bushings` -> `dig:power:transformer-insulation`

**Greatest assumption.** Grain-oriented electrical steel is the binding sub-part for large transformer output, not windings, bushings or factory labour.

**Kill test.** Transformer output rises with flat GOES supply, or GOES capacity additions do not change lead times.

| Node | Layer | Players | Observables | Payer | Evidence | Source |
|---|---|---|---|---|---|---|
| **Large power transformer output** `dig:power:lpt` | mechanism | Hitachi Energy, Siemens Energy, GE Vernova, Hyosung HICO, Prolec GE | OEM capacity announcements; lead-time statements | utilities and developers | E2 | company releases, trade press |
| **Grain-oriented electrical steel** `dig:power:goes` | raw | Nippon Steel, JFE, POSCO, thyssenkrupp, Cleveland-Cliffs, Baowu | USITC imports; mill expansion announcements | transformer makers | E2 | USITC, mill releases |
| **Core laminations and stacking** `dig:power:core-stacking` | mechanism | POSCO, thyssenkrupp, specialist core shops | mill disclosures; line announcements | transformer makers | E3 | industry literature |
| **Copper and aluminium windings** `dig:power:windings-copper` | raw | Aurubis, Southwire, Elektrisola, Superior Essex | LME copper; wire mill capacity | transformer makers | E2 | LME, company releases |
| **On-load tap changers** `dig:power:tap-changers` | raw | Reinhausen (MR), Hitachi Energy, Huaming | supplier capacity notes | transformer makers | E2 | supplier releases |
| **Bushings** `dig:power:bushings` | raw | Hitachi Energy, NGK Insulators, Hubbell (Trench) | supplier capacity notes | transformer makers | E2 | supplier releases |
| **Insulating materials** `dig:power:transformer-insulation` | raw | Weidmann, Nynas, Dupont (Nomex) | plant capacities; bio-fluid adoption | transformer makers | E2 | supplier releases |
| **Transformer producer price index** `dig:power:transformer-ppo` | outcome | none named | BLS PPI transformers and power distribution equipment | utilities | E2 | BLS |

Sub-items to fetch for every node above: composition, inputs, constraints, observables, substitutes, payers.

| Edge | Relation | Condition | Falsifier |
|---|---|---|---|
| `dig:power:lpt` -> `dig:power:goes` | requires | Every large unit needs a core wound from GOES. | Amorphous or alternative cores take large-unit share. |
| `dig:power:goes` -> `dig:power:core-stacking` | feeds | Mill capacity is only useful with lamination capacity behind it. | Core shops run below capacity while steel is available. |
| `dig:power:lpt` -> `dig:power:windings-copper` | requires | Windings need enamelled copper or aluminium at volume. | Substitution or aluminium grades remove the copper constraint. |
| `dig:power:lpt` -> `dig:power:tap-changers` | requires | Load tap changing stays mechanical on most large units. | Solid-state or electronic regulation displaces mechanical changers. |
| `dig:power:lpt` -> `dig:power:bushings` | requires | Bushing supply is not substitutable across makes in the short run. | Universal bushing interchangeability holds. |
| `dig:power:transformer-ppo` -> `dig:power:goes` | reveals | When the core input binds, the producer price index for transformers rises relative to input steel prices. | Transformer prices fall while GOES prices rise. |

### Gas turbine to the superalloys and their byproducts

`dig:power:gas-turbine-superalloys` · root `mechanism:capacity:constraint` · ceiling **testable** · nodes 7 · edges 5

**Why.** Turbine slots gate new gas capacity. The slots are gated by castings, and the castings are gated by a set of metals most people cannot name: rhenium, hafnium, cobalt, and the nickel that goes into every blade.

**Chain.** `dig:turbine:heavy-duty` -> `dig:turbine:blades` -> `dig:turbine:superalloys` -> `dig:turbine:nickel` -> `dig:turbine:rhenium` -> `dig:turbine:hafnium` -> `dig:turbine:casters`

**Greatest assumption.** Single-crystal blade casting capacity, not assembly capacity, is the limiting step in turbine deliveries.

**Kill test.** Turbine output rises while blade casting capacity is flat, or casting expansion does not shorten slots.

| Node | Layer | Players | Observables | Payer | Evidence | Source |
|---|---|---|---|---|---|---|
| **Heavy-duty gas turbine deliveries** `dig:turbine:heavy-duty` | mechanism | GE Vernova, Siemens Energy, Mitsubishi Power, Ansaldo | OEM backlog and slot disclosures | utilities and IPPs | E2 | company filings |
| **Hot-section blades and vanes** `dig:turbine:blades` | mechanism | Howmet, Precision Castparts, Chromalloy, Doncasters | casting capacity announcements; OEM qualification lists | turbine OEMs | E2 | supplier releases |
| **Nickel superalloys** `dig:turbine:superalloys` | raw | Precision Castparts, Howmet, Carpenter, VDM (Acerinox) | alloy premium indices; mill shipments | casting and forge shops | E2 | industry literature |
| **Nickel** `dig:turbine:nickel` | raw | Vale, Glencore, Indonesian producers, Norilsk | LME nickel; USGS | alloy makers | E2 | LME, USGS |
| **Rhenium** `dig:turbine:rhenium` | raw | Molymet, KGHM, Freeport | USGS rhenium; oxide and metal prices | blade casters | E2 | USGS |
| **Hafnium** `dig:turbine:hafnium` | raw | Framatome, Westinghouse supply chain, Chinese producers | USGS zirconium and hafnium | blade coaters and nuclear | E2 | USGS |
| **Investment casting capacity** `dig:turbine:casters` | mechanism | Howmet, Precision Castparts, Doncasters, Zollern | capacity expansions; apprenticeship hiring | OEMs | E2 | supplier releases |

Sub-items to fetch for every node above: composition, inputs, constraints, observables, substitutes, payers.

| Edge | Relation | Condition | Falsifier |
|---|---|---|---|
| `dig:turbine:heavy-duty` -> `dig:turbine:blades` | requires | Every hot gas path needs a set of cast blades and vanes. | Rotor or other architectures bypass cast hot-section parts. |
| `dig:turbine:blades` -> `dig:turbine:casters` | requires | Blades come from vacuum investment casting with long qualification. | Additive or alternative processes qualify at scale. |
| `dig:turbine:blades` -> `dig:turbine:superalloys` | requires | Hot section alloys carry rhenium and hafnium additions. | Alloy formulations drop the rare additions without losing life. |
| `dig:turbine:superalloys` -> `dig:turbine:rhenium` | requires | Rhenium is a byproduct with inelastic supply, so blade demand and moly roasting set its price. | Recycling covers incremental demand. |
| `dig:turbine:superalloys` -> `dig:turbine:nickel` | requires | Nickel is the base and is price exposed to other demand. | Substitution away from nickel base is feasible. |

### HVDC to the valves, the cables and the ships

`dig:power:hvdc-converter` · root `mechanism:capacity:interconnection-bottleneck` · ceiling **testable** · nodes 6 · edges 4

**Why.** Moving power between regions needs converter stations and cables, and both have short supplier lists. The cables need ships, and the ships are booked years out.

**Chain.** `dig:hvdc:transfer` -> `dig:hvdc:converters` -> `dig:hvdc:valves` -> `dig:hvdc:cables` -> `dig:hvdc:cable-ships`

**Greatest assumption.** Cable and converter valve capacity, not right of way, is the constraint on interregional transfer additions.

**Kill test.** Transfer additions proceed while cable ship schedules slip, or cable makers hold spare capacity.

| Node | Layer | Players | Observables | Payer | Evidence | Source |
|---|---|---|---|---|---|---|
| **Interregional transfer capacity** `dig:hvdc:transfer` | mechanism | TSOs, developers | project award announcements; ENTSO-E and ISO plans | ratepayers and TSOs | E2 | TSO and ISO publications |
| **Converter stations** `dig:hvdc:converters` | mechanism | Hitachi Energy, Siemens Energy, GE Vernova, Mitsubishi Electric | order awards; factory expansions | TSOs | E2 | company releases |
| **Converter valves and power electronics** `dig:hvdc:valves` | raw | Hitachi Energy, Infineon, ABB semiconductors, Mitsubishi Electric, Dynex | fab capacity notes; semiconductor lead times | converter makers | E2 | supplier releases |
| **HVDC and submarine cables** `dig:hvdc:cables` | raw | Prysmian, Nexans, NKT, Sumitomo Electric, LS Cable | order backlogs; capacity expansions | TSOs and developers | E2 | company filings |
| **Cable laying vessels** `dig:hvdc:cable-ships` | raw | Prysmian, Nexans, NKT, Jan De Nul, Boskalis | newbuild orders; charter rates | cable makers and TSOs | E2 | shipping and trade press |
| **Cable conductor metals** `dig:hvdc:copper-aluminium` | raw | Aurubis, Southwire, Nexans | LME; cable maker input commentary | cable makers | E2 | LME, company filings |

Sub-items to fetch for every node above: composition, inputs, constraints, observables, substitutes, payers.

| Edge | Relation | Condition | Falsifier |
|---|---|---|---|
| `dig:hvdc:transfer` -> `dig:hvdc:converters` | requires | Every link needs two converter terminals. | Alternative conversion technology changes the supplier base. |
| `dig:hvdc:converters` -> `dig:hvdc:valves` | requires | Valves and their semiconductors are on the critical path. | Valve inventories cover project schedules. |
| `dig:hvdc:transfer` -> `dig:hvdc:cables` | requires | Long links need cable from a short supplier list. | Overhead or alternative routes dominate. |
| `dig:hvdc:cables` -> `dig:hvdc:cable-ships` | requires | Installation capacity is as scarce as the cable itself. | Ships are readily available at short notice. |

### Storage to the cells and the materials inside them

`dig:power:bess-cells` · root `mechanism:capacity:constraint` · ceiling **testable** · nodes 7 · edges 4

**Why.** Battery storage is now the flexible capacity behind new load. The chemistry chain is where the cost curves and the export controls live.

**Chain.** `dig:bess:systems` -> `dig:bess:cells` -> `dig:bess:lfp` -> `dig:bess:lithium` -> `dig:bess:graphite` -> `dig:bess:electrolyte`

**Greatest assumption.** LFP chemistry dominates stationary storage, so lithium, iron phosphate and graphite are the binding materials, not nickel or cobalt.

**Kill test.** Stationary storage moves back to nickel chemistries at scale, or sodium ion takes meaningful share.

| Node | Layer | Players | Observables | Payer | Evidence | Source |
|---|---|---|---|---|---|---|
| **Grid scale storage systems** `dig:bess:systems` | mechanism | Tesla, Fluence, Sungrow, Nidec, Chinese integrators | deployment statistics; integrator backlog | utilities and developers | E2 | EIA, company filings |
| **Storage cells** `dig:bess:cells` | raw | CATL, BYD, EVE Energy, LG Energy Solution, Samsung SDI | cell price indices; export data | integrators | E2 | BNEF, trade data |
| **LFP cathode chemistry** `dig:bess:lfp` | raw | CATL, EVE, Hunan Yuneng, LFP licence holders | cathode shipment data; patent and licence news | cell makers | E2 | industry data |
| **Lithium** `dig:bess:lithium` | raw | Albemarle, SQM, Pilbara, Ganfeng, CATL (Jianxiawo) | Fastmarkets lithium; spodumene shipments | cell makers | E2 | Fastmarkets, USGS |
| **Graphite anode** `dig:bess:graphite` | raw | Chinese anode makers, Syrah Resources, Novonix, Elkem | China export licence data; synthetic graphite prices | cell makers | E2 | trade data, USGS |
| **Electrolyte and separator** `dig:bess:electrolyte` | raw | Tinci, Capchem, Asahi Kasei, Toray, SKIET | chemical prices; plant expansions | cell makers | E2 | industry data |
| **Copper and aluminium foil** `dig:bess:copper-foil` | raw | Wason, Nuode, Furukawa, Lotte | foil price premia | cell makers | E2 | industry data |

Sub-items to fetch for every node above: composition, inputs, constraints, observables, substitutes, payers.

| Edge | Relation | Condition | Falsifier |
|---|---|---|---|
| `dig:bess:systems` -> `dig:bess:cells` | requires | Systems scale with cell supply and cost. | Integrator value moves entirely to power electronics. |
| `dig:bess:cells` -> `dig:bess:lfp` | requires | LFP wins on cost and cycle life for stationary duty. | Nickel chemistries regain stationary share. |
| `dig:bess:lfp` -> `dig:bess:lithium` | requires | Every LFP cell carries lithium, so lithium price moves cell cost. | Sodium ion or alternatives remove lithium from the cost stack. |
| `dig:bess:cells` -> `dig:bess:graphite` | requires | Anodes are graphite, and processing is concentrated in China. | Silicon or hard carbon anodes scale at stationary cost points. |

### Power electronics to silicon carbide and its furnace inputs

`dig:power:sic-semiconductors` · root `mechanism:capacity:constraint` · ceiling **testable** · nodes 5 · edges 4

**Why.** Every inverter, converter and charger runs through power semiconductors. The shift from silicon to silicon carbide moves the bottleneck to crystal growth and its raw inputs.

**Chain.** `dig:sic:power-devices` -> `dig:sic:wafers` -> `dig:sic:crystal-growth` -> `dig:sic:quartz` -> `dig:sic:graphite`

**Greatest assumption.** SiC adoption in grid and data center power conversion scales fast enough to matter for the upstream materials.

**Kill test.** Silicon IGBTs keep the cost advantage in the relevant power classes.

| Node | Layer | Players | Observables | Payer | Evidence | Source |
|---|---|---|---|---|---|---|
| **Power semiconductor devices** `dig:sic:power-devices` | raw | Infineon, Onsemi, STMicroelectronics, Mitsubishi Electric, Wolfspeed | semi lead times; fab utilisation | inverter and converter makers | E2 | company filings |
| **SiC substrates and epitaxy** `dig:sic:wafers` | raw | Wolfspeed, Coherent, SK Siltron, Resonac | substrate capacity announcements; yield commentary | device makers | E2 | company releases |
| **Crystal growth furnaces** `dig:sic:crystal-growth` | mechanism | Wolfspeed, AIXTRON, LPE, Chinese furnace makers | furnace order data; expansion projects | substrate makers | E2 | industry press |
| **High purity quartz** `dig:sic:quartz` | raw | Sibelco (Spruce Pine), TQC, Mitsubishi Chemical | mine output; supply agreements | furnace and wafer makers | E2 | company releases, USGS |
| **High purity graphite** `dig:sic:graphite` | raw | SGL Carbon, Mersen, Tokai Carbon, Chinese producers | graphite electrode prices; China export policy | furnace makers | E2 | industry data |

Sub-items to fetch for every node above: composition, inputs, constraints, observables, substitutes, payers.

| Edge | Relation | Condition | Falsifier |
|---|---|---|---|
| `dig:sic:power-devices` -> `dig:sic:wafers` | requires | SiC devices need substrates with qualified yield. | Alternative wide bandgap routes dominate. |
| `dig:sic:wafers` -> `dig:sic:crystal-growth` | requires | Boule growth capacity and yield set substrate supply. | Substrate supply outruns device demand persistently. |
| `dig:sic:crystal-growth` -> `dig:sic:quartz` | requires | High purity quartz is essential and concentrated. | Synthetic or alternative crucible materials qualify. |
| `dig:sic:crystal-growth` -> `dig:sic:graphite` | requires | Furnace hot zones need high purity graphite. | Alternative hot zone materials qualify. |

### Motors and generators to the magnets and the export controls

`dig:power:rare-earth-magnets` · root `asset:equity:supplier-basket` · ceiling **testable** · nodes 6 · edges 4

**Why.** Direct drive wind generators and industrial motors run on rare earth magnets, and the heavy rare earths that make them work at temperature come from a supply chain one country can throttle.

**Chain.** `dig:ree:magnets` -> `dig:ree:alloys` -> `dig:ree:heavy-rare-earths` -> `dig:ree:separation` -> `dig:ree:export-controls`

**Greatest assumption.** Heavy rare earth supply remains the chokepoint, so magnet makers' margins and defence buying respond to export policy before prices fully adjust.

**Kill test.** Magnet makers substitute away from dysprosium and terbium, or non-Chinese separation capacity removes the chokepoint.

| Node | Layer | Players | Observables | Payer | Evidence | Source |
|---|---|---|---|---|---|---|
| **NdFeB magnets** `dig:ree:magnets` | raw | JL Mag, Zhongke Sanhuan, Ningbo Yunsheng, Shin-Etsu, Proterial, VAC | magnet shipment data; export quotas | motor, wind and auto OEMs | E2 | industry data |
| **Magnet alloys and strip casting** `dig:ree:alloys` | mechanism | JL Mag, Shin-Etsu, Proterial, Neo Performance | capacity announcements | magnet makers | E3 | company releases |
| **Dysprosium and terbium** `dig:ree:heavy-rare-earths` | raw | Myanmar and Chinese ion adsorption producers, Lynas, MP Materials | USGS; China quota announcements; prices | magnet makers and defence | E2 | USGS, MOFCOM |
| **Rare earth separation and refining** `dig:ree:separation` | mechanism | China Northern Rare Earth, China Rare Earth Group, Shenghe, Lynas, Energy Fuels | plant commissioning; DOE and DPA awards | magnet, catalyst and defence buyers | E2 | company releases, DOE |
| **Export control regime** `dig:ree:export-controls` | event | MOFCOM, US and allied policy bodies | MOFCOM announcements; Federal Register actions | importers | E2 | official gazettes |
| **Defence and strategic stockpile buying** `dig:ree:defence-buying` | entity | MP Materials, Lynas, neo, DoD, DPA | contract awards; price floor terms |  governments | E2 | award announcements |

Sub-items to fetch for every node above: composition, inputs, constraints, observables, substitutes, payers.

| Edge | Relation | Condition | Falsifier |
|---|---|---|---|
| `dig:ree:magnets` -> `dig:ree:heavy-rare-earths` | requires | High temperature grades need Dy and Tb additions. | Grain boundary diffusion or new grades remove heavy rare earths. |
| `dig:ree:heavy-rare-earths` -> `dig:ree:separation` | requires | Heavy rare earths need separation capacity that barely exists outside China. | New non-Chinese separation lines cover demand. |
| `dig:ree:separation` -> `dig:ree:export-controls` | gated_by | Policy can throttle what the separation base ships. | Controls are not enforced in practice. |
| `dig:ree:defence-buying` -> `dig:ree:separation` | funds | Government support changes the economics of non-Chinese capacity. | Private demand alone carries the new capacity. |

### Data center cooling to refrigerants, chemicals and pumps

`dig:power:cooling-water` · root `mechanism:capacity:cooling-bottleneck` · ceiling **testable** · nodes 6 · edges 4

**Why.** Cooling is the quiet constraint: refrigerants face regulation, water treatment faces discharge rules, and the equipment list is short.

**Chain.** `dig:cool:load` -> `dig:cool:chillers` -> `dig:cool:refrigerants` -> `dig:cool:water-treatment` -> `dig:cool:liquid-cooling`

**Greatest assumption.** The refrigerant transition and water rules bind before power availability does in the affected regions.

**Kill test.** Sites and equipment proceed on old refrigerants and unrestricted water without delay or cost step change.

| Node | Layer | Players | Observables | Payer | Evidence | Source |
|---|---|---|---|---|---|---|
| **Data center cooling load** `dig:cool:load` | mechanism | operators and colocation | rack density disclosures; PUE reports | operators | E2 | operator reports |
| **Chillers and air handlers** `dig:cool:chillers` | raw | Trane Technologies, Carrier, Daikin, Vertiv, Stulz, nVent | order books; equipment lead times | operators | E2 | company filings |
| **Refrigerants** `dig:cool:refrigerants` | raw | Chemours, Honeywell, Daikin, Arkema | F-gas regulation dockets; refrigerant prices | equipment owners | E2 | regulatory dockets |
| **Water treatment chemicals** `dig:cool:water-treatment` | raw | Ecolab, Solenis, Kurita, Veolia | company volumes; discharge permits | operators | E2 | company filings |
| **Direct liquid cooling** `dig:cool:liquid-cooling` | mechanism | Vertiv, nVent, Boyd, 3M (exiting PFAS), Chemours | server roadmaps; fluid qualifications | operators and chip vendors | E2 | company releases |
| **Pumps and heat exchangers** `dig:cool:pumps` | raw | Grundfos, Xylem, Alfa Laval, Danfoss | order books | operators | E2 | company filings |

Sub-items to fetch for every node above: composition, inputs, constraints, observables, substitutes, payers.

| Edge | Relation | Condition | Falsifier |
|---|---|---|---|
| `dig:cool:load` -> `dig:cool:chillers` | requires | Density growth forces more mechanical cooling. | Air cooling scales with density. |
| `dig:cool:chillers` -> `dig:cool:refrigerants` | requires | Every vapour compression plant needs a working fluid. | Alternative cooling cycles bypass refrigerants. |
| `dig:cool:load` -> `dig:cool:water-treatment` | requires | Evaporative cooling needs chemical treatment and water. | Closed loop designs remove the water chemistry load. |
| `dig:cool:load` -> `dig:cool:liquid-cooling` | drives | High density racks push liquid cooling into the mainstream. | Air cooling holds through the density curve. |

### Switchgear to the gas inside it and the ceramic around it

`dig:power:switchgear-sf6` · root `mechanism:capacity:transformer-bottleneck` · ceiling **testable** · nodes 5 · edges 4

**Why.** Breakers and switchgear sit on the same critical path as transformers, and one of their inputs, SF6, is a regulated greenhouse gas being phased down.

**Chain.** `dig:switch:gear` -> `dig:switch:sf6` -> `dig:switch:vacuum` -> `dig:switch:insulators`

**Greatest assumption.** SF6 regulation changes equipment specifications and costs enough to matter for project schedules.

**Kill test.** Alternative insulation gases replace SF6 without cost or qualification delay.

| Node | Layer | Players | Observables | Payer | Evidence | Source |
|---|---|---|---|---|---|---|
| **Switchgear and breakers** `dig:switch:gear` | raw | Eaton, Schneider Electric, Siemens Energy, Hitachi Energy, ABB, Hubbell | order backlogs; lead times | utilities and developers | E2 | company filings |
| **SF6 insulating gas** `dig:switch:sf6` | raw | Linde, Air Products, Solvay (fluorine chain) | fluorite and HF prices; EU F-gas rules; EPA rules | equipment makers | E2 | regulatory dockets, USGS fluorspar |
| **Vacuum interrupters** `dig:switch:vacuum` | raw | Eaton, Hitachi Energy, Siemens Energy, Mitsubishi Electric | capacity announcements | switchgear makers | E3 | company releases |
| **Insulators and bushings** `dig:switch:insulators` | raw | NGK Insulators, Hubbell, Lapp, Sediver | clay and feldspar statistics; plant capacities | utilities | E2 | USGS, company releases |
| **Fluorspar and fluorine chain** `dig:switch:fluorite` | raw | China and Mexico producers, Solvay, Mexichem (Orbia) | USGS fluorspar; export policy | chemical makers | E2 | USGS |

Sub-items to fetch for every node above: composition, inputs, constraints, observables, substitutes, payers.

| Edge | Relation | Condition | Falsifier |
|---|---|---|---|
| `dig:switch:gear` -> `dig:switch:sf6` | requires | SF6 remains the default insulation for high voltage gear. | Alternative gases qualify at scale. |
| `dig:switch:gear` -> `dig:switch:vacuum` | requires | Vacuum interruption is standard below the highest voltages. | Solid state switching displaces vacuum in the medium voltage class. |
| `dig:switch:gear` -> `dig:switch:insulators` | requires | Outdoor equipment needs porcelain or composite insulation. | Enclosed designs remove the insulator requirement. |
| `dig:switch:sf6` -> `dig:switch:fluorite` | requires | Fluorine chemistry starts at fluorspar. | Recycled or synthetic fluorine covers demand. |

### Data transmission to fiber, dopants and rare gases

`dig:data:fiber-optics` · root `entity:datacenter:site` · ceiling **watch** · nodes 6 · edges 4

**Why.** Every model run and every byte to a data center crosses glass. The fiber chain carries two supply points that are almost invisible: high purity silica and the germanium and helium behind the dopants.

**Chain.** `dig:fiber:interconnect` -> `dig:fiber:cable` -> `dig:fiber:preform` -> `dig:fiber:germanium` -> `dig:fiber:helium`

**Greatest assumption.** Interconnect demand growth reaches fiber supply constraints within the observation window.

**Kill test.** Fiber capacity keeps ahead of demand with stable lead times and prices.

| Node | Layer | Players | Observables | Payer | Evidence | Source |
|---|---|---|---|---|---|---|
| **Data center interconnect** `dig:fiber:interconnect` | mechanism | hyperscalers, carriers, Zayo, Lumen | carrier capex; route announcements | hyperscalers | E2 | company filings |
| **Optical fiber and cable** `dig:fiber:cable` | raw | Corning, YOFC, Prysmian, Sumitomo Electric, OFS (Furukawa), Sterlite | fiber shipment data; capacity announcements | carriers and hyperscalers | E2 | company filings |
| **Silica preform** `dig:fiber:preform` | raw | Corning, Shin-Etsu, Sumitomo Electric, Heraeus | preform capacity | fiber makers | E3 | industry literature |
| **Germanium dopant** `dig:fiber:germanium` | raw | Umicore, Yunnan Chihong, Teck, Nyrstar | USGS germanium; China export controls | fiber and infrared optics makers | E2 | USGS, MOFCOM |
| **Helium and rare gases** `dig:fiber:helium` | raw | Linde, Air Products, Air Liquide, ExxonMobil | USGS helium; auction results | fiber and semiconductor makers | E2 | USGS |
| **Submarine cables** `dig:fiber:submarine` | raw | SubCom, ASN (Alcatel), NEC, HMN Tech, Prysmian | system awards; route consortia | consortia and hyperscalers | E2 | trade press |

Sub-items to fetch for every node above: composition, inputs, constraints, observables, substitutes, payers.

| Edge | Relation | Condition | Falsifier |
|---|---|---|---|
| `dig:fiber:interconnect` -> `dig:fiber:cable` | requires | Capacity grows through more fiber pairs. | Coherent optics remove the need for more fiber. |
| `dig:fiber:cable` -> `dig:fiber:preform` | requires | Fiber output is set by preform capacity. | Preform output runs ahead of draw capacity persistently. |
| `dig:fiber:preform` -> `dig:fiber:germanium` | requires | Most fiber designs use germanium doping. | Germanium free fiber designs dominate. |
| `dig:fiber:cable` -> `dig:fiber:helium` | requires | Drawing and cooling need helium and rare gases. | Gas recovery removes the dependence. |

### The buildout to the crews that install it

`dig:power:labor-pipeline` · root `mechanism:capacity:labor-bottleneck` · ceiling **watch** · nodes 5 · edges 4

**Why.** Equipment arrives at a site and waits for crews. The pipeline behind the crews is apprenticeships, union halls, licensing boards and community colleges, and it moves on a decade clock.

**Chain.** `dig:labor:crews` -> `dig:labor:apprenticeship` -> `dig:labor:unions` -> `dig:labor:licensing` -> `dig:labor:wages`

**Greatest assumption.** Crew scarcity, not equipment, is binding in the specific regions of the buildout.

**Kill test.** Projects run to schedule with available crews while equipment is late, which would flip the ordering.

| Node | Layer | Players | Observables | Payer | Evidence | Source |
|---|---|---|---|---|---|---|
| **Certified electrical and line crews** `dig:labor:crews` | mechanism | NECA contractors, Quanta Services, MYR Group, Primoris | contractor backlogs; labour availability commentary | developers and utilities | E2 | company filings |
| **Apprenticeship pipeline** `dig:labor:apprenticeship` | mechanism | IBEW and NECA JATCs, ABC programs, community colleges | apprenticeship registrations; DOL data | contractors and members | E2 | DOL apprenticeship data |
| **Union halls and referral** `dig:labor:unions` | entity | IBEW locals | referral volumes; local agreements | contractors | E2 | public labour agreements |
| **Licensing and reciprocity** `dig:labor:licensing` | rule | state boards | licensing rules; reciprocity agreements | workers and contractors | E2 | state boards |
| **Wage premia and per diem** `dig:labor:wages` | factor | none named | BLS OES; union wage schedules; per diem practice | developers | E2 | BLS |

Sub-items to fetch for every node above: composition, inputs, constraints, observables, substitutes, payers.

| Edge | Relation | Condition | Falsifier |
|---|---|---|---|
| `dig:labor:crews` -> `dig:labor:apprenticeship` | requires | Crews come from a pipeline that cannot speed up quickly. | Alternative training or immigration fills the gap fast. |
| `dig:labor:crews` -> `dig:labor:unions` | requires | Referral through halls is the allocation mechanism on most large sites. | Open shop contractors supply most crews. |
| `dig:labor:crews` -> `dig:labor:licensing` | gated_by | Licence reciprocity limits how fast crews move to where the work is. | Reciprocity is broad and mobility is free. |
| `dig:labor:wages` -> `dig:labor:crews` | reveals | When crews bind, wages and per diem rise ahead of schedule slips. | Wage premia stay flat through the buildout. |

### Copper from mine to the winding and the cable

`dig:material:copper-stack` · root `factor:commodity:copper` · ceiling **testable** · nodes 6 · edges 4

**Why.** Grid buildout, data centers and electrification all draw the same metal through a supply chain whose first link, mine supply, moves on a decade clock and whose middle link, smelting, is concentrated.

**Chain.** `dig:copper:demand` -> `dig:copper:concentrate` -> `dig:copper:smelters` -> `dig:copper:scrap` -> `dig:copper:moly-byproduct`

**Greatest assumption.** Mine and smelter supply cannot respond to the buildout within the observation window, so the price response comes from the demand side.

**Kill test.** Mine expansions and scrap respond fast enough to keep markets balanced through the buildout.

| Node | Layer | Players | Observables | Payer | Evidence | Source |
|---|---|---|---|---|---|---|
| **Grid and data center copper demand** `dig:copper:demand` | factor | none named | ICSG balances; cable maker commentary | utilities and developers | E2 | ICSG |
| **Copper concentrate supply** `dig:copper:concentrate` | mechanism | Freeport-McMoRan, BHP, Codelco, Antofagasta, Glencore, Southern Copper | mine guidance; TC/RC benchmark | smelters | E2 | company filings, Fastmarkets |
| **Smelting and refining** `dig:copper:smelters` | mechanism | Jiangxi Copper, Tongling, Aurubis, Korea Zinc | treatment charges; smelter outages | fabricators | E2 | Fastmarkets |
| **Scrap and secondary supply** `dig:copper:scrap` | mechanism | recyclers and traders | scrap spreads; China import policy | smelters | E2 | trade data |
| **Molybdenum byproduct** `dig:copper:moly-byproduct` | raw | Freeport-McMoRan, Molymet, Codelco | USGS molybdenum; roaster capacity | steel and catalyst makers | E2 | USGS |
| **Smelter power economics** `dig:copper:power-cost` | mechanism | none named | TC/RC benchmark; smelter curtailments | miners and smelters | E2 | Fastmarkets |

Sub-items to fetch for every node above: composition, inputs, constraints, observables, substitutes, payers.

| Edge | Relation | Condition | Falsifier |
|---|---|---|---|
| `dig:copper:demand` -> `dig:copper:concentrate` | requires | Demand growth meets a mine supply that moves on a decade clock. | Mine supply expansion keeps pace. |
| `dig:copper:concentrate` -> `dig:copper:smelters` | requires | Concentrate must pass through smelters whose capacity is concentrated. | Alternative refining routes or locations absorb the flow. |
| `dig:copper:demand` -> `dig:copper:scrap` | absorbs | Scrap supply flexes with price and cools the market. | Scrap supply is inelastic through the buildout. |
| `dig:copper:concentrate` -> `dig:copper:moly-byproduct` | co_produces | Molybdenum comes from the same porphyry systems, tying catalyst input to copper supply. | Moly supply decouples from copper mining. |

### Firm power to the fuel, the enrichment and the cladding

`dig:power:nuclear-fuel` · root `mechanism:capacity:constraint` · ceiling **testable** · nodes 6 · edges 5

**Why.** The data center complex is contracting firm power, and some of it is nuclear. The fuel chain behind it has one chokepoint most people have never heard of: HALEU enrichment outside Russia.

**Chain.** `dig:nuc:firm-power` -> `dig:nuc:haleu` -> `dig:nuc:enrichment` -> `dig:nuc:conversion` -> `dig:nuc:uranium` -> `dig:nuc:cladding`

**Greatest assumption.** New nuclear and uprates proceed on the announced schedule, so fuel chain capacity becomes the binding constraint before the reactor does.

**Kill test.** Reactor projects slip years while fuel chain capacity expands ahead of demand.

| Node | Layer | Players | Observables | Payer | Evidence | Source |
|---|---|---|---|---|---|---|
| **Firm nuclear capacity for compute** `dig:nuc:firm-power` | mechanism | Constellation, Vistra, Talen, Oklo, NuScale, GE Hitachi, X-energy | PPA announcements; NRC licensing dockets | hyperscalers and utilities | E2 | company releases, NRC |
| **HALEU fuel** `dig:nuc:haleu` | raw | Centrus, Urenco, Orano, Tenex (Russia) | DOE HALEU program milestones; Centrus production updates | reactor developers and DOE | E2 | DOE, company releases |
| **Enrichment capacity** `dig:nuc:enrichment` | mechanism | Urenco, Orano, Centrus, Rosatom | SWU capacity announcements; SWU prices | utilities | E2 | company and agency data |
| **Conversion and deconversion** `dig:nuc:conversion` | mechanism | ConverDyn, Cameco, Framotome, Orano | conversion prices; plant restarts | utilities | E2 | trade press |
| **Uranium mining** `dig:nuc:uranium` | raw | Cameco, Kazatomprom, Uranium Energy Corp, enCore, Paladin | spot and term prices; production guidance | utilities | E2 | trade press, company filings |
| **Zirconium cladding and hafnium split** `dig:nuc:cladding` | raw | Westinghouse, Framatome, Chinese producers | USGS zirconium; plant capacity | fuel fabricators | E2 | USGS |

Sub-items to fetch for every node above: composition, inputs, constraints, observables, substitutes, payers.

| Edge | Relation | Condition | Falsifier |
|---|---|---|---|
| `dig:nuc:firm-power` -> `dig:nuc:haleu` | requires | Advanced reactors need HALEU before first criticality. | Reactors run on LEU or alternative fuels. |
| `dig:nuc:haleu` -> `dig:nuc:enrichment` | requires | HALEU needs enrichment capacity that exists in few places. | Alternative enrichment routes scale. |
| `dig:nuc:enrichment` -> `dig:nuc:conversion` | requires | Enrichment needs UF6, so conversion is upstream of it. | Conversion capacity is ample through the period. |
| `dig:nuc:conversion` -> `dig:nuc:uranium` | requires | Conversion needs mined and milled uranium. | Secondary supply covers demand. |
| `dig:nuc:cladding` -> `dig:nuc:firm-power` | supplies | Fuel fabrication needs cladding, tying the zirconium chain to reactor operation. | Alternative cladding materials qualify. |

### Load growth to the rate base and the rate case

`dig:grid:utility-economics` · root `outcome:firm:capex-level` · ceiling **testable** · nodes 9 · edges 8

**Why.** Data center load growth lands on regulated utilities, and the path from a load forecast to shareholder return runs through a rate case. The analogue utilities followed the same path after their own buildout bust.

**Chain.** `dig:grid:load-growth` -> `dig:grid:capex-plan` -> `dig:grid:rate-case` -> `dig:grid:allowed-return` -> `dig:grid:special-contracts`

**Greatest assumption.** The regulatory compact converts demand-driven capex into rate base at a fair return without political interruption.

**Kill test.** Rate cases disallow demand-driven capex or slow recovery while capex rises.

| Node | Layer | Players | Observables | Payer | Evidence | Source |
|---|---|---|---|---|---|---|
| **Load growth forecast** `dig:grid:load-growth` | mechanism | utilities, consultants | EIA-930 demand; utility IRPs | ratepayers | E2 | EIA, utility filings |
| **Utility capital plan** `dig:grid:capex-plan` | mechanism | utilities | 10-K and 10-Q capex guidance; EIA-861; FERC Form 1 | ratepayers | E2 | company filings, FERC |
| **Rate case** `dig:grid:rate-case` | event | state PUCs, intervenors, utilities | state commission dockets; testimony; orders | ratepayers | E2 | state commission dockets |
| **Allowed return on equity** `dig:grid:allowed-return` | outcome | state PUCs | commission orders; ROE comparisons | shareholders | E2 | commission orders |
| **Large load special contracts** `dig:grid:special-contracts` | contract | utilities, hyperscalers, commissions | special contract filings; commission orders | ratepayers and the new load | E2 | state dockets |
| **Transmission planning and cost allocation** `dig:grid:transmission-planning` | mechanism | RTOs, FERC, utilities | FERC filings; RTO planning reports; Order 1000 records | ratepayers | E2 | FERC, RTO documents |
| **Capacity market** `dig:grid:capacity-auction` | mechanism | RTOs, generators, load | ISO capacity auction clearing prices | load | E2 | ISO results |
| **Ratepayer politics** `dig:grid:ratepayer-politics` | entity | state legislators, advocates, commissions | bill impact testimony; legislative activity | utilities via allowed returns | E3 | state dockets |
| **Utility equity issuance and financing** `dig:grid:equity-financing` | mechanism | utilities, investors | equity issuance records; credit ratings | shareholders | E2 | company filings |

Sub-items to fetch for every node above: composition, inputs, constraints, observables, substitutes, payers.

| Edge | Relation | Condition | Falsifier |
|---|---|---|---|
| `dig:grid:load-growth` -> `dig:grid:capex-plan` | drives | Load forecasts set the capex that regulators are asked to approve. | Capex plans shrink while load forecasts rise. |
| `dig:grid:capex-plan` -> `dig:grid:rate-case` | requires | Capital recovery runs through the rate case process. | Costs are recovered without a filing. |
| `dig:grid:rate-case` -> `dig:grid:allowed-return` | sets | The case sets the authorised return on the rate base. | Returns are set by formula without a case. |
| `dig:grid:load-growth` -> `dig:grid:special-contracts` | requires | New large load needs a cost responsibility arrangement. | Standard tariffs absorb the cost. |
| `dig:grid:special-contracts` -> `dig:grid:ratepayer-politics` | influences | Contract design decides who pays and therefore how loud the politics gets. | Cost allocation is never contested. |
| `dig:grid:capex-plan` -> `dig:grid:equity-financing` | requires | Capex growth needs funding at the authorised capital structure. | Cash flow funds capex with no external finance. |
| `dig:grid:transmission-planning` -> `dig:grid:capex-plan` | feeds | Approved transmission projects enter the capital plan. | Projects proceed outside the plan. |
| `dig:grid:capacity-auction` -> `dig:grid:allowed-return` | complements | Capacity revenue supports the merchant side of the fleet. | Energy and contracts cover all fixed costs. |

### The compute index as a phase marker and a feed

`dig:cloud:compute-index` · root `feature:compute:rental-price` · ceiling **testable** · nodes 9 · edges 7

**Why.** We hold 566 monthly observations across 18 compute families, and our own measures found ten independent markets and a provider policy price, not a clearing price. That makes the index a read on provider inventory state, which is exactly what phases turn on.

**Chain.** `dig:compute:families` -> `dig:compute:rental-change` -> `dig:compute:inventory-state` -> `dig:compute:provider-capex` -> `dig:compute:power-commitment` -> `dig:compute:inference-cost`

**Greatest assumption.** Family level compute price changes lead provider capex and power commitments rather than merely reflecting demand that is already visible elsewhere.

**Kill test.** No measurable relation between family level price changes and later provider capex or power commitments.

| Node | Layer | Players | Observables | Payer | Evidence | Source |
|---|---|---|---|---|---|---|
| **Compute families** `dig:compute:families` | factor | providers | results/compute-price-monthly.csv; provider price pages | buyers of compute | E1 | results/compute-price-monthly.csv; truth T8 |
| **Family rental price change** `dig:compute:rental-change` | factor | providers | results/compute-price-monthly.csv | providers and buyers | E1 | results/compute-price-monthly.csv |
| **Provider inventory state** `dig:compute:inventory-state` | mechanism | providers | availability zones; waiting lists; price levels | providers | E2 | provider behaviour; truth T9 |
| **Provider capital spending** `dig:compute:provider-capex` | mechanism | hyperscalers, neoclouds | 10-Q capex; guidance; supplier backlogs | shareholders | E2 | company filings |
| **Power commitment** `dig:compute:power-commitment` | mechanism | operators, utilities, IPPs | PPA announcements; interconnection requests; load forecasts | ratepayers and operators | E2 | company and utility filings |
| **Inference cost per token** `dig:compute:inference-cost` | factor | model providers, operators | provider pricing pages; model releases | buyers of inference | E2 | public pricing |
| **Token and workload demand** `dig:compute:token-demand` | factor | enterprises, consumers | API usage disclosures; cloud revenue; model release cadence | end users | E3 | company disclosures |
| **Depreciation schedule** `dig:compute:depreciation` | accounting | hyperscalers, neoclouds | 10-K useful life disclosures | shareholders | E2 | company filings |
| **Rental volatility** `dig:compute:rental-volatility` | factor | providers | results/compute-price-monthly.csv | providers | E1 | results/compute-price-monthly.csv |

Sub-items to fetch for every node above: composition, inputs, constraints, observables, substitutes, payers.

| Edge | Relation | Condition | Falsifier |
|---|---|---|---|
| `dig:compute:families` -> `dig:compute:rental-change` | measures | Family level prices are the finest observable we hold. | Family prices are unavailable or unreliable. |
| `dig:compute:rental-change` -> `dig:compute:inventory-state` | indicates | Price changes are how the provider expresses inventory conditions. | Prices are contractual and do not move with inventory. |
| `dig:compute:inventory-state` -> `dig:compute:provider-capex` | drives | Scarcity invites capex and surplus defers it. | Capex is fixed by strategy regardless of inventory. |
| `dig:compute:provider-capex` -> `dig:compute:power-commitment` | requires | New compute needs firm power and grid capacity. | Compute growth decouples from power through efficiency. |
| `dig:compute:inference-cost` -> `dig:compute:token-demand` | drives | Falling unit cost has expanded demand, the Jevons pattern of this cycle. | Demand saturates despite falling cost. |
| `dig:compute:depreciation` -> `dig:compute:provider-capex` | gates | Short useful lives turn capex into a recurring cash cost, changing the build economics. | Accelerator life extends far beyond current assumptions. |
| `dig:compute:rental-volatility` -> `dig:compute:inventory-state` | reveals | Volatility rises when inventory is stressed. | Volatility stays flat through inventory cycles. |

### Energy providers, the payer side of the buildout

`dig:power:energy-providers` · root `asset:equity:utility-basket` · ceiling **testable** · nodes 7 · edges 5

**Why.** The buildout pays a specific set of providers: regulated utilities, merchant generators, nuclear operators and transmission owners. Each has a different mechanism and a different regime response.

**Chain.** `dig:providers:load-growth` -> `dig:providers:firm-capacity` -> `dig:providers:ppa-price` -> `dig:providers:provider-margin` -> `dig:providers:credit`

**Greatest assumption.** Firm capacity and grid services remain the scarce product through the buildout, so providers with existing assets keep pricing power.

**Kill test.** Storage, demand response and self generation remove the scarcity before new supply arrives.

| Node | Layer | Players | Observables | Payer | Evidence | Source |
|---|---|---|---|---|---|---|
| **Local load growth** `dig:providers:load-growth` | mechanism | utilities, IPPs | EIA-930; IRPs; interconnection requests | ratepayers | E2 | EIA, utility filings |
| **Firm capacity** `dig:providers:firm-capacity` | mechanism | nuclear, gas, storage, imports | ISO auctions; PPA volumes | operators | E2 | ISO and company data |
| **PPA and capacity price** `dig:providers:ppa-price` | factor | utilities, hyperscalers, IPPs | PPA announcements; capacity clearing prices | ratepayers and operators | E2 | company announcements |
| **Provider margin** `dig:providers:provider-margin` | accounting | utilities, IPPs, nuclear operators | 10-K segment results | shareholders | E2 | company filings |
| **Provider credit** `dig:providers:credit` | asset | utilities, IPPs | credit ratings; bond spreads | shareholders | E2 | rating agencies |
| **Transmission owner** `dig:providers:transmission-owner` | entity | transmission utilities, ITCs | FERC Form 1; rate filings | ratepayers | E2 | FERC filings |
| **Retail and large load contracts** `dig:providers:retail-load` | contract | utilities, load | special contracts; tariff filings | ratepayers | E2 | state dockets |

Sub-items to fetch for every node above: composition, inputs, constraints, observables, substitutes, payers.

| Edge | Relation | Condition | Falsifier |
|---|---|---|---|
| `dig:providers:load-growth` -> `dig:providers:firm-capacity` | requires | Load growth raises the firm capacity requirement. | Load growth is met by interruptible demand. |
| `dig:providers:firm-capacity` -> `dig:providers:ppa-price` | prices | Scarcity of firm capacity sets the price of contracts. | Regulated rates decouple price from scarcity. |
| `dig:providers:ppa-price` -> `dig:providers:provider-margin` | drives | Contract prices set provider margins. | Costs move one for one with prices. |
| `dig:providers:provider-margin` -> `dig:providers:credit` | funds | Margins support the credit that funds new supply. | New supply is funded externally regardless of margins. |
| `dig:providers:transmission-owner` -> `dig:providers:load-growth` | serves | Transmission delivers the growth and earns a regulated return. | Growth reaches load without new transmission. |

### Nine infrastructure cycles as one phase machine

`dig:cycles:analogue-infrastructure` · root `mechanism:capacity:constraint` · ceiling **testable** · nodes 10 · edges 7

**Why.** The current buildout is not the first. Nine recorded infrastructure cycles share a phase ordering, and the analogue requirement in docs/plan/regimes.md makes the ordering testable rather than rhetorical.

**Chain.** `dig:cycles:shortage` -> `dig:cycles:buildout` -> `dig:cycles:overbuild` -> `dig:cycles:shakeout` -> `dig:cycles:second-wave`

**Greatest assumption.** The current complex follows the same phase ordering as at least two of the nine analogues.

**Kill test.** The current build stays fully preleased and self-funded with no price collapse, which would show phase 3 was skipped rather than delayed.

| Node | Layer | Players | Observables | Payer | Evidence | Source |
|---|---|---|---|---|---|---|
| **Phase 1, shortage** `dig:cycles:shortage` | mechanism | none named | analogue-cycles.jsonl | incumbent capacity holders | E2 | docs/scan/analogue-cycles.jsonl |
| **Phase 2, buildout** `dig:cycles:buildout` | mechanism | none named | analogue-cycles.jsonl | suppliers and early builders | E2 | docs/scan/analogue-cycles.jsonl |
| **Phase 3, overbuild** `dig:cycles:overbuild` | mechanism | none named | analogue-cycles.jsonl | no one; shorts | E2 | docs/scan/analogue-cycles.jsonl |
| **Phase 4, shakeout** `dig:cycles:shakeout` | mechanism | none named | analogue-cycles.jsonl | distressed buyers | E2 | docs/scan/analogue-cycles.jsonl |
| **Phase 5, second wave** `dig:cycles:second-wave` | mechanism | none named | analogue-cycles.jsonl | consolidated owners | E2 | docs/scan/analogue-cycles.jsonl |
| **Railroads analogue** `dig:cycles:railroads` | event | none named | analogue-cycles.jsonl | reorganizers | E2 | cycle:railroads-us |
| **Merchant power analogue** `dig:cycles:merchant-power` | event | none named | analogue-cycles.jsonl | asset buyers | E2 | cycle:merchant-power-us |
| **Fiber analogue** `dig:cycles:fiber` | event | none named | analogue-cycles.jsonl | dark fiber buyers | E2 | cycle:telecom-fiber |
| **Cloud and colocation analogue** `dig:cycles:colocation` | event | none named | analogue-cycles.jsonl | contracted owners | E2 | cycle:cloud-colocation |
| **Nuclear analogue** `dig:cycles:nuclear` | event | none named | analogue-cycles.jsonl | completed plant owners | E2 | cycle:nuclear-build-us |

Sub-items to fetch for every node above: composition, inputs, constraints, observables, substitutes, payers.

| Edge | Relation | Condition | Falsifier |
|---|---|---|---|
| `dig:cycles:shortage` -> `dig:cycles:buildout` | precedes | Shortage invites capital. | Capital arrives without scarcity. |
| `dig:cycles:buildout` -> `dig:cycles:overbuild` | precedes | Capex clusters because competitors can see the same shortage. | Builds are staggered enough to match demand. |
| `dig:cycles:overbuild` -> `dig:cycles:shakeout` | precedes | Price collapse bankrupts the levered. | Declines are shallow enough to avoid failures. |
| `dig:cycles:shakeout` -> `dig:cycles:second-wave` | precedes | Distressed assets need operators with cheap capital. | Assets stay stranded. |
| `dig:cycles:merchant-power` -> `dig:cycles:buildout` | observed_in | Turbine scarcity in 1999 to 2002 is the same marker as the current cycle. | Current turbine scarcity has a different cause. |
| `dig:cycles:fiber` -> `dig:cycles:overbuild` | observed_in | Dark fiber is the same overbuild object as idle interconnection capacity. | Interconnection capacity is consumed on arrival. |
| `dig:cycles:colocation` -> `dig:cycles:buildout` | observed_in | Hyperscale self-build is the same capital pattern as the current build. | Capital is all equity and preleased. |

### Entry windows: the edge must work without latency, and then latency adds

`dig:exec:entry-windows` · root `event:sec:8k-material-agreement` · ceiling **testable** · nodes 7 · edges 6

**Why.** A fast estimate of what a filing or disclosure means is worth size and timing, not existence. Every chain here must survive at zero latency advantage, and the entry windows are written down so the improvement can be measured.

**Chain.** `dig:exec:event-stamp` -> `dig:exec:parse-latency` -> `dig:exec:state-estimate` -> `dig:exec:entry-window` -> `dig:exec:capacity`

**Greatest assumption.** The edge is profitable with no latency advantage, so speed improves size and price rather than being the reason the edge exists.

**Kill test.** The strategy's profit disappears when entries are delayed by one bar, which would prove it was a latency business.

| Node | Layer | Players | Observables | Payer | Evidence | Source |
|---|---|---|---|---|---|---|
| **Event timestamp** `dig:exec:event-stamp` | event | SEC EDGAR, RTOs, issuers | EDGAR acceptance timestamps; queue update posts | the strategy | E1 | results/; EDGAR |
| **Interpretation latency** `dig:exec:parse-latency` | mechanism | our stack | parser logs | the strategy | E1 | internal |
| **State estimation job** `dig:exec:state-estimate` | mechanism | our stack | job runtimes; estimate error against settled states | the strategy | E3 | docs/inbox notes on QGM and spectral methods |
| **Entry window** `dig:exec:entry-window` | mechanism | the market | quote snapshots; post-disclosure drift | the strategy | E2 | market data |
| **Capacity and slippage** `dig:exec:capacity` | mechanism | the market | adv; fill ledger; impact estimates | the strategy | E1 | results/ |
| **Edge decay half life** `dig:exec:decay` | outcome | the strategy | event study by horizon | the strategy | E3 | to measure |
| **Zero latency rehearsal** `dig:exec:zero-latency-rehearsal` | experiment | our stack | delayed entry backtest | the strategy | E3 | to run |

Sub-items to fetch for every node above: composition, inputs, constraints, observables, substitutes, payers.

| Edge | Relation | Condition | Falsifier |
|---|---|---|---|
| `dig:exec:event-stamp` -> `dig:exec:parse-latency` | requires | The clock starts at publication. | Timestamps are unavailable or wrong. |
| `dig:exec:parse-latency` -> `dig:exec:state-estimate` | feeds | The parser hands a classified event to the estimator. | The estimate needs no classification. |
| `dig:exec:state-estimate` -> `dig:exec:entry-window` | beats_clock | A faster estimate reaches the entry window earlier. | The window is long enough that speed does not matter. |
| `dig:exec:entry-window` -> `dig:exec:capacity` | bounds | The window length bounds the size that can be filled. | Liquidity exceeds what the window allows. |
| `dig:exec:capacity` -> `dig:exec:decay` | gates | Impact consumed at entry competes with the decay of the edge. | Impact is negligible at target size. |
| `dig:exec:zero-latency-rehearsal` -> `dig:exec:decay` | tests | Delayed entries test whether the edge exists without speed. | Delayed entry performs the same, which is fine, and the rehearsal still decides. |

### Compute rentals to provider revenue to equity, written as nodes

`dig:compute:provider-transmission` · root `feature:compute:rental-price` · ceiling **testable** · nodes 11 · edges 11

**Why.** The provider family claims rental change reaches provider economics through revenue. The aggregate was tested and came back inside the null (T19), and the family level signs disagree, which leaves the middle object open: which rental family each provider actually sells, and what its revenue is levered to.

**Chain.** `feature:compute:rental-price` -> `dig:compute:provider-revenue-line` -> `dig:compute:revenue-per-mw` -> `dig:compute:equity-transmission`

**Greatest assumption.** Each provider's revenue is levered to one identifiable rental family, and the aggregate median washes that structure out rather than the mechanism being absent.

**Kill test.** After the exposure map is written, family specific transmission shows no association for any provider family pair.

| Node | Layer | Players | Observables | Payer | Evidence | Source |
|---|---|---|---|---|---|---|
| **Provider revenue line** `dig:compute:provider-revenue-line` | outcome | AMZN, MSFT, GOOGL, META, ORCL, CRWV, IREN, APLD, CORZ, EQIX | SEC XBRL revenue concepts, quarterly durations | provider shareholders | E2 | SEC XBRL; results/provider-revenue-quarterly.csv |
| **Rental to revenue link** `dig:compute:rental-to-revenue-link` | mechanism | providers, rental marketplaces | results/provider-transmission-study.json | provider shareholders | E2 | own study, T19 |
| **Provider to family exposure map** `dig:compute:family-exposure-map` | feature | providers, cloud resellers, neocloud hosts | provider disclosures; instance type catalogues | provider shareholders | E4 | to be built |
| **Revenue per contracted megawatt** `dig:compute:revenue-per-mw` | feature | providers, utilities | provider filings | provider shareholders | E3 | provider filings |
| **Contracted against merchant share** `dig:compute:contracted-share` | feature | providers, hyperscalers | provider disclosures | provider shareholders | E3 | provider filings |
| **Lease and renewal spread** `dig:compute:lease-spread` | feature | providers, tenants | provider disclosures | provider shareholders | E3 | provider filings |
| **Power cost pass through** `dig:compute:power-cost-pass-through` | contract | providers, utilities, tenants | contract excerpts; utility tariffs | provider shareholders or tenants | E3 | contracts |
| **Depreciation policy on accelerator fleets** `dig:compute:depreciation-policy` | rule | providers, auditors | annual reports, useful life notes | provider shareholders | E3 | annual reports |
| **Tenant concentration** `dig:compute:tenant-concentration` | entity | providers, hyperscalers | provider disclosures | provider shareholders | E3 | provider filings |
| **Financing cost and structure** `dig:compute:financing-cost` | contract | providers, lenders, rating agencies | agency publications; results/agency-universe.csv | provider equity and debt holders | E2 | agency data in hand |
| **Equity transmission** `dig:compute:equity-transmission` | asset | providers, investors | results/provider-capex-quarterly.csv; price and multiple panels | end holder | E4 | to be built |

Sub-items to fetch for every node above: composition, inputs, constraints, observables, substitutes, payers.

| Edge | Relation | Condition | Falsifier |
|---|---|---|---|
| `feature:compute:rental-price` -> `dig:compute:provider-revenue-line` | drives | Rental resets pass into provider revenue with a lag. | Rental changes leave revenue growth unmoved in the same direction, as the aggregate test found (T19). |
| `dig:compute:family-exposure-map` -> `dig:compute:rental-to-revenue-link` | conditions | Each provider's revenue is levered to specific families, so family level tests replace the aggregate. | No provider family pair shows any association once the map is used. |
| `dig:compute:rental-to-revenue-link` -> `dig:compute:revenue-per-mw` | refines | Transmission shows up per unit of committed capacity before it shows up in total revenue. | Revenue per megawatt moves against total revenue for the same provider. |
| `dig:compute:contracted-share` -> `dig:compute:revenue-per-mw` | conditions | Contracted share sets how much of the rental change reaches revenue inside the year. | Revenue per megawatt is insensitive to the contracted share. |
| `dig:compute:lease-spread` -> `dig:compute:revenue-per-mw` | drives | Renewal pricing is the observed version of the rental change at the provider level. | Lease spreads move opposite to rental prices for the same period. |
| `dig:compute:power-cost-pass-through` -> `dig:compute:revenue-per-mw` | conditions | Where power cost passes through, rental economics reach the provider undiluted by energy cost. | Provider margin per megawatt is flat across pass through and non pass through contracts. |
| `dig:compute:tenant-concentration` -> `dig:compute:provider-revenue-line` | conditions | Concentrated tenants hold pricing power and slow the pass through of rental resets. | Revenue growth is unrelated to tenant concentration. |
| `dig:compute:depreciation-policy` -> `dig:compute:equity-transmission` | drives | Useful life assumptions convert cash economics into reported earnings. | Earnings revisions are insensitive to depreciation policy changes. |
| `dig:compute:financing-cost` -> `dig:compute:equity-transmission` | drives | Funding cost sets the discount applied to capacity cash flows. | Equity reaction to capacity news is unrelated to funding structure. |
| `dig:compute:revenue-per-mw` -> `dig:compute:equity-transmission` | drives | Revenue per megawatt is the cash flow line that equity prices. | Equity revisions follow total revenue while revenue per megawatt stays flat. |
| `dig:compute:financing-cost` -> `dig:compute:provider-revenue-line` | feeds | Securitised and debt funded capacity shows up as contracted revenue before it shows up as equity value. | Funded capacity adds no contracted revenue. |

### The forced seller, written as nodes, and the cost hurdle it faces

`dig:flow:forced-seller` · root `dig:flow:trigger-identity` · ceiling **testable** · nodes 12 · edges 10

**Why.** The cascade family claims a forced seller creates a dislocation that reverts enough to pay for entry after the flow. The reversion was measured on the recorded tape (T20): the percentile levels do not clear the cost hurdle, and the frozen conjunction's gross does, on six events. The nodes here write the mechanism and the constraint, so the next pass tests identity and cheaper entry rather than wider ladders.

**Chain.** `dig:flow:trigger-identity` -> `dig:flow:liquidation-engine` -> `dig:flow:oi-collapse` -> `dig:flow:depth-vacuum` -> `dig:flow:reversion-half-life` -> `dig:flow:cost-hurdle`

**Greatest assumption.** The forced seller is identifiable in real time from the observable conjunction, and that identity does not require a speed advantage.

**Kill test.** Extended tape shows the conjunction's gross reversion inside the cost hurdle at the same horizons.

| Node | Layer | Players | Observables | Payer | Evidence | Source |
|---|---|---|---|---|---|---|
| **Trigger identity** `dig:flow:trigger-identity` | event | levered accounts, venues | funding extremes; open interest collapse; liquidation prints | the forced account | E4 | to be built |
| **Liquidation engine** `dig:flow:liquidation-engine` | mechanism | venues, clearing | venue documentation; results/cascade-tape.json | forced accounts | E3 | venue documentation |
| **Funding extreme** `dig:flow:funding-extreme` | feature | perpetual traders | funding rate, results/cascade-reversion-study.json | crowded side holders | E2 | recorded tape; 769 events measured |
| **Open interest collapse** `dig:flow:oi-collapse` | feature | perpetual traders | open interest from the tape | forced accounts | E2 | recorded tape; part of the frozen conjunction |
| **Depth vacuum** `dig:flow:depth-vacuum` | feature | market makers, takers | depth from the tape | takers | E2 | recorded tape; 2,139 events measured |
| **Dislocation magnitude** `dig:flow:dislocation-magnitude` | outcome | takers, forced accounts | one minute and five minute moves | the counterparty side | E2 | recorded tape; 103 events at the top one percent |
| **Reversion half life** `dig:flow:reversion-half-life` | feature | liquidity providers | results/cascade-reversion-study.json | liquidity providers | E2 | own study, T20 |
| **Cost hurdle** `dig:flow:cost-hurdle` | rule | venues, takers | fee schedules, measured spreads | takers | E2 | own study, T20 |
| **Maker entry candidate** `dig:flow:maker-entry-candidate` | claim | liquidity providers | best bid and ask from the tape | fill counterparties | E4 | to be tested |
| **Capacity by depth** `dig:flow:capacity-by-depth` | feature | takers | median depth at events: about 1.9 million dollars at the top one percent level, 950 dollars when the book is thin | takers | E2 | recorded tape |
| **Market heterogeneity** `dig:flow:market-heterogeneity` | feature | perpetual traders | results/cascade-reversion-study.json | takers | E2 | own study, T20 |
| **Zero latency entry rule** `dig:flow:zero-latency-entry-rule` | strategy | us | results/cascade-reversion-study.json | end holder | E2 | declared protocol and measured |

Sub-items to fetch for every node above: composition, inputs, constraints, observables, substitutes, payers.

| Edge | Relation | Condition | Falsifier |
|---|---|---|---|
| `dig:flow:trigger-identity` -> `dig:flow:liquidation-engine` | drives | An identifiable forced account is what makes the engine act. | Dislocations of the same size occur with no identifiable forced side. |
| `dig:flow:liquidation-engine` -> `dig:flow:oi-collapse` | exposes | Forced liquidation closes positions, so open interest falls with the move. | Large moves at the same conditions occur with rising open interest. |
| `dig:flow:oi-collapse` -> `dig:flow:depth-vacuum` | drives | Closing flow consumes the resting book and leaves thinner depth behind it. | Depth at the events is no thinner than its trailing level. |
| `dig:flow:funding-extreme` -> `dig:flow:dislocation-magnitude` | conditions | Extreme funding marks the crowded side that breaks first. | Funding extremes precede no larger moves than average, as the measured level suggests (taken direction was wrong). |
| `dig:flow:dislocation-magnitude` -> `dig:flow:reversion-half-life` | drives | The larger the forced move, the more room to revert. | Reversion shows no relation to move size. |
| `dig:flow:cost-hurdle` -> `dig:flow:reversion-half-life` | conditions | Only reversion above the round trip cost is capitalizable. | Net reversion is positive where gross is below the hurdle. |
| `dig:flow:maker-entry-candidate` -> `dig:flow:cost-hurdle` | refines | A resting order replaces the taker fee and half the spread with fill risk. | Maker fills at the extreme do not improve the realized net. |
| `dig:flow:capacity-by-depth` -> `dig:flow:maker-entry-candidate` | conditions | Maker entry is only possible where the book has size to fill. | Fills appear at events whose depth is too thin to matter. |
| `dig:flow:market-heterogeneity` -> `dig:flow:reversion-half-life` | conditions | Reversion pools only markets whose structure supports it. | The per market differences vanish with more events. |
| `dig:flow:zero-latency-entry-rule` -> `dig:flow:reversion-half-life` | conditions | The measured reversion is the one available at bar close, with no speed used. | The reversion exists only inside the first seconds after the event. |


## The analogue cycles, the temporal backbone

Nine recorded infrastructure cycles with the same phase ordering. Method owner:
`docs/plan/regimes.md`. Every claim of a ten to twenty year rationale is checked against
at least two of these.

| Cycle | Era | Trigger | What persisted | What died |
|---|---|---|---|---|
| **US railroads, the first infrastructure bubble** `cycle:railroads-us` | 1840s to 1900 | Land grants and the telegraph making long distance freight and information cheap. | Freight demand and the physical network; the second owner of an asset bought at receiver prices. | The promotional equity and the first generation of parallel lines. |
| **Electrification and the utility holding company bubble** `cycle:electric-utilities-us` | 1890s to 1935 | Cheap alternating current transmission made electricity a networked product. | The physical grid and the regulated compact. | Layered holding company leverage and the promotional marketing behind it. |
| **Merchant power and deregulation** `cycle:merchant-power-us` | 1998 to 2006 | Deregulation promised competitive generation markets and merchant plants earned development premiums. | Physical generation and the capacity market design that pays for standing still. | The merchant development premium and its high yield financing. |
| **The nuclear build and its cancellations** `cycle:nuclear-build-us` | 1965 to 1990 | Utility demand growth forecasts and a technology seen as too cheap to meter. | Completed plants, and the lesson that late cost arrives after demand forecasts decay. | Construction work in progress and the demand forecasts underwriting it. |
| **The fiber and telecom bubble** `cycle:telecom-fiber` | 1996 to 2005 | The 1996 Telecom Act and the internet traffic forecasts of the late 1990s. | The glass in the ground and the traffic that eventually used it. | The debt and the equipment vendor financing cycle. |
| **Midstream MLPs and pipeline overbuild** `cycle:midstream-mlp` | 2008 to 2020 | Shale production growth needed gathering and takeaway capacity. | The pipes and the fee-based contracts on them. | The distribution growth promise and the leverage behind it. |
| **Cloud and colocation, the most recent analogue** `cycle:cloud-colocation` | 2006 to 2018 | Commodity server virtualization and the shift of enterprise IT to rented capacity. | Land, power interconnections and the leasing contracts. | Speculative wholesale builds without preleasing. |
| **US LNG export buildout** `cycle:lng-export-us` | 2012 to 2026 | Shale gas abundance and global demand for flexible molecules. | The contracted tolling model that survived the price cycle. | Speculative merchant capacity. |
| **Offshore wind and the cable bottleneck** `cycle:offshore-wind-hvdc` | 2010 to 2026 | Decarbonisation targets and maturing fixed bottom technology. | The cable, vessel and port capacity, which re-priced upward through the bust. | Fixed price contracts written before cost inflation. |

### US railroads, the first infrastructure bubble

`cycle:railroads-us` | 1840s to 1900

| Phase | Years | Markers | Outcome |
|---|---|---|---|
| 1. Shortage | 1840s-1850s | Ports and canals at capacity, freight rates high, charters granted freely. | Incumbent carriers and canal owners collect. |
| 2. Buildout | 1860s-1870s | Mileage doubles, labor and iron shortages, bond issuance explodes, promoters paid in stock. | Suppliers and early promoters win. |
| 3. Overbuild | 1870s-1890s | Parallel lines, rate wars, freight rates collapse, receiverships. | Equity holders wiped out in successive panics. |
| 4. Shakeout | 1893-1898 | A quarter of US rail mileage in receivership, consolidation into trunk systems. | Bondholders and reorganizers take control. |
| 5. Second wave | 1900s | Regulated rates, stable freight, consolidated trunk lines earn steady returns. | Regulated returns for consolidated owners. |

**Funding.** Bonds, land grants, and speculative equity, with many lines oversubscribed before a single rail was laid.

**Mapping to current nodes.** `mechanism:capacity:constraint` (same_shape: Capacity shortage, promotional capital, overbuild, consolidation is the same sequence.); `outcome:firm:capex-timing` (marker: Capex growth alone never identified the turning point, which is why phase markers are paired.)

**Falsifier.** Infrastructure cycles since then show no overbuild or shakeout phase.


### Electrification and the utility holding company bubble

`cycle:electric-utilities-us` | 1890s to 1935

| Phase | Years | Markers | Outcome |
|---|---|---|---|
| 1. Shortage | 1890s | City franchises scarce, electricity expensive, small isolated plants. | Franchise holders collect. |
| 2. Buildout | 1900s-1920s | Generation and grid capex booms, holding companies acquire hundreds of utilities, pyramided leverage. | Equipment makers and promoters win. |
| 3. Overbuild | 1920s | Capacity ahead of demand, rate competition, holding company leverage opaque. | Equity prices detached from earnings. |
| 4. Shakeout | 1929-1935 | Holding company collapse, defaults, Public Utility Holding Company Act breaking the pyramids. | Retail investors wiped out. |
| 5. Second wave | 1935 onward | Regulated rate base, stable allowed returns, utility becomes a bond-like asset. | Regulated returns for decades. |

**Funding.** Holding company structures with layered debt, marketed to retail investors as a growth story.

**Mapping to current nodes.** `outcome:firm:capex-level` (same_shape: Load growth to capex to rate base is the same regulated conversion that followed the bust.); `factor:macro:rates` (conditional: Rate base economics are rate sensitive, which ties the analogue to our rates factor.)

**Falsifier.** The regulated compact fails to survive the current buildout where it held before.


### Merchant power and deregulation

`cycle:merchant-power-us` | 1998 to 2006

| Phase | Years | Markers | Outcome |
|---|---|---|---|
| 1. Shortage | 1998-2000 | California and other markets with reserve shortfalls, spark spreads wide. | Existing generators earn windfalls. |
| 2. Buildout | 1999-2002 | Over 200GW announced, turbine slots scarce, developers IPO at premiums. | Turbine makers and developers win. |
| 3. Overbuild | 2002-2004 | Reserve margins jump, spark spreads collapse, plants worth less than cost. | Merchant equity destroyed. |
| 4. Shakeout | 2002-2006 | Calpine, Mirant, NRG and others restructure; assets sold at fractions of cost. | Debt holders and buyers take assets. |
| 5. Second wave | 2006 onward | Consolidated fleets with contracts, capacity markets formalised in ISOs. | Contracted and capacity revenue returns. |

**Funding.** Project finance, high yield debt, and IPO windows for merchant developers.

**Mapping to current nodes.** `mechanism:capacity:constraint` (same_shape: Turbine slot scarcity in the current cycle is the same marker as 1999-2002.); `mechanism:capacity:labor-bottleneck` (same_shape: In the analogue, skilled construction labour priced up before the overbuild.)

**Falsifier.** Capacity markets and contracts fail to stabilise returns after the current overbuild.


### The nuclear build and its cancellations

`cycle:nuclear-build-us` | 1965 to 1990

| Phase | Years | Markers | Outcome |
|---|---|---|---|
| 1. Shortage | 1965-1970 | Demand growth strong, oil price risk, reactor orders surge. | Vendors and utilities with early plants. |
| 2. Buildout | 1970-1978 | Order book peaks above 200 reactors, lead times stretch, cost estimates triple. | Vendors and construction firms win. |
| 3. Overbuild | 1974-1982 | Demand growth halves after the oil shocks, plants arrive late and massively over budget. | Utilities with construction work in progress carry the cost. |
| 4. Shakeout | 1979-1990 | Cancellations of over 100 units, WPPSS default, prudence disallowances. | Ratepayers and shareholders absorb the losses. |
| 5. Second wave | 1990s onward | Completed plants run cheaply for decades, life extensions, uprates. | Owners of completed plants earn durable margins. |

**Funding.** Regulated rate base and construction work in progress, with cost overruns eventually disallowed.

**Mapping to current nodes.** `dig:nuc:firm-power` (same_shape: The current firm power contracts are the analogue's early phase, and the cancellation risk is phase 3.); `mechanism:delivery:revision-to-cash-flow` (same_shape: Cost and schedule revisions are the analogue's central failure mode, which is exactly the object we measured.)

**Falsifier.** Modular construction and fixed price contracts remove the overrun mechanism.


### The fiber and telecom bubble

`cycle:telecom-fiber` | 1996 to 2005

| Phase | Years | Markers | Outcome |
|---|---|---|---|
| 1. Shortage | 1995-1997 | Long distance and internet capacity tight, incumbents profitable. | Incumbents collect. |
| 2. Buildout | 1997-2001 | Long haul fiber mileage multiplied, equipment order books full, vendor financing hides demand quality. | Equipment makers and contractors win. |
| 3. Overbuild | 2000-2002 | Most installed fiber dark, bandwidth prices collapse over ninety percent, traffic forecasts missed by years. | Carrier equity destroyed. |
| 4. Shakeout | 2001-2005 | Global Crossing, 360networks, WorldCom failures; equipment vendors restructure. | Dark fiber bought at cents on the dollar. |
| 5. Second wave | 2005 onward | Survivors and new entrants light the fiber for video and cloud traffic at low cost. | Buyers of cheap assets earn the second wave. |

**Funding.** High yield bonds, vendor financing from equipment makers, and equity at extraordinary multiples.

**Mapping to current nodes.** `mechanism:capacity:interconnection-bottleneck` (same_shape: Dark fiber is the analogue of dark interconnection capacity, bought cheap by the second wave.); `dig:fiber:interconnect` (same_shape: Interconnect is that same physical layer in the current cycle.)

**Falsifier.** Current capacity additions are matched to demand with contracts that cannot reprice.


### Midstream MLPs and pipeline overbuild

`cycle:midstream-mlp` | 2008 to 2020

| Phase | Years | Markers | Outcome |
|---|---|---|---|
| 1. Shortage | 2008-2012 | Takeaway constraints, basis differentials wide, gathering fees strong. | Existing pipeline owners collect. |
| 2. Buildout | 2012-2016 | Capital spending multiples distributable cash flow, projects announced far ahead of volume. | Contractors and early investors win. |
| 3. Overbuild | 2015-2019 | Basin congestion reverses, fee compression, some pipelines underutilised at completion. | Levered MLPs de-rate as distributions exceed cash flow. |
| 4. Shakeout | 2018-2021 | Distribution cuts, consolidation into corporate structures, ESG-driven capital exit. | Units holders lose a decade. |
| 5. Second wave | 2021 onward | Consolidated midstream with buybacks and fee-based contracts, energy transition discount slowly lifts. | Consolidators earn returns on cheap assets. |

**Funding.** MLP structures with distribution growth promises, funded by debt and equity issuance.

**Mapping to current nodes.** `outcome:firm:free-cash-flow` (same_shape: The phase 4-5 value came from free cash flow discipline after growth died.); `asset:equity:utility-basket` (same_shape: The shift to contracted, fee-like structures is the same second wave shape.)

**Falsifier.** Contracted take-or-pay structures prevent the overbuild repricing.


### Cloud and colocation, the most recent analogue

`cycle:cloud-colocation` | 2006 to 2018

| Phase | Years | Markers | Outcome |
|---|---|---|---|
| 1. Shortage | 2006-2010 | Power-dense colocation scarce in primary markets, rents firm. | Early colocation owners collect. |
| 2. Buildout | 2010-2015 | Hyperscaler self-build plus REIT acquisition, powered shell development booms. | REITs and contractors win. |
| 3. Overbuild | 2015-2018 | Secondary market vacancies rise, rent concessions, wholesale leases at lower spreads. | Speculative developers underperform. |
| 4. Shakeout | 2016-2019 | Consolidation of small hosts, operator exits, asset sales. | Platforms acquire distressed capacity. |
| 5. Second wave | 2019 onward | Preleased hyperscale campuses, REIT structures with long contracts, dividends. | Contracted owners earn stable returns. |

**Funding.** REIT conversions, venture capital for platforms, vendor financing from server makers.

**Mapping to current nodes.** `entity:datacenter:site` (same_shape: The current AI build is the same asset class entering its own phase 2.); `mechanism:capacity:cooling-bottleneck` (new_in_cycle: Cooling density is the variable the cloud cycle largely did not have at scale, so the analogue is partial.)

**Falsifier.** Current build is fully preleased and self-funded, which would skip the speculative phase.


### US LNG export buildout

`cycle:lng-export-us` | 2012 to 2026

| Phase | Years | Markers | Outcome |
|---|---|---|---|
| 1. Shortage | 2012-2016 | Global LNG tight, Asian spot prices high, US projects queue for permits. | Existing exporters and engineering firms. |
| 2. Buildout | 2016-2024 | Train FIDs cluster, engineering and module yards saturated, long lead equipment booked. | Engineers and early contract holders win. |
| 3. Overbuild | 2025 onward | Global liquefaction capacity grows faster than contracted demand, spot spreads compress. | Contracted sellers protected, merchant volumes exposed. |
| 4. Shakeout | ahead | Cancellations of speculative trains, consolidation of developers. | Buyers of stranded assets. |
| 5. Second wave | ahead | Fully contracted trains with stable tolling revenue. | Contracted owners. |

**Funding.** 20 year take-or-pay contracts and project finance on contracted volumes.

**Mapping to current nodes.** `dig:nuc:firm-power` (same_shape: Take-or-pay contracts are the analogue of firm power PPAs for data centers.); `mechanism:capacity:constraint` (same_shape: Engineer and module capacity were the binding constraint in phase 2.)

**Falsifier.** Contracted volumes cover all new capacity so no merchant exposure remains.


### Offshore wind and the cable bottleneck

`cycle:offshore-wind-hvdc` | 2010 to 2026

| Phase | Years | Markers | Outcome |
|---|---|---|---|
| 1. Shortage | 2010-2016 | Subsidy support strong, few capable installers, costs falling. | Developers and turbine makers. |
| 2. Buildout | 2016-2022 | Cable and vessel capacity sells out years ahead, turbine prices firm, auction prices hit zero subsidy. | Cable makers, ships, contractors win. |
| 3. Overbuild | 2022-2025 | Cost inflation and financing rates break project economics, developers cancel contracted projects and write penalties. | Developers and utilities absorb losses. |
| 4. Shakeout | 2023-2026 | Auction cancellations, supply chain losses, turbine maker writedowns. | Owners of scarce inputs keep pricing power. |
| 5. Second wave | ahead | Indexed contracts pass cost through, consolidated supply chain. | Contracted infrastructure owners. |

**Funding.** Contract for difference auctions, utility balance sheets, and supply chain credit.

**Mapping to current nodes.** `dig:hvdc:cable-ships` (same_shape: Cable ships and cables are the current cycle's analogue of scarce installation capacity.); `dig:power:hvdc-converter` (same_shape: Converter and valve capacity repeat the same bottlenecks.)

**Falsifier.** Supply chain capacity expands ahead of project awards so no bottleneck pricing appears.

