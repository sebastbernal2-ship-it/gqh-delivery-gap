# Connection chains, graded

Method owner: `docs/plan/deep-connections.md`. Every link carries its evidence class, its
load and the kill test that would show it wrong. The greatest assumption is computed, not
declared: the highest-load link with the weakest evidence class.

Chains: 13. Links: 52. Evidence: E1 3, E2 18, E3 23, E4 8. Loads: high 39, low 4, medium 9.

| Chain | Ceiling | Payer | Greatest assumption |
|---|---|---|---|
| `chain:power:aluminum-to-conductors` | testable | smelters with hedged power collect; cable and conductor buyers pay | Curtailment decisions respond to spot and forward power within a quarter. |
| `chain:power:goes-steel-to-transformer-output` | testable | steel makers with GOES capacity collect rent while transformer output is capped | No substitute material qualifies for the large units on the critical path. |
| `chain:power:load-growth-to-rate-base` | testable | ratepayers pay the return; utility shareholders collect it if the case is allowed | The regulatory compact holds and capital is recovered with a fair return. |
| `chain:power:panama-drought-to-power` | testable | US gas producers and power sellers see the flow shift; importers pay | The restriction is not offset by booking auctions and rerouting at scale. |
| `chain:power:transformer-scarcity-to-supplier-margin` | testable | equipment makers collect pricing power, developers and ratepayers pay for it in delay and cost | The lead time is a queue, not a price, so it cannot be cleared by paying more in the short run. |
| `chain:power:turbine-slots-to-power-price` | testable | merchant generators with existing capacity collect the scarcity; late entrants pay for it | Slot holders cannot flip slots to faster projects when prices rise. |
| `chain:power:upgrade-costs-to-withdrawals` | testable | developers eat the study cost; equipment makers whose slots were reserved absorb the cancellation | Withdrawals are economically driven, not housekeeping of duplicate applications. |
| `chain:promise:revision-to-cash-flow` | testable | the developer's cash flow moves; the question is who agreed to pay for the delay | The null generalises to the bigger revisions we can now see in the queue-matched subset. |
| `chain:power:cooling-water-to-siting` | watch | utilities in water-stressed service areas lose the load, or pay to build the water side | Water use stays large, rather than shifting to closed-loop or air cooling designs. |
| `chain:power:labor-to-schedules` | watch | contractors with crews price the scarcity; developers absorb the schedule | Crews do not move freely across regions fast enough to clear local scarcity. |
| `chain:power:rates-to-schedules` | watch | the marginal project dies first | Developers re-underwrite on rate moves rather than ride fixed-rate project debt. |
| `chain:power:wildfire-insurance-to-utility-credit` | watch | utility security holders absorb liability; ratepayers absorb the recovery | Public utility commissions do not fully substitute for the insurance market. |
| `chain:salmon:temperature-to-index` | watch | integrated farmers with the best sites collect; feed costs and lice limits decide the margin | Temperature is the leading driver among biology, regulation and feed. |

## Cheap power makes aluminum, expensive power unmakes it, and conductors gate the grid

`chain:power:aluminum-to-conductors` · anchor `mechanism:capacity:constraint` · outcome `outcome:firm:capex-timing` · ceiling **testable**

**Payer.** smelters with hedged power collect; cable and conductor buyers pay

**Why now.** power price spikes curtail smelting, and the same buildout needs aluminium conductor at scale

**Nodes proposed.** `material:aluminum:conductor` (raw)

| # | Link | Kind | Evidence | Load | Assumption | Kill test |
|---|---|---|---|---|---|---|
| 1 **greatest** | Aluminium smelting is a power contract business that curtails when power resale beats smelting. | behavioral | E2 | high | Curtailment decisions respond to spot and forward power within a quarter. | Smelters run through price spikes because contracts are fully hedged. |
| 2 | Curtailment removes conductor supply exactly when the grid buildout raises conductor demand. | constraint | E3 | high | Other regions expand smelting output fast enough to fill the gap, which is the thing to test. | Conductor prices and lead times stay flat through curtailment episodes. |
| 3 | The observable is smelter curtailment announcements joined to conductor lead times and cable maker backlogs. | accounting | E3 | medium | Curtailment announcements are dated precisely enough to align with lead times. | The announcement dates cannot be reconstructed point in time. |

**Greatest assumption.** Curtailment decisions respond to spot and forward power within a quarter. (E2, load high)

**Kill test.** Smelters run through price spikes because contracts are fully hedged.

## Grain-oriented steel is the transformer core bottleneck

`chain:power:goes-steel-to-transformer-output` · anchor `mechanism:capacity:transformer-bottleneck` · outcome `outcome:firm:capex-timing` · ceiling **testable**

**Payer.** steel makers with GOES capacity collect rent while transformer output is capped

**Why now.** transformer capacity additions depend on a narrow class of electrical steel that few mills make

**Nodes proposed.** `material:steel:goes` (raw)

| # | Link | Kind | Evidence | Load | Assumption | Kill test |
|---|---|---|---|---|---|---|
| 1 **greatest** | Transformer cores need grain-oriented electrical steel, produced by a small set of mills. | constraint | E2 | high | No substitute material qualifies for the large units on the critical path. | Amorphous or alternative core designs take share in large units. |
| 2 | GOES capacity additions are slow and lumpy, so transformer output cannot outrun steel supply. | constraint | E3 | high | GOES, not copper, labor or winding capacity, is the binding input in practice. | Transformer output rises while GOES supply is flat, for example through imports that fill the gap. |
| 3 | When the binding input is scarce, its price and allocation power rise before the downstream product price does. | causal | E3 | medium | Contracts reprice within a year rather than riding long-term fixed prices. | GOES contract prices stay flat through a scarcity episode. |
| 4 | The observable is import volumes and unit values by origin, joined to transformer shipment data. | accounting | E3 | medium | Customs codes separate GOES from other flat steel well enough to measure it. | The HS line is too broad to isolate GOES. |

**Greatest assumption.** No substitute material qualifies for the large units on the critical path. (E2, load high)

**Kill test.** Amorphous or alternative core designs take share in large units.

## Load growth fills regulated rate base, if regulators allow it

`chain:power:load-growth-to-rate-base` · anchor `outcome:firm:capex-level` · outcome `outcome:firm:free-cash-flow` · ceiling **testable**

**Payer.** ratepayers pay the return; utility shareholders collect it if the case is allowed

**Why now.** load growth forecasts in data-center regions turned up after two decades of flat demand

| # | Link | Kind | Evidence | Load | Assumption | Kill test |
|---|---|---|---|---|---|---|
| 1 **greatest** | Regulated utilities earn a return on capital invested, so load growth converts into capex plans and rate base growth. | constraint | E2 | high | The regulatory compact holds and capital is recovered with a fair return. | Rate cases start disallowing the demand-driven capex at scale. |
| 2 | Load growth is observable in balancing-authority demand before it becomes capex, which gives the ordering variable. | accounting | E2 | high | The demand growth is load-driven and persistent rather than weather or temporary timing. | Growth is a weather artifact that reverses. |
| 3 | The payer side has a political limit: large load growth raises rates for other customers, which invites pushback. | behavioral | E3 | high | The pushback shows up in specific jurisdictions before it shows up in valuations. | Rate outcomes stay uniformly constructive while bills rise. |
| 4 | The edge is jurisdictional dispersion: the same load signal maps to different allowed outcomes by state. | behavioral | E4 | high | The market prices the dispersion in one direction, which is the study's null. | Utility multiples already rank the jurisdictions the way the analysis would. |

**Greatest assumption.** The regulatory compact holds and capital is recovered with a fair return. (E2, load high)

**Kill test.** Rate cases start disallowing the demand-driven capex at scale.

## Canal transit restrictions reach US power through gas

`chain:power:panama-drought-to-power` · anchor `mechanism:capacity:constraint` · outcome `outcome:firm:revenue-level` · ceiling **testable**

**Payer.** US gas producers and power sellers see the flow shift; importers pay

**Why now.** an exotic physical constraint on shipping can move the same gas balances that set our complex's power prices

| # | Link | Kind | Evidence | Load | Assumption | Kill test |
|---|---|---|---|---|---|---|
| 1 **greatest** | Drought lowers canal water levels and cuts daily transit slots. | constraint | E2 | high | The restriction is not offset by booking auctions and rerouting at scale. | Transit volumes recover through alternate routings and slot auctions. |
| 2 | Reduced transits raise voyage times and freight cost for LNG and container flows between the Pacific and the Atlantic. | causal | E2 | high | The affected routes cannot substitute Suez or the Cape without losing the arbitrage. | Rerouting absorbs the restriction with no freight spread. |
| 3 | When LNG routing shifts, US export pull and domestic gas balances shift with it. | causal | E3 | high | US LNG flows are swing volumes sensitive to freight, which is the thing to test. | US feedgas is unchanged through the restriction. |
| 4 | Gas balances set power prices in the marginal market, which is the node our complex already depends on. | causal | E2 | high | The marginal power market is gas-set through the episode. | Power prices decouple from gas in the affected regions. |

**Greatest assumption.** The restriction is not offset by booking auctions and rerouting at scale. (E2, load high)

**Kill test.** Transit volumes recover through alternate routings and slot auctions.

## Transformer scarcity pays the equipment makers, not the event study

`chain:power:transformer-scarcity-to-supplier-margin` · anchor `mechanism:capacity:transformer-bottleneck` · outcome `outcome:firm:cash-flow-revision` · ceiling **testable**

**Payer.** equipment makers collect pricing power, developers and ratepayers pay for it in delay and cost

**Why now.** grid capex is rising while heavy equipment capacity is fixed, and our own event study already showed the delay is not tradable through the developer

| # | Link | Kind | Evidence | Load | Assumption | Kill test |
|---|---|---|---|---|---|---|
| 1 **greatest** | Interconnection and energization require large power transformers and high-voltage gear with multi-year procurement queues. | constraint | E2 | high | The lead time is a queue, not a price, so it cannot be cleared by paying more in the short run. | Lead times shorten while order books stay full and prices fall. |
| 2 | Scarcity in a queue market shows up first as price and allocation power for the equipment makers. | causal | E3 | high | OEMs can hold price because capacity cannot be added inside two years. | Transformer price indices fall while backlogs rise. |
| 3 | Pricing power converts into margins and free cash flow when large projects ship, years after booking. | accounting | E3 | high | Margin is not competed away by Siemens, Hitachi, GE Vernova, and new entrants before delivery. | Backlog converts at flat or falling margins. |
| 4 | The payer is the developer and ultimately the ratepayer, so the same mechanism that makes our delivery tail negative for the developer is positive for the supplier. | accounting | E2 | high | Cost escalation lands on the developer's schedule and budget, not on the OEM's penalty clauses. | Liquidated damages absorb the delay cost at the OEM. |
| 5 | The edge is cross-sectional: whether this is priced depends on relative, not absolute, valuation. | behavioral | E4 | high | The market has not fully capitalised the queue economics into supplier multiples, or has capitalised it unevenly. | Supplier forward multiples already rank the same way as the backlog quality measure. |

**Greatest assumption.** The lead time is a queue, not a price, so it cannot be cleared by paying more in the short run. (E2, load high)

**Kill test.** Lead times shorten while order books stay full and prices fall.

## Turbine slot scarcity delays entry and tightens the local power market

`chain:power:turbine-slots-to-power-price` · anchor `mechanism:capacity:constraint` · outcome `outcome:firm:revenue-level` · ceiling **testable**

**Payer.** merchant generators with existing capacity collect the scarcity; late entrants pay for it

**Why now.** gas plant orders are queued behind a fixed turbine supply while load growth is real and local

| # | Link | Kind | Evidence | Load | Assumption | Kill test |
|---|---|---|---|---|---|---|
| 1 **greatest** | New gas capacity requires turbine slots that are allocated years ahead. | constraint | E2 | high | Slot holders cannot flip slots to faster projects when prices rise. | Slot trading accelerates projects enough to keep dates. |
| 2 | Delayed entry shows up as slipped commercial operation dates in the planned inventory. | accounting | E2 | high | Our planned-sheet revision measure captures this class of slip, which our panels already track. | Gas projects slip for reasons that never reach the planned sheet. |
| 3 | When entry slips in a node with rising load, reserve margins tighten and forward power prices rise. | causal | E3 | high | The local market is tight enough that a two-year slip matters, rather than being covered by imports or demand response. | Reserve margins hold while entry slips, or prices fall. |
| 4 | Existing merchant capacity in that node earns the scarcity, and the payer is the load that cannot move. | accounting | E3 | high | Scarcity rents are not fully hedged away in advance. | Hedges and contracts pass the scarcity through to consumers immediately. |

**Greatest assumption.** Slot holders cannot flip slots to faster projects when prices rise. (E2, load high)

**Kill test.** Slot trading accelerates projects enough to keep dates.

## Interconnection upgrade costs push marginal projects out, and the exit shows up in supplier books

`chain:power:upgrade-costs-to-withdrawals` · anchor `mechanism:capacity:interconnection-bottleneck` · outcome `outcome:firm:contract-cancellation` · ceiling **testable**

**Payer.** developers eat the study cost; equipment makers whose slots were reserved absorb the cancellation

**Why now.** the measured withdrawal share is already 57 percent across the queue, and the cost of the upgrade decision is the clearest reason a marginal project leaves

| # | Link | Kind | Evidence | Load | Assumption | Kill test |
|---|---|---|---|---|---|---|
| 1 | Cluster studies assign network upgrade costs that can exceed a project's economics. | constraint | E2 | high | Upgrade costs are not socialised enough to save marginal projects. | Cost allocation reforms move the burden to ratepayers at scale. |
| 2 **greatest** | When the assigned cost crosses the project's threshold, the rational move is withdrawal, which our queue panel already measures at 57.4 percent. | behavioral | E1 | high | Withdrawals are economically driven, not housekeeping of duplicate applications. | Withdrawals cluster in projects with trivial upgrade costs. |
| 3 | Withdrawn projects had reserved long-lead equipment, so the cancellation reaches supplier order books with a lag. | accounting | E3 | high | Reservations are real and cancellable, not options that were never booked into backlog. | Backlogs are unaffected by queue exit waves. |
| 4 | A queue exit wave is therefore an early observable for supplier guidance risk in the affected segment. | behavioral | E4 | high | The market does not price the exit wave until the supplier discloses it, which is the greatest assumption here and the study's null. | Supplier multiples move with our queue-exit series at the same time, with no lag. |

**Greatest assumption.** Withdrawals are economically driven, not housekeeping of duplicate applications. (E1, load high)

**Kill test.** Withdrawals cluster in projects with trivial upgrade costs.

## The revision to cash-flow chain, where our own null lives

`chain:promise:revision-to-cash-flow` · anchor `mechanism:delivery:revision-to-cash-flow` · outcome `outcome:firm:cash-flow-revision` · ceiling **testable**

**Payer.** the developer's cash flow moves; the question is who agreed to pay for the delay

**Why now.** we measured this chain and the pricing half already failed on our panels, so the chain's value now is the exposure map, not the event study

| # | Link | Kind | Evidence | Load | Assumption | Kill test |
|---|---|---|---|---|---|---|
| 1 | A promise revision delays the revenue of the project, which changes the developer's cash-flow timing. | accounting | E3 | high | The revision is material to reported periods rather than a rounding of the schedule. | Large revisions arrive with no measurable cash-flow disclosure. |
| 2 | Who pays for the delay is written in the contract: fixed-price EPC passes it to the contractor, cost-plus keeps it with the developer. | accounting | E3 | high | Contract type is distinguishable from filings. | Contract structures do not change the incidence of delay cost. |
| 3 **greatest** | The equity pricing of the revision is already measured and null on our panels, so this link is closed rather than assumed. | behavioral | E1 | high | The null generalises to the bigger revisions we can now see in the queue-matched subset. | A larger tail sample overturns the null, in a fresh window. |
| 4 | The remaining untested link is the contract incidence: the same revision should move the contractor's guidance differently than the developer's. | accounting | E4 | high | Contractor guidance reacts to delay cost at all, rather than being absorbed in a diversified book. | Contractors guide through revisions without a measurable pattern. |

**Greatest assumption.** The null generalises to the bigger revisions we can now see in the queue-matched subset. (E1, load high)

**Kill test.** A larger tail sample overturns the null, in a fresh window.

## Cooling water constraints push data-center siting, and the counterexample is loud

`chain:power:cooling-water-to-siting` · anchor `mechanism:capacity:cooling-bottleneck` · outcome `outcome:firm:capex-timing` · ceiling **watch**

**Payer.** utilities in water-stressed service areas lose the load, or pay to build the water side

**Why now.** large-scale computing consumes water for cooling in regions that are also the cheapest power and are drying

| # | Link | Kind | Evidence | Load | Assumption | Kill test |
|---|---|---|---|---|---|---|
| 1 **greatest** | Evaporative cooling consumes water at a scale that matters in stressed basins. | constraint | E2 | high | Water use stays large, rather than shifting to closed-loop or air cooling designs. | New builds shift to designs with negligible water use at scale. |
| 2 | Some regions limit new consumption through permits, discharge rules and aquifer constraints. | constraint | E3 | high | Permitting actually binds before land and power do. | Sites announce and build in the most constrained basins anyway; Phoenix and the desert buildout are the standing counterexample. |
| 3 | When siting is blocked or delayed, the local load growth path and the utility capex tied to it weaken. | accounting | E3 | medium | The delayed load does not simply move to another state in the same utility's footprint. | Load reappears elsewhere in the same balanced area. |
| 4 | This chain is kept as a watch item because its own kill test is a known live counterexample, which is exactly the honest reason not to trade it. | associative | E4 | low | None of the above is decided; the chain's value is that it names the permit data that would decide it. | A permit-level dataset shows water constraints delaying projects relative to matched peers. |

**Greatest assumption.** Water use stays large, rather than shifting to closed-loop or air cooling designs. (E2, load high)

**Kill test.** New builds shift to designs with negligible water use at scale.

## The electrician pipeline, not the equipment, may be the binding schedule constraint

`chain:power:labor-to-schedules` · anchor `mechanism:capacity:labor-bottleneck` · outcome `outcome:firm:capex-timing` · ceiling **watch**

**Payer.** contractors with crews price the scarcity; developers absorb the schedule

**Why now.** equipment queues are public and discussed, while the workforce that installs it is not

| # | Link | Kind | Evidence | Load | Assumption | Kill test |
|---|---|---|---|---|---|---|
| 1 **greatest** | Substation, line and data-center electrical work needs certified crews that take years to train. | constraint | E2 | high | Crews do not move freely across regions fast enough to clear local scarcity. | Regional wage premia stay flat while schedules slip. |
| 2 | Where crews are binding, schedules slip even when equipment arrives on time. | causal | E3 | high | The slippage is separable from equipment delay in project disclosures. | Projects disclose equipment, not labor, as the delay cause. |
| 3 | The tradeable payer is the contractor with regional density, whose margins hold up while the pipeline is long. | accounting | E4 | medium | Contractor margins are visible in segment reporting rather than buried in consolidated numbers. | Contractor margins fall through the buildout. |

**Greatest assumption.** Crews do not move freely across regions fast enough to clear local scarcity. (E2, load high)

**Kill test.** Regional wage premia stay flat while schedules slip.

## Funding cost reaches schedules only through the marginal developer

`chain:power:rates-to-schedules` · anchor `factor:macro:rates` · outcome `outcome:firm:capex-timing` · ceiling **watch**

**Payer.** the marginal project dies first

**Why now.** the whole complex is capital intensive and was financed through a low-rate window, and our panels live inside that window

| # | Link | Kind | Evidence | Load | Assumption | Kill test |
|---|---|---|---|---|---|---|
| 1 **greatest** | Project economics in this complex are rate sensitive because the cash flows start years out. | accounting | E3 | high | Developers re-underwrite on rate moves rather than ride fixed-rate project debt. | Financing is locked at fixed rates for the life of the projects under study. |
| 2 | Higher funding costs push marginal projects over the hurdle, converting into deferral and cancellation. | causal | E3 | high | The marginal project is rate-limited rather than queue-limited or equipment-limited. | Cancellations track queue and equipment constraints, not financing. |
| 3 | Our windows cannot test this: the delivery panels run through the low-rate period, so a rate-regime test needs data this repo does not have yet. | accounting | E1 | low | The honest move is to park the chain rather than fit it on one regime. | A second regime with enough events is assembled and the association disappears. |

**Greatest assumption.** Developers re-underwrite on rate moves rather than ride fixed-rate project debt. (E3, load high)

**Kill test.** Financing is locked at fixed rates for the life of the projects under study.

## Insurance withdrawal reaches utility credit before it reaches capex

`chain:power:wildfire-insurance-to-utility-credit` · anchor `asset:credit:per-site-bond` · outcome `outcome:firm:capex-level` · ceiling **watch**

**Payer.** utility security holders absorb liability; ratepayers absorb the recovery

**Why now.** physical risk is repricing insurance in the same regions that hold the grid capex we study

| # | Link | Kind | Evidence | Load | Assumption | Kill test |
|---|---|---|---|---|---|---|
| 1 **greatest** | Insurers are withdrawing from wildfire-exposed regions or repricing sharply. | behavioral | E2 | high | Public utility commissions do not fully substitute for the insurance market. | State backstops fill the gap at no cost to utilities. |
| 2 | Uninsured liability risk raises the utility's cost of capital and narrows its financing capacity. | causal | E3 | high | Rating agencies treat the exposure as a credit event rather than a tail scenario. | Utility spreads do not move with insurance availability. |
| 3 | A financing-constrained utility slows grid capex exactly when the buildout needs it. | accounting | E3 | medium | Capex programs are financing-limited at the margin rather than pre-committed. | Capex plans stay intact through credit stress. |
| 4 | The chain is a watch item for this repo: the dates are hard to align and the exposure is jurisdiction-specific, and the kill tests need insurance data we do not hold. | associative | E4 | low | The honest disposition is to record the chain and name the data that would decide it. | Insurance withdrawal dates joined to utility spread events show no pattern. |

**Greatest assumption.** Public utility commissions do not fully substitute for the insurance market. (E2, load high)

**Kill test.** State backstops fill the gap at no cost to utilities.

## The salmon chain, graded: sea temperature to harvest to the index

`chain:salmon:temperature-to-index` · anchor `mechanism:capacity:constraint` · outcome `outcome:firm:revenue-level` · ceiling **watch**

**Payer.** integrated farmers with the best sites collect; feed costs and lice limits decide the margin

**Why now.** demonstration of the method on the captain's example, and an honest verdict on whether it belongs to this repo's venues

| # | Link | Kind | Evidence | Load | Assumption | Kill test |
|---|---|---|---|---|---|---|
| 1 **greatest** | Sea temperature drives farmed salmon growth rates and lice pressure, which together set harvest volumes. | causal | E2 | high | Temperature is the leading driver among biology, regulation and feed. | Harvest volumes follow regulatory lice limits and smolt release schedules with no temperature signal. |
| 2 | Wild catch and predator-prey dynamics move with the same ocean conditions, which is the captain's wider web. | causal | E3 | medium | The wild side is a separate supply channel rather than a substitute that stabilises price. | Wild catch and farmed supply offset each other in price. |
| 3 | Feed costs (soy, fishmeal, fish oil) set the margin against the harvest price. | accounting | E2 | high | Feed contracts reprice within the same horizon as the harvest signal. | Feed costs are locked long enough to be irrelevant at the trading horizon. |
| 4 | Demand is concentrated in Japanese sushi and US retail, where the cut and quality preferences decide which producer's fish clears at a premium. | behavioral | E3 | medium | Quality premia are producer-specific enough to separate margins. | The index price is a commodity price with no producer-level dispersion. |
| 5 | The instrument is Fish Pool futures or integrated farmer equity, and FX (NOK) sits between the harvest price and shareholder returns. | accounting | E2 | medium | Futures liquidity and basis allow expression at the sizes the signal would justify. | The contract is too illiquid to express the view net of costs. |
| 6 | Verdict for this repo: watch item. It is a real chain with a testable core, but it needs data this repo does not have, and no node of ours touches it except through method. | associative | E4 | low | The honest disposition is to record the grade and not pretend it is ours. | A tie to one of our existing nodes appears, for example a feed commodity shared with a complex we trade. |

**Greatest assumption.** Temperature is the leading driver among biology, regulation and feed. (E2, load high)

**Kill test.** Harvest volumes follow regulatory lice limits and smolt release schedules with no temperature signal.

