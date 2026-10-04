#!/usr/bin/env python3
"""Conceptual seed, part two: grid, materials, labour, sites and water."""
from __future__ import annotations

from conceptual_seed import F, I

# --------------------------------------------------------------------------------------- grid
F("force:grid:transformer-lead-time", "Transformer lead time", "quoted delivery time for large power and distribution transformers",
  "gates energization and prices scarcity into equipment", "supplier backlogs, order slot disclosures", "project developers and ratepayers")
F("force:grid:hvdc-lead-time", "HVDC lead time", "delivery time for converters, cables and ships",
  "gates long haul transfer", "converter and cable order books, vessel bookings", "transmission customers")
F("force:grid:switchgear-supply", "Switchgear supply", "medium and high voltage switchgear capacity",
  "gates substation completion", "supplier guidance, substation lead times", "developers")
F("force:grid:utility-capex-plan", "Utility capex plan", "approved and proposed utility capital programmes",
  "sets the order book for equipment and labour", "rate case filings, capital plans", "ratepayers")
F("force:grid:rate-case-lag", "Rate case lag", "the time between spending and recovering it",
  "creates a financing gap and political risk", "rate case calendars, interim rates", "utility shareholders")
F("force:grid:allowed-return", "Allowed return", "the regulated return on rate base",
  "sets the hurdle for regulated build", "rate case orders, ROE awards", "utility shareholders")
F("force:grid:interconnection-study-backlog", "Study backlog", "the volume of projects awaiting engineering studies",
  "delays the queue", "queue reports, study cycle times", "developers")
F("force:grid:wildfire-hardening", "Wildfire hardening", "spend forced by fire risk and liability",
  "competes with growth capex for the same equipment", "utility plans, regulatory directives", "ratepayers and insurers")

# --------------------------------------------------------------------------------------- materials
F("force:materials:goes-steel", "Grain oriented electrical steel", "the mill capacity for transformer core steel",
  "gates transformer output", "mill expansions, import licence data", "transformer makers")
F("force:materials:copper-concentrate", "Copper concentrate", "mine supply of copper units",
  "sets conductor cost and availability", "mine guidance, treatment charges", "cable and winding buyers")
F("force:materials:rare-earth-magnets", "Rare earth magnets", "sintered magnet capacity and export policy",
  "gates motors and generators", "export quotas, magnet plant announcements", "equipment makers")
F("force:materials:aluminium-conductor", "Aluminium conductor", "rod and conductor capacity",
  "sets cable cost and speed", "smelter and rod mill data, cable maker guidance", "cable buyers")
F("force:materials:silicon-carbide", "Silicon carbide", "substrate and device capacity",
  "gates efficient power conversion", "substrate capacity, device qualifications", "converter makers")
F("force:materials:graphite-anode", "Graphite anode", "synthetic and natural anode capacity",
  "gates battery cells", "anode plant announcements, export controls", "cell makers")
F("force:materials:coolant-chemistry", "Coolant chemistry", "refrigerants, dielectrics and treatment chemicals",
  "gates cooling design choices", "chemical supplier qualifications, PFAS rules", "cooling system buyers")
F("force:materials:nuclear-fuel-enrichment", "Enrichment capacity", "enrichment and fabrication capacity",
  "gates fuel for restarts and new builds", "enrichment contracts, government programmes", "reactor operators")

# --------------------------------------------------------------------------------------- labour
F("force:labor:construction-crews", "Construction crews", "skilled crews for industrial and power construction",
  "gates build rates and sets installed cost", "union hiring halls, project labour agreements", "project owners")
F("force:labor:electricians", "Electricians", "licensed electrical labour for substations and fitout",
  "gates energization and fitout", "apprenticeship registrations, wage data", "project owners")
F("force:labor:turbine-casters", "Turbine casters", "specialist foundry labour for turbine components",
  "gates turbine output", "foundry employment, casting lead times", "turbine makers")
F("force:labor:epc-backlog", "EPC backlog", "engineering procurement and construction order books",
  "reveals demand and gates delivery", "contractor disclosures", "project owners")
F("force:labor:union-wage-pressure", "Wage pressure", "wage escalation in the scarce trades",
  "pushes project cost and shifts margin", "wage settlements, project labour agreements", "project owners")

# --------------------------------------------------------------------------------------- sites
F("force:sites:land-permitting", "Land and permitting", "the time and risk of entitlements",
  "gates site start dates", "permit filings, planning agendas", "developers")
F("force:sites:community-opposition", "Community opposition", "organised local resistance to projects",
  "delays and sometimes kills sites", "planning hearings, litigation", "developers")
F("force:sites:water-rights", "Water rights", "the legal right to withdraw and discharge water",
  "gates evaporative cooling designs", "water permits, basin allocations", "site operators")
F("force:sites:fiber-routes", "Fiber routes", "the availability of long haul and metro fibre",
  "gates cluster placement and latency", "route maps, right of way filings", "network operators")
F("force:sites:latency-geography", "Latency geography", "where compute must sit to meet latency budgets",
  "constrains site choice and creates land premia", "latency maps, colocation footprints", "tenants")

# --------------------------------------------------------------------------------------- water
F("force:water:cooling-water-availability", "Cooling water availability", "local water supply for cooling",
  "gates site scale and technology", "basin data, withdrawal permits", "site operators")
F("force:water:evaporative-limits", "Evaporative limits", "rules capping consumptive water use",
  "pushes closed loop designs", "regulatory limits, drought measures", "site operators")
F("force:water:closed-loop-retrofit", "Closed loop retrofit", "retrofitting cooling to reduce water use",
  "raises capex and lowers water risk", "retrofit announcements, design disclosures", "site owners")
F("force:water:waste-heat-reuse", "Waste heat reuse", "selling or reusing rejected heat",
  "improves site economics and community standing", "district heating contracts, heat reuse projects", "site owners")

# grid -> grid, grid -> power, grid -> providers
I("force:grid:transformer-lead-time", "force:power:energization-delay", "gates",
  "No transformer means no energization, whatever the queue says.",
  "Transformer delivery precedes energization.",
  "The transformer is a true gate rather than a schedulable input.",
  "Sites energize without transformers or with substitutes.", lag="1-4q", load=5)
I("force:grid:transformer-lead-time", "force:grid:utility-capex-plan", "dampens",
  "Equipment scarcity forces plans to stretch and rephase.",
  "Plans are equipment constrained rather than budget constrained.",
  "Utilities cannot substitute equipment or buy second hand at scale.",
  "Plans accelerate while lead times lengthen.", lag="2-6q", load=4,
  signs={"shortage": -1, "buildout": -1, "overbuild": 1, "shakeout": 1, "second_wave": -1})
I("force:grid:transformer-lead-time", "force:materials:goes-steel", "reveals",
  "Transformer lead times are the surface read on core steel tightness.",
  "Lead times respond to steel availability rather than labour.",
  "Core steel is the binding transformer input.",
  "Lead times shorten while steel stays tight.", lag="1-2q", load=3)
I("force:grid:hvdc-lead-time", "force:power:merchant-power-price", "dampens",
  "Transfer capacity moves power between regions and flattens price spreads.",
  "The link is built and operated.",
  "Regional price differences exceed transfer cost.",
  "Spreads persist after the link operates.", lag="4-16q", load=3)
I("force:grid:switchgear-supply", "force:sites:land-permitting", "complements",
  "A permitted site still needs a substation to be usable.",
  "Substations are on the critical path to occupancy.",
  "Switchgear cannot be stockpiled far ahead of the design.",
  "Sites occupy while substations lag.", lag="1-3q", load=3)
I("force:grid:rate-case-lag", "force:grid:utility-capex-plan", "dampens",
  "A long lag to recovery makes utilities sequence spend carefully.",
  "Cash flow, not desire, governs the plan.",
  "Utilities cannot fund indefinite working capital gaps.",
  "Plans accelerate while recovery lags.", lag="2-6q", load=4)
I("force:grid:allowed-return", "force:grid:utility-capex-plan", "drives",
  "A higher allowed return makes more projects worth building.",
  "The project earns the allowed return on the spend.",
  "Rate base growth is the utility objective function.",
  "Capex plans shrink when allowed returns rise.", lag="2-6q", load=3)
I("force:grid:wildfire-hardening", "force:grid:utility-capex-plan", "crowds_out",
  "Hardening spend uses the same equipment and crews as growth.",
  "Both programmes draw on the same supply chain.",
  "Hardening is mandatory and cannot be deferred.",
  "Growth capex accelerates while hardening spend rises.", lag="2-6q", load=4)
I("force:grid:interconnection-study-backlog", "force:power:grid-operator-reform", "drives",
  "A visible backlog is the political trigger for reform.",
  "Backlog is measured and published.",
  "Regulators respond to documented delay.",
  "Reform is passed while backlogs fall.", lag="2-8q", load=2)
I("force:grid:transformer-lead-time", "force:providers:rental-spread", "drives",
  "Power delays keep the installed base scarce and spreads wide.",
  "Providers must energise to earn.",
  "Rental prices clear on availability.",
  "Spreads narrow while transformer delays run long.", lag="2-6q", load=4)

# materials -> grid, materials -> power, materials -> labour
I("force:materials:goes-steel", "force:grid:transformer-lead-time", "gates",
  "Core steel is the long pole in transformer output.",
  "Mills run near capacity and new lines take years.",
  "Core steel cannot be imported at scale under current duties.",
  "Lead times fall while steel capacity is flat.", lag="2-8q", load=4)
I("force:materials:copper-concentrate", "force:materials:aluminium-conductor", "substitutes",
  "Conductor designs trade copper for aluminium as prices diverge.",
  "Design codes permit aluminium in the relevant applications.",
  "Substitution is technically acceptable and persistent.",
  "Substitution reverses when the price gap narrows.", lag="1-4q", load=3)
I("force:materials:copper-concentrate", "force:grid:hvdc-lead-time", "drives",
  "Cable is a copper intensive, long lead item.",
  "Cable demand is incremental rather than reshuffled.",
  "Mine supply cannot respond inside the project window.",
  "Cable lead times fall while copper tightens.", lag="2-8q", load=3)
I("force:materials:rare-earth-magnets", "force:labor:turbine-casters", "complements",
  "Generators and turbines need magnets and castings together.",
  "Both inputs are needed for the same unit.",
  "Neither input has a fast substitute.",
  "Units ship with one input missing.", lag="1-4q", load=3)
I("force:materials:silicon-carbide", "force:grid:switchgear-supply", "substitutes",
  "SiC devices change converter and breaker designs.",
  "Qualification cycles complete and designs adopt the parts.",
  "Reliability in the field matches incumbent technology.",
  "Adoption stalls on qualification failures.", lag="4-12q", load=3)
I("force:materials:graphite-anode", "force:power:onsite-generation", "gates",
  "Batteries smooth on site generation and shift load.",
  "Storage is part of the on site design.",
  "Anode supply is the battery constraint.",
  "On site projects proceed without storage.", lag="1-4q", load=3)
I("force:materials:coolant-chemistry", "force:water:closed-loop-retrofit", "gates",
  "Closed loops need chemistries that survive high heat flux.",
  "Retrofit specifications depend on the coolant.",
  "The chemistry is available at industrial scale.",
  "Retrofits stall on fluid supply or rules.", lag="1-3q", load=3)
I("force:materials:nuclear-fuel-enrichment", "force:power:nuclear-ppa", "gates",
  "Firm nuclear power needs fuel contracts that reach years ahead.",
  "Enrichment capacity is contracted before restart.",
  "Fuel supply is not substitutable inside the restart window.",
  "Restarts proceed while fuel coverage is short.", lag="4-16q", load=4)
I("force:materials:goes-steel", "force:labor:turbine-casters", "competes_for",
  "Electrical steel and castings compete for the same industrial capacity and power.",
  "Both are made in heavy industrial clusters.",
  "Clusters cannot expand power and labour quickly.",
  "Both lines expand together without constraint.", lag="2-8q", load=2)

# labour -> grid, labour -> sites, labour -> providers
I("force:labor:construction-crews", "force:grid:utility-capex-plan", "gates",
  "Plans are only as fast as the crews that build them.",
  "Crews are the binding constraint rather than equipment.",
  "Crews cannot be imported or trained inside the plan window.",
  "Plans execute faster than crew availability allows.", lag="2-6q", load=4)
I("force:labor:electricians", "force:power:energization-delay", "gates",
  "Energization work needs licensed electricians in a narrow window.",
  "Fitout labour is the last gate before energization.",
  "The trade cannot be substituted by equipment.",
  "Sites energize faster than electrician availability allows.", lag="1-3q", load=4)
I("force:labor:turbine-casters", "force:power:gas-turbine-slot", "gates",
  "Casting capacity decides how many turbine slots become machines.",
  "Specialist castings are on the critical path.",
  "Casting capacity cannot be expanded quickly.",
  "Turbines ship at booked rates despite casting constraints.", lag="2-8q", load=4)
I("force:labor:union-wage-pressure", "force:labor:construction-crews", "dampens",
  "Higher wages attract crews but raise the cost of every project.",
  "Wage increases do attract labour into the trade.",
  "The labour supply responds to wages within the cycle.",
  "Wages rise and crew availability does not improve.", lag="1-4q", load=3)
I("force:labor:epc-backlog", "force:labor:construction-crews", "crowds_in",
  "A growing backlog pulls crews to the biggest projects.",
  "Backlog is real work rather than options.",
  "Crews move toward the highest bidder.",
  "Backlogs grow while crew supply comes free.", lag="1-4q", load=3,
  signs={"shortage": 1, "buildout": 1, "overbuild": -1, "shakeout": -1, "second_wave": 1})
I("force:labor:epc-backlog", "force:providers:capex-intensity", "reveals",
  "Contractor backlogs are the earliest public read on provider spend.",
  "Contractors book before providers report capex.",
  "Backlog converts to revenue rather than being cancelled.",
  "Backlogs build while provider capex falls.", lag="1-2q", load=3)

# sites -> grid, sites -> power, water -> sites
I("force:sites:land-permitting", "force:power:interconnection-queue", "delays",
  "A queue position without land is not a project.",
  "Sites must be entitled before they can be studied.",
  "Entitlement is on the critical path rather than parallel.",
  "Projects proceed to construction before entitlement.", lag="1-4q", load=3)
I("force:sites:community-opposition", "force:sites:land-permitting", "dampens",
  "Organised opposition converts permits into litigation.",
  "Opposition has standing in the process.",
  "Local politics can delay but not permanently block.",
  "Projects with active opposition proceed on schedule.", lag="2-8q", load=4)
I("force:sites:water-rights", "force:water:cooling-water-availability", "gates",
  "The permit is what makes the water usable.",
  "Water law binds before physics does.",
  "Rights are not transferable at the needed scale.",
  "Sites with water constraints run evaporative cooling anyway.", lag="1-4q", load=4)
I("force:sites:fiber-routes", "force:sites:latency-geography", "drives",
  "Fibre routes define which places can be close enough.",
  "Latency depends on path, not straight line distance.",
  "New routes are not built inside the site window.",
  "Sites are chosen without regard to route availability.", lag="2-6q", load=3)
I("force:sites:latency-geography", "force:providers:contracted-share", "drives",
  "Latency critical tenants sign long contracts near users.",
  "Tenants pay a premium for proximity.",
  "Proximity cannot be replicated elsewhere.",
  "Tenants accept remote sites for latency critical work.", lag="2-6q", load=3)
I("force:water:cooling-water-availability", "force:water:evaporative-limits", "drives",
  "Water stress triggers consumption rules.",
  "Local supply is the political trigger.",
  "Rules bind the site rather than being waived.",
  "Rules tighten while supply recovers.", lag="1-4q", load=3)
I("force:water:evaporative-limits", "force:water:closed-loop-retrofit", "drives",
  "Limits force the retrofit decision.",
  "Retrofit is permitted and supply constrained only by capital.",
  "Closed loop designs meet the limit at acceptable cost.",
  "Limits are imposed and no retrofit activity follows.", lag="1-4q", load=3)
I("force:water:closed-loop-retrofit", "force:providers:capex-intensity", "drives",
  "Retrofits add capex per megawatt on top of the base build.",
  "Retrofit spend is provider funded.",
  "The retrofit cannot be passed to the tenant in full.",
  "Retrofits are tenant funded and leave provider capex flat.", lag="2-6q", load=3)
I("force:water:waste-heat-reuse", "force:sites:community-opposition", "dampens",
  "Visible community benefit softens local resistance.",
  "The benefit is legible to the community.",
  "Opposition responds to material benefits rather than identity.",
  "Reuse projects do not change local approval.", lag="2-8q", load=2)
I("force:water:cooling-water-availability", "force:power:onsite-generation", "complements",
  "On site plants need cooling too, and change the water balance.",
  "The generation design includes cooling.",
  "On site plants are not air cooled where water is scarce.",
  "On site plants add water stress without any constraint.", lag="1-4q", load=2)
I("force:sites:community-opposition", "force:power:onsite-generation", "drives",
  "Opposition to grid build makes self generation attractive.",
  "Grid capacity is contested locally.",
  "Self generation avoids the contested permitting path.",
  "Opposition subsides and on site building continues.", lag="2-6q", load=3)
