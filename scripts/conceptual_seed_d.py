#!/usr/bin/env python3
"""Conceptual seed, part four: substitutions, moderators, cycle sign maps and the second order links."""
from __future__ import annotations

from conceptual_seed import A, I

# ------------------------------------------------------------------- substitutions inside the complex
I("force:power:nuclear-ppa", "force:power:gas-turbine-slot", "substitutes",
  "Firm nuclear contracts displace new gas for the same capacity need.",
  "Nuclear restarts or new builds clear their own permits.",
  "The nuclear tranche is additive supply rather than a reshuffle of existing output.",
  "Gas slots keep booking at the same rate while nuclear contracts grow.", lag="4-16q", load=3)
I("force:power:onsite-generation", "force:power:firm-capacity-scarcity", "substitutes",
  "Behind the meter supply removes load from the scarcity calculation.",
  "The load is genuinely islanded or contractually curtailable.",
  "On site capacity is not double counted as system capacity.",
  "Scarcity prices rise while self generation scales.", lag="2-6q", load=3)
I("force:materials:aluminium-conductor", "force:materials:copper-concentrate", "substitutes",
  "Conductor substitution changes the copper intensity per kilometre.",
  "Codes and designs accept aluminium for the application.",
  "Substitution is persistent rather than a temporary squeeze response.",
  "Copper intensity per kilometre is unchanged by the price gap.", lag="1-4q", load=3)
I("force:materials:silicon-carbide", "force:materials:graphite-anode", "complements",
  "Efficient conversion and storage arrive together in the same site designs.",
  "Designs include both conversion and storage.",
  "Neither component substitutes for the other.",
  "Sites add one without the other at scale.", lag="1-4q", load=2)
I("force:silicon:asic-substitution", "force:silicon:hbm-supply", "drives",
  "In house silicon consumes the same limited memory bits.",
  "ASICs use comparable memory content per unit of compute.",
  "Substitution shifts vendors rather than relieving the memory constraint.",
  "HBM tightness eases while ASIC volume grows.", lag="2-6q", load=3)
I("force:financing:vendor-financing", "force:financing:abs-capacity", "substitutes",
  "Vendor credit and securitisation are alternative ways to carry the receivable.",
  "Both channels are open to the same buyer.",
  "Buyers use the cheaper channel rather than both.",
  "Both channels deepen at the same time for the same buyer.", lag="1-3q", load=2)
I("force:sites:latency-geography", "force:sites:fiber-routes", "complements",
  "Latency requires a path, and paths follow fibre.",
  "Latency critical workloads dominate the site decision.",
  "Fibre routes cannot be built inside the decision window.",
  "Sites are placed for latency without regard to fibre availability.", lag="2-6q", load=3)

# ------------------------------------------------------------------- demand and providers
I("force:demand:token-volume", "force:providers:rental-spread", "drives",
  "Volume growth fills rented capacity before it fills new capacity.",
  "Installed capacity has spare utilisation.",
  "Providers can raise price on the installed base.",
  "Spreads fall while token volume grows.", lag="1-2q", load=3)
I("force:demand:consumer-apps", "force:providers:rental-spread", "amplifies",
  "Consumer bursts hit the same pools as enterprise workloads and price clears the peak.",
  "Consumer demand is bursty and shares capacity with paid workloads.",
  "Providers do not reserve capacity for one segment only.",
  "Consumer spikes leave rental prices unchanged.", lag="0-2q", load=2)
I("force:demand:enterprise-adoption", "force:providers:contracted-share", "drives",
  "Enterprise workloads want fixed prices and long terms.",
  "Enterprises are willing to sign multi year commitments.",
  "Providers prefer contracts to spot exposure.",
  "Contracted share stays flat while enterprise adoption grows.", lag="2-6q", load=3)
I("force:demand:training-scale", "force:providers:contracted-share", "dampens",
  "Training contracts are large but finite and renegotiated each generation.",
  "Training buyers keep optionality rather than locking capacity.",
  "Frontier scale changes fast enough that long contracts are unattractive.",
  "Training contracts lengthen while scale keeps changing.", lag="1-4q", load=3)
I("force:demand:sovereign-ai", "force:providers:rental-spread", "dampens",
  "Sovereign buyers build rather than rent at scale.",
  "Programmes fund their own capacity.",
  "Sovereign demand is additive rather than rented.",
  "Sovereign programmes rent at scale from listed providers.", lag="4-12m", load=2)
I("force:demand:model-efficiency", "force:providers:rental-spread", "dampens",
  "Cheaper tokens per watt reduce capacity per unit of output.",
  "Efficiency converts into lower capacity needs rather than more usage.",
  "Elasticity does not absorb the efficiency gain inside the window.",
  "Spreads hold while efficiency improves sharply.", lag="2-8q", load=4)

# ------------------------------------------------------------------- silicon and providers
I("force:silicon:accelerator-lead-time", "force:providers:capex-intensity", "drives",
  "Long lead times force prepayment and inventory, both of which hit the capex line.",
  "Vendors require commitments and deposits.",
  "Prepayment is treated as capex rather than working capital.",
  "Capex intensity falls while lead times lengthen.", lag="1-2q", load=3)
I("force:silicon:accelerator-resale-value", "force:providers:neocloud-funding", "gates",
  "Lenders underwrite the fleet against residual value.",
  "Residual value is the collateral in the structure.",
  "Residuals are observable and enforceable.",
  "Funding terms are unchanged by residual values.", lag="1-3q", load=4)
I("force:silicon:export-controls", "force:providers:rental-spread", "drives",
  "Restricted markets buy through cloud region workarounds, tightening available supply elsewhere.",
  "Workarounds exist and are used.",
  "The workaround demand is served from the same pools.",
  "Restricted demand drains without affecting rental prices.", lag="1-3q", load=3)
I("force:silicon:node-capacity", "force:silicon:accelerator-lead-time", "gates",
  "Wafers gate finished parts when packaging is available.",
  "Wafer capacity is the tighter of the two constraints in the window.",
  "Node capacity cannot be reallocated quickly from other products.",
  "Lead times fall while node utilisation is full.", lag="2-6q", load=3)
I("force:silicon:networking-optics", "force:providers:capex-intensity", "drives",
  "Cluster networking is a rising share of the bill of materials.",
  "Clusters scale in port count faster than in compute per node.",
  "Optics are provider funded rather than tenant funded.",
  "Networking cost per unit of compute falls.", lag="1-3q", load=2)

# ------------------------------------------------------------------- power and providers
I("force:power:merchant-power-price", "force:providers:revenue-per-mw", "dampens",
  "Power cost is a direct deduction from the revenue a megawatt can earn.",
  "Provider power contracts are floating rather than fixed.",
  "Providers cannot pass the full move to tenants in the short run.",
  "Revenue per megawatt is unchanged by power prices.", lag="1-3q", load=4)
I("force:power:capacity-auction", "force:providers:contracted-share", "prices",
  "Capacity revenue is a contracted stream that can be sold forward.",
  "Provider generation is capacity accredited.",
  "The stream is financeable.",
  "Capacity revenue is excluded from contracted share by the market.", lag="1-2q", load=2)
I("force:power:grid-operator-reform", "force:providers:rental-spread", "dampens",
  "Faster connections add capacity and narrow spreads.",
  "Reform delivers megawatts inside the cycle.",
  "Added capacity is not offset by new queue entries in the same window.",
  "Spreads stay wide while connections accelerate.", lag="4-12m", load=3)

# ------------------------------------------------------------------- cycles sign maps
I("force:cycles:capacity-overbuild", "force:power:gas-turbine-slot", "dampens",
  "Cancellations free turbine slots for the next buyer.",
  "Slots are cancellable with penalty.",
  "Cancelled slots are re-marketable.",
  "Slot queues lengthen through an overbuild.", lag="2-6q", load=3,
  signs={"buildout": 1, "overbuild": -1, "shakeout": -1, "second_wave": 1})
I("force:cycles:capacity-overbuild", "force:grid:utility-capex-plan", "dampens",
  "Excess capacity defers the next wave of grid spend.",
  "Utilities respond to load forecasts that fall with cancellations.",
  "Load forecasts are revised rather than sticky.",
  "Capex plans accelerate through an overbuild.", lag="2-8q", load=4,
  signs={"buildout": 1, "overbuild": -1, "shakeout": -1, "second_wave": 1})
I("force:cycles:price-collapse", "force:providers:neocloud-funding", "dampens",
  "Funding closes when the price signal breaks.",
  "Lenders and equity are return sensitive.",
  "Distressed terms do not attract new capacity in the same window.",
  "Funding opens wider during a price collapse.", lag="1-3q", load=4)
I("force:cycles:shakeout-consolidation", "force:labor:epc-backlog", "dampens",
  "Consolidation shrinks the order book that kept crews busy.",
  "Cancellations exceed new awards.",
  "Contractors release crews rather than hoard them.",
  "Backlogs grow through the shakeout.", lag="2-6q", load=3)
I("force:cycles:second-wave-demand", "force:labor:construction-crews", "crowds_in",
  "The second wave competes for the same crews at a lower price point.",
  "The cost base is lower but the labour pool did not grow.",
  "Crews return from other sectors.",
  "Crew scarcity is absent in the second wave.", lag="4-12q", load=3)
I("force:cycles:demand-shock", "force:sites:land-permitting", "drives",
  "Demand converts into site acquisition and entitlements.",
  "Capital exists to buy land ahead of demand.",
  "Entitlement queues are the binding step.",
  "Site acquisition is flat while demand shocks upward.", lag="1-4q", load=2)

# ------------------------------------------------------------------- financing and the physical chain
I("force:financing:policy-rate", "force:grid:utility-capex-plan", "dampens",
  "Higher rates raise the revenue requirement and the political resistance to it.",
  "Rate cases pass the cost of capital through to consumers.",
  "Political tolerance for bill increases is finite.",
  "Capex plans grow as rates rise.", lag="2-6q", load=3)
I("force:financing:credit-spreads", "force:power:onsite-generation", "dampens",
  "Expensive credit kills the marginal self generation project first.",
  "On site projects are project financed.",
  "Balance sheet funding is not available instead.",
  "Self generation accelerates through a credit shock.", lag="2-6q", load=3)
I("force:financing:reit-cost-of-capital", "force:providers:contracted-share", "reveals",
  "Cheap REIT capital is deployed against long leases, so the mix shifts with funding.",
  "REITs compete for the same tenants as providers.",
  "Funding cost decides who wins the tenant.",
  "The funding mix is unrelated to the contract mix.", lag="2-6q", load=3)
I("force:financing:abs-capacity", "force:cycles:capacity-overbuild", "amplifies",
  "Securitisation lets the marginal builder keep building past the point of sense.",
  "Deals clear on contracted cash flows regardless of market-wide capacity.",
  "Rating agencies do not aggregate sector exposure fast enough.",
  "Issuance closes before the overbuild arrives.", lag="2-8q", load=4)

# ------------------------------------------------------------------- policy and the physical chain
I("force:policy:tariffs-equipment", "force:materials:aluminium-conductor", "drives",
  "Tariffs on conductor and rod redirect sourcing and cost.",
  "Tariffs bind on the imported alternative.",
  "Domestic supply is not instantly substitutable.",
  "Sourcing and cost are unchanged by the tariff.", lag="1-4q", load=3)
I("force:policy:data-sovereignty", "force:power:onsite-generation", "drives",
  "Localisation forces capacity into jurisdictions with weaker grids.",
  "The jurisdiction lacks grid headroom.",
  "On site generation is permitted locally.",
  "Localised capacity waits for the grid without building.", lag="4-12m", load=3)
I("force:policy:antitrust-scrutiny", "force:providers:tenant-concentration", "reveals",
  "Scrutiny makes the largest contracts and their terms public.",
  "Inquiries produce disclosures.",
  "The market reads the contracts through the inquiry.",
  "Contract terms are unaffected by scrutiny.", lag="2-8q", load=2)
I("force:policy:energy-price-caps", "force:power:onsite-generation", "drives",
  "Caps push large loads to build rather than buy.",
  "Caps are binding and durable.",
  "Self generation is permitted.",
  "Loads keep buying capped power without building.", lag="1-4q", load=3)
I("force:policy:grid-permitting-reform", "force:grid:transformer-lead-time", "reveals",
  "If permits shorten and lead times do not, the bottleneck was never permits.",
  "Both clocks are measured.",
  "Equipment lead times are independent of permitting.",
  "Lead times shorten when permits shorten.", lag="4-12m", load=3)

# ------------------------------------------------------------------- micro and the physical chain
I("force:micro:forced-deleveraging", "force:silicon:accelerator-resale-value", "drives",
  "Forced selling in related equities and private marks moves the reference prices for residuals.",
  "Residual values are marked against market references.",
  "Marks adjust faster than disposal prices.",
  "Residual marks are unchanged by forced selling.", lag="0-5d", load=2)
I("force:micro:options-positioning", "force:providers:equity-multiple", "dampens",
  "Dealer hedging absorbs buying pressure and flattens multiple expansion.",
  "Positioning is concentrated at strikes near spot.",
  "Dealers hedge rather than warehouse.",
  "Multiple expansion is unaffected by option positioning.", lag="0-5d", load=2)
I("force:micro:index-inclusion-flows", "force:providers:neocloud-funding", "drives",
  "Index inclusion lowers the cost of equity for the included name.",
  "The name is included in a major index.",
  "Passive demand is price insensitive at the margin.",
  "Funding access is unchanged by index events.", lag="1-10d", load=2)
I("force:micro:depth-liquidity", "force:providers:equity-multiple", "bounds",
  "Thin books make the same fundamental news produce larger multiple moves.",
  "Depth is thin relative to the news flow.",
  "The marginal price setter is small relative to the float.",
  "Multiple moves are independent of depth.", lag="0-5d", load=2)

# ------------------------------------------------------------------- moderators (second order links)
I("force:power:energization-delay", "force:providers:capex-intensity", "conditions",
  "When power is gated, the spend is only in the money if the delay is shorter than the demand curve.",
  "Delays are long relative to the demand cycle.",
  "Demand persists past the delay window rather than moving to another site.",
  "Providers keep spending into delays that outlast the demand.", lag="2-6q", load=4)
I("force:demand:inference-price-elasticity", "force:providers:rental-spread", "conditions",
  "Elasticity is the moderator that decides whether rental prices fall on new supply.",
  "Elasticity is above one and new supply arrives.",
  "New supply serves elastic demand rather than displacing the installed base.",
  "Prices collapse on new supply even with elastic demand.", lag="2-6q", load=4)
I("force:financing:policy-rate", "force:providers:capex-intensity", "conditions",
  "Rate direction decides whether intensity is punished or ignored.",
  "The measurement window spans a rate move.",
  "Multiple compression dominates the capacity reward in the window.",
  "Intensity is rewarded in every rate regime.", lag="2-6q", load=4)
I("force:micro:depth-liquidity", "force:cycles:capital-inflow", "conditions",
  "Thin public markets cannot fund the cycle at the needed scale, so private capital decides.",
  "Equity issuance exceeds what the book absorbs.",
  "Private and public capital are substitutes.",
  "The cycle funds itself entirely in public markets regardless of depth.", lag="1-4q", load=3)
I("force:labor:union-wage-pressure", "force:grid:allowed-return", "conditions",
  "Wage pressure only changes behaviour when the allowed return does not cover it.",
  "Rate cases lag wage settlements.",
  "Regulators do not pre-emptively raise allowed returns.",
  "Utilities absorb wage increases without re-filing.", lag="2-6q", load=3)
I("force:materials:goes-steel", "force:policy:tariffs-equipment", "conditions",
  "Steel scarcity matters more where tariffs close the import valve.",
  "Tariffs bind on core steel imports.",
  "Domestic mill capacity cannot respond inside the window.",
  "Lead times fall after tariffs despite tight steel.", lag="1-4q", load=3)

# ------------------------------------------------------------------- more assumptions
A("elasticity-is-the-moderator", "The sign of the rental spread response to new supply depends on elasticity.",
  "Compare new supply windows against rental price changes split by demand growth.",
  "Rental prices fall on new supply in every elasticity regime.",
  "force:demand:inference-price-elasticity", "provider spreads and the capex absorption chain", load=4)
A("rate-regime-decides-intensity", "The punishment of capex intensity depends on the rate direction in the window.",
  "Split the intensity panel by rate direction and compare the sign.",
  "Intensity is charged identically across rate directions.",
  "force:financing:policy-rate", "the intensity object and its segment cuts", load=4)
A("permits-versus-equipment", "Permitting reform only helps if permits were the binding clock.",
  "Compare permit timelines against equipment lead times after reform.",
  "Lead times fall when permits fall.",
  "force:policy:grid-permitting-reform", "the power chain and utility plans", load=3)
A("self-build-threat-is-live", "The self build threat from large tenants is live at every negotiation.",
  "Compare announced tenant capacity against contract signings.",
  "Tenants sign long contracts while building nothing.",
  "force:providers:tenant-concentration", "provider spreads, revenue per megawatt and the funding chain", load=4)
A("public-markets-cannot-fund-it", "The cycle cannot be funded by public equity alone at this scale.",
  "Compare issuance against the capital needed for announced capacity.",
  "Issuance covers the announced build.",
  "force:micro:depth-liquidity", "financing chain and cycle sign map", load=3)
