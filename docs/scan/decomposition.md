# Decomposition: the graph at sub-node resolution

Method owner: `docs/plan/decomposition.md`. Every node decomposes into at least six children
along the dimensions of its layer, and every child decomposes again. The skeleton is written
out and labelled `proposed_unverified`; the curated digs are where domain knowledge fills the
levels with named minerals, suppliers, observables and payers.

**Written graph: 23,703 nodes** (555 declared + 19,980 skeleton children + 3,168 children of curated dig nodes), 23,148 split edges.

- Manifest nodes decomposed: 555, minimum children per node: 6

- Curated dig nodes: 88, digs: 13

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

