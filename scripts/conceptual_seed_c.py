#!/usr/bin/env python3
"""Conceptual seed, part three: financing, policy, providers, cycles, micro, the chains and assumptions."""
from __future__ import annotations

from conceptual_seed import A, C, F, I

# --------------------------------------------------------------------------------------- financing
F("force:financing:policy-rate", "Policy rate", "the risk free rate that discounts every project",
  "sets the hurdle and the multiple", "central bank path, forward curve", "all capital owners")
F("force:financing:credit-spreads", "Credit spreads", "the price of corporate and project credit",
  "sets funding cost and deal access", "index spreads, new issue concessions", "borrowers")
F("force:financing:abs-capacity", "Securitisation capacity", "the depth of demand for data centre and equipment backed deals",
  "converts contracted cash flows into upfront capital", "ABS issuance, spread levels, rating actions", "sponsors")
F("force:financing:vendor-financing", "Vendor financing", "supplier provided credit for equipment",
  "accelerates purchases and hides end demand risk", "vendor financing disclosures, terms", "vendors and buyers")
F("force:financing:reit-cost-of-capital", "REIT cost of capital", "the equity and debt cost for listed landlords",
  "decides who can build at a spread", "REIT multiples, ATM issuance", "REIT shareholders")
F("force:financing:depreciation-schedule", "Depreciation schedule", "the useful life assumption for assets in place",
  "shifts reported earnings and loan covenants", "annual report notes, policy changes", "shareholders and lenders")
F("force:financing:lease-accounting", "Lease accounting", "how capacity commitments appear on balance sheets",
  "shifts demand between structure and disclosure", "lease notes, accounting changes", "issuers and analysts")

# --------------------------------------------------------------------------------------- policy
F("force:policy:investment-credits", "Investment credits", "tax credits and subsidies for build",
  "raises after tax returns and pulls build forward", "legislation, guidance, qualifying lists", "taxpayers")
F("force:policy:tariffs-equipment", "Equipment tariffs", "duties on imported equipment and materials",
  "raises cost and reshapes sourcing", "tariff schedules, exclusion decisions", "buyers")
F("force:policy:antitrust-scrutiny", "Antitrust scrutiny", "regulatory attention on vertical integration and deals",
  "slows consolidation and changes structuring", "complaints, inquiries, remedies", "shareholders")
F("force:policy:grid-permitting-reform", "Permitting reform", "statutory change to siting and approval timelines",
  "compresses or extends project clocks", "bill text, agency rules", "developers")
F("force:policy:energy-price-caps", "Energy price caps", "administrative limits on power prices",
  "caps merchant upside and protects loads", "market rules, emergency orders", "merchant generators")
F("force:policy:data-sovereignty", "Data sovereignty", "rules localising data and compute",
  "fragments demand into national pools", "statutes, certification regimes", "multinationals")

# --------------------------------------------------------------------------------------- providers
F("force:providers:rental-spread", "Rental spread", "the price of compute capacity against its cost",
  "sets provider profit and entry", "contract prices, spot rates", "capacity owners")
F("force:providers:capex-intensity", "Capex intensity", "capex as a share of revenue",
  "sets the future depreciation and funding need", "SEC capex and revenue", "shareholders")
F("force:providers:tenant-concentration", "Tenant concentration", "share of revenue from the largest tenants",
  "shifts pricing power to tenants", "disclosures, contract filings", "providers")
F("force:providers:contracted-share", "Contracted share", "share of capacity under long contracts",
  "stabilises cash flow and limits upside", "disclosures, lease schedules", "providers")
F("force:providers:revenue-per-mw", "Revenue per megawatt", "revenue per unit of committed capacity",
  "the bridge between power and profit", "segment disclosures, capacity announcements", "providers")
F("force:providers:hyperscaler-roic-discipline", "ROIC discipline", "capital discipline inside the largest buyers",
  "caps build when returns wobble", "earnings commentary, capex guidance", "shareholders")
F("force:providers:neocloud-funding", "Neocloud funding", "the funding access of dedicated GPU lessors",
  "decides whether independent capacity exists", "raises, ABS, vendor terms", "neocloud shareholders")
F("force:providers:equity-multiple", "Equity multiple", "the valuation applied to provider earnings",
  "translates cash flow into price", "multiples, consensus revisions", "shareholders")

# --------------------------------------------------------------------------------------- cycles
F("force:cycles:demand-shock", "Demand shock", "a step change in demand for the output",
  "starts the cycle", "order books, utilisation", "all participants")
F("force:cycles:capital-inflow", "Capital inflow", "capital attracted by the shock",
  "funds the build", "issuance, capex announcements, deal counts", "investors")
F("force:cycles:capacity-overbuild", "Overbuild", "capacity added beyond clearing demand",
  "collapses price and margin", "utilisation, price levels, vacancy", "incumbent owners")
F("force:cycles:price-collapse", "Price collapse", "the adjustment phase",
  "destroys marginal participants", "prices, bankruptcies", "equity holders")
F("force:cycles:shakeout-consolidation", "Shakeout and consolidation", "survivors absorb distressed assets",
  "resets ownership and cost base", "restructurings, M&A", "creditors and survivors")
F("force:cycles:second-wave-demand", "Second wave demand", "the new demand that arrives on the leaner cost base",
  "restarts the cycle at a lower price point", "new categories, utilisation recovery", "survivors")

# --------------------------------------------------------------------------------------- micro
F("force:micro:index-inclusion-flows", "Index flows", "passive flows around index events",
  "moves price without information", "index calendars, volume spikes", "index funds")
F("force:micro:short-interest-squeeze", "Short squeeze", "positioning driven moves",
  "amplifies moves beyond fundamentals", "borrow data, short interest", "short sellers")
F("force:micro:options-positioning", "Options positioning", "dealer hedging of listed options",
  "dampens or amplifies moves by strike", "open interest, gamma profiles", "dealers")
F("force:micro:forced-deleveraging", "Forced deleveraging", "margin driven selling",
  "creates short dislocations", "funding, open interest, liquidations", "levered accounts")
F("force:micro:depth-liquidity", "Depth and liquidity", "the size the market absorbs at a price",
  "bounds what a strategy can carry", "order book depth, spreads", "market makers")

# financing -> providers, financing -> cycles, financing -> grid
I("force:financing:policy-rate", "force:providers:equity-multiple", "re_rates",
  "Higher rates compress the multiple on the same cash flow.",
  "Duration of the cash flows exceeds the rate move horizon.",
  "The multiple is primarily a discount rate story rather than a growth story.",
  "Multiples expand while rates rise.", lag="1-3q", load=3)
I("force:financing:credit-spreads", "force:financing:abs-capacity", "dampens",
  "Wider spreads shut the securitisation window and slow the build.",
  "Deals clear on spread rather than on structure.",
  "Securitisation is a marginal funding source rather than the core one.",
  "Issuance continues at the same pace through a spread shock.", lag="1-2q", load=3)
I("force:financing:abs-capacity", "force:providers:neocloud-funding", "finances",
  "Securitisation lets lessors fund fleets against contracted cash flows.",
  "Contracts are assignable and rated.",
  "Investors accept equipment and contract risk at the offered spread.",
  "Lessors fund only with equity and their growth stalls.", lag="2-6q", load=4)
I("force:financing:vendor-financing", "force:silicon:accelerator-lead-time", "reveals",
  "Vendor credit terms are a read on end demand strength.",
  "Vendors use credit to clear inventory.",
  "Vendor financing expands when demand softens, not when it surges.",
  "Terms tighten while lead times lengthen.", lag="1-2q", load=4)
I("force:financing:reit-cost-of-capital", "force:sites:land-permitting", "drives",
  "Cheap capital lets landlords buy sites ahead of demand and entitle them.",
  "Development is funded on the balance sheet.",
  "Landlords can carry entitled land through the permitting period.",
  "Site acquisition stops when cost of capital rises.", lag="2-6q", load=3)
I("force:financing:depreciation-schedule", "force:providers:equity-multiple", "drives",
  "The schedule decides reported earnings for the same cash flow.",
  "The market prices reported earnings rather than cash flow at the margin.",
  "Depreciation policy is not fully transparent to the market.",
  "Multiples are unchanged by depreciation policy changes.", lag="1-2q", load=4)
I("force:financing:lease-accounting", "force:providers:contracted-share", "reveals",
  "Accounting decides what counts as contracted revenue and committed cost.",
  "Leases are material enough to change the reported picture.",
  "Disclosure is comparable across issuers.",
  "Reported contracted share moves with accounting rather than contracts.", lag="1-2q", load=3)
I("force:financing:policy-rate", "force:cycles:capital-inflow", "dampens",
  "Cheap money feeds the cycle; expensive money cuts the flow.",
  "Credit conditions bind on marginal projects.",
  "The cycle is funding driven rather than demand driven at the margin.",
  "Capital inflow accelerates while rates rise.", lag="1-4q", load=3,
  signs={"shortage": 1, "buildout": 1, "overbuild": -1, "shakeout": -1, "second_wave": 1})
I("force:financing:credit-spreads", "force:cycles:price-collapse", "accelerates",
  "Spread widening forces the marginal owner to sell into weakness.",
  "Leverage is high enough that refinancing matters.",
  "Lenders mark and manage exposure actively.",
  "Spread widening has no effect on asset sales.", lag="1-2q", load=4)

# policy -> power, policy -> grid, policy -> providers, policy -> cycles
I("force:policy:investment-credits", "force:grid:utility-capex-plan", "accelerates",
  "Credits pull spending forward into the qualifying window.",
  "Projects qualify and can be placed in service in time.",
  "The credit is a marginal subsidy rather than the only reason.",
  "Credits are enacted and no acceleration follows.", lag="2-6q", load=3,
  signs={"shortage": 1, "buildout": 1, "overbuild": -1, "shakeout": -1, "second_wave": 1})
I("force:policy:tariffs-equipment", "force:grid:transformer-lead-time", "drives",
  "Tariffs on transformers and steel raise cost and stretch delivery.",
  "Tariffs bind on the imported alternative.",
  "Domestic supply cannot replace imports inside the window.",
  "Lead times fall while tariffs rise.", lag="1-4q", load=3)
I("force:policy:grid-permitting-reform", "force:grid:interconnection-study-backlog", "dampens",
  "Reform can compress the study and approval clock.",
  "Reform binds on the binding step.",
  "Agency capacity exists to implement the change.",
  "Clocks are unchanged after reform takes effect.", lag="4-12m", load=3)
I("force:policy:energy-price-caps", "force:power:merchant-power-price", "dampens",
  "Caps remove the scarcity signal that would attract generation.",
  "Caps bind in scarcity hours.",
  "Merchant revenue is the entry signal.",
  "Entry continues while caps are binding.", lag="1-4q", load=4)
I("force:policy:data-sovereignty", "force:providers:contracted-share", "drives",
  "Localisation mandates create long sovereign contracts.",
  "Compliance requires in country capacity.",
  "Providers can serve the mandate at a return.",
  "Sovereign contracts are announced and not signed.", lag="4-12m", load=3)
I("force:policy:antitrust-scrutiny", "force:cycles:shakeout-consolidation", "dampens",
  "Scrutiny slows consolidation exactly when it is cheapest.",
  "Deals need clearance in the relevant jurisdictions.",
  "Distressed assets cannot be carved out without review.",
  "Consolidation proceeds unimpeded during scrutiny.", lag="4-12m", load=3)
I("force:policy:investment-credits", "force:cycles:capital-inflow", "amplifies",
  "Subsidies raise the return that attracts capital.",
  "The credit flows to the marginal project.",
  "Capital is responsive to after tax returns.",
  "Capital flows in without credits.", lag="2-6q", load=3)

# providers -> providers, providers -> equity, providers -> cycles
I("force:providers:rental-spread", "force:providers:capex-intensity", "drives",
  "Wide spreads justify more spend on capacity.",
  "The spread is expected to persist past the payback.",
  "Providers reinvest retained spread rather than returning it.",
  "Spreads widen and spending falls.", lag="1-3q", load=3,
  signs={"shortage": 1, "buildout": 1, "overbuild": -1, "shakeout": 1, "second_wave": 1})
I("force:providers:capex-intensity", "force:providers:equity-multiple", "dampens",
  "Spending ahead of revenue compresses near term earnings and multiples.",
  "Depreciation and interest land inside the measurement window.",
  "The market charges near term earnings rather than rewarding capacity.",
  "Multiples rise with intensity, as the asset growth literature once implied.", lag="1-2q", load=4,
  signs={"shortage": 1, "buildout": -1, "overbuild": -1, "shakeout": -1, "second_wave": 1})
I("force:providers:tenant-concentration", "force:providers:rental-spread", "dampens",
  "A few large tenants set price and terms.",
  "Tenants can threaten to self build.",
  "Concentration is durable rather than temporary.",
  "Spreads widen while concentration rises.", lag="2-6q", load=4)
I("force:providers:contracted-share", "force:financing:abs-capacity", "drives",
  "Contracted cash flows are what makes a deal financeable.",
  "Contracts are long enough to cover the debt tenor.",
  "Investors price contract quality rather than counterparty identity.",
  "Deals fund fully on merchant exposure.", lag="1-3q", load=3)
I("force:providers:revenue-per-mw", "force:providers:equity-multiple", "drives",
  "The market prices the cash flow per unit of capacity.",
  "Capacity data is disclosed consistently.",
  "Revenue per megawatt is the cleanest read of pricing power.",
  "Multiples track total revenue while revenue per megawatt falls.", lag="1-3q", load=3)
I("force:providers:hyperscaler-roic-discipline", "force:providers:capex-intensity", "dampens",
  "Discipline shows up as slower intensity growth.",
  "Buyers have genuine alternatives to deploying capital.",
  "Discipline survives competitive pressure.",
  "Intensity keeps rising through a stated discipline phase.", lag="2-6q", load=4,
  signs={"shortage": -1, "buildout": -1, "overbuild": 1, "shakeout": 1, "second_wave": -1})
I("force:providers:neocloud-funding", "force:providers:rental-spread", "dampens",
  "New independent capacity competes the spread down.",
  "Capacity arrives in the same demand window.",
  "Neocloud capacity is price competitive for the same workloads.",
  "Spreads stay wide while independent capacity scales.", lag="2-6q", load=3,
  signs={"shortage": 1, "buildout": 1, "overbuild": -1, "shakeout": -1, "second_wave": 1})
I("force:providers:equity-multiple", "force:providers:neocloud-funding", "drives",
  "A higher multiple is cheaper equity and easier funding.",
  "Equity issuance is a live funding channel.",
  "Management issues into strength.",
  "Raises stop while multiples rise.", lag="1-3q", load=3)
I("force:providers:capex-intensity", "force:providers:tenant-concentration", "conditions",
  "Intensity funded on balance sheet pushes providers toward fewer, larger tenants.",
  "Balance sheet funding requires anchor contracts.",
  "Anchor contracts are compatible with the tenant base.",
  "Intensity rises while the tenant base diversifies.", lag="2-6q", load=2)

# cycles -> everything
I("force:cycles:demand-shock", "force:cycles:capital-inflow", "drives",
  "A visible shock pulls capital into the theme.",
  "The shock is legible to capital markets.",
  "Capital chases the theme rather than the asset.",
  "Capital stays out while the shock is obvious.", lag="1-3q", load=3)
I("force:cycles:capital-inflow", "force:cycles:capacity-overbuild", "drives",
  "Funded capacity gets built, and it arrives in herds.",
  "Capital converts to physical capacity within the cycle.",
  "Builders cannot coordinate to stop at demand.",
  "Capacity additions track demand without overshoot.", lag="2-8q", load=4)
I("force:cycles:capacity-overbuild", "force:cycles:price-collapse", "drives",
  "Excess capacity clears at prices below full cost.",
  "Demand does not grow into the new capacity in time.",
  "Supply is price inelastic downward.",
  "Prices hold while utilisation falls.", lag="1-4q", load=4)
I("force:cycles:price-collapse", "force:cycles:shakeout-consolidation", "drives",
  "Distress transfers assets to the strongest balance sheets.",
  "Leverage exists to force sales.",
  "Buyers have capital and conviction at the bottom.",
  "Distress appears with no consolidation.", lag="2-8q", load=4)
I("force:cycles:shakeout-consolidation", "force:cycles:second-wave-demand", "drives",
  "The leaner cost base makes new demand profitable.",
  "Demand persists across the cycle.",
  "The surviving cost structure is genuinely lower.",
  "Second wave demand arrives at the old cost base.", lag="4-12q", load=3)
I("force:cycles:second-wave-demand", "force:providers:rental-spread", "drives",
  "The second wave tightens the market again from a lower base.",
  "Capacity was retired or absorbed during the shakeout.",
  "Demand growth outpaces the remaining capacity.",
  "Spreads stay depressed into the second wave.", lag="4-12q", load=3,
  signs={"shakeout": -1, "second_wave": 1})
I("force:cycles:capacity-overbuild", "force:micro:short-interest-squeeze", "amplifies",
  "The crowded short side exists precisely in the overbuild fear.",
  "Positioning data shows crowding.",
  "Fundamentals and positioning diverge enough to squeeze.",
  "No squeeze occurs despite crowding.", lag="0-1q", load=2)

# micro -> micro, micro -> providers, micro -> cycles
I("force:micro:forced-deleveraging", "force:micro:depth-liquidity", "drives",
  "Forced selling consumes resting depth and widens spreads.",
  "The forced account is large relative to the book.",
  "Depth does not replenish inside the window.",
  "Spreads tighten during forced selling.", lag="minutes", load=3,
  evidence="E2")
I("force:micro:depth-liquidity", "force:micro:forced-deleveraging", "reveals",
  "Depth is the capacity limit that turns a shock into a dislocation.",
  "Depth is measured at the moment it matters.",
  "Displayed depth is a usable estimate of executable size.",
  "Deep markets dislocate as much as thin ones.", lag="minutes", load=3)
I("force:micro:options-positioning", "force:micro:depth-liquidity", "conditions",
  "Dealer hedging adds or removes depth depending on the strike structure.",
  "Dealer gamma has the same sign as price moves.",
  "Hedging flows are visible in depth rather than hidden in dark venues.",
  "Depth is unchanged by option positioning.", lag="0-5d", load=3)
I("force:micro:index-inclusion-flows", "force:micro:depth-liquidity", "drives",
  "Passive flows are mechanical and price insensitive.",
  "Inclusion dates are known and flows are predictable.",
  "Index funds trade the close regardless of price.",
  "Inclusion has no volume or price effect.", lag="1-10d", load=2)
I("force:micro:short-interest-squeeze", "force:providers:equity-multiple", "drives",
  "Squeezes move the multiple without changing the cash flow.",
  "Short interest is high enough to move price.",
  "Fundamentals do not resolve inside the squeeze window.",
  "Multiples move with cash flow only.", lag="1-20d", load=2)
I("force:micro:forced-deleveraging", "force:micro:reversion-candidate", "drives",
  "Dislocations created by forced flow can revert once the flow ends.",
  "The forced seller is finite and identifiable after the fact.",
  "The dislocation is larger than the cost of taking the other side.",
  "Dislocations continue without reversal.",
  lag="minutes", load=4, signs={"shortage": 1, "buildout": 1, "overbuild": -1}, evidence="E2")
F("force:micro:reversion-candidate", "Reversion candidate", "the post flow reversal available at low latency",
  "provides the entry if it exists", "post event paths, depth at the event", "the taker")

# --------------------------------------------------------------------------------------- chains
C("capex-absorption", "Capex absorption: spending ahead of revenue is charged",
  ["force:providers:rental-spread", "force:providers:capex-intensity", "force:financing:depreciation-schedule",
   "force:providers:equity-multiple"],
  "Wide rental spreads invite capacity spending; the spending arrives as depreciation before it arrives as "
  "revenue, and the market charges the gap in the multiple first and the earnings later.",
  "Depreciation and interest land inside the measurement window rather than after the revenue arrives.",
  "Provider capex guides rise while the equity multiple holds and then falls three to six months later.",
  {"shortage": 1, "buildout": -1, "overbuild": -1, "shakeout": -1, "second_wave": 1})
C("power-chain", "Power chain: the queue decides who earns",
  ["force:power:interconnection-queue", "force:power:energization-delay", "force:providers:rental-spread",
   "force:providers:capex-intensity", "force:grid:transformer-lead-time"],
  "The queue and then the transformer gate energization; while gates bind, installed capacity is scarce and "
  "spreads stay wide, which is the provider's window and the equipment maker's pricing power.",
  "The queue and equipment gates bind for years rather than clearing through price.",
  "Energized megawatts lag announced megawatts by more than a year across the panel.",
  {"shortage": 1, "buildout": 1, "overbuild": -1, "shakeout": -1, "second_wave": 1})
C("equipment-scarcity", "Equipment scarcity pays the supplier",
  ["force:demand:token-volume", "force:power:gas-turbine-slot", "force:labor:turbine-casters",
   "force:grid:transformer-lead-time", "force:materials:goes-steel"],
  "Demand pulls on turbines and transformers at once; castings and core steel gate the makers, so lead "
  "times extend and the pricing power sits with whoever already has slots and mill capacity.",
  "The gates are capacity rather than price, so the margin accrues to incumbents for years.",
  "Lead times and supplier margins rise together across at least two equipment categories.",
  {"shortage": 1, "buildout": 1, "overbuild": -1})
C("policy-pull-forward", "Policy pulls the cycle forward and lengthens the shakeout",
  ["force:policy:investment-credits", "force:cycles:capital-inflow", "force:cycles:capacity-overbuild",
   "force:cycles:price-collapse", "force:cycles:shakeout-consolidation"],
  "Credits raise after tax returns, capital floods in, capacity overshoots and the adjustment is deeper "
  "than it would have been without the subsidy; the analogue is merchant power and telecom fibre.",
  "Subsidised capital is less disciplined than equity funded capital.",
  "Capacity announcements accelerate in the quarters after a credit is enacted, and cancellations follow "
  "within two years of the first price break.",
  {"shortage": 1, "buildout": 1, "overbuild": -1, "shakeout": -1, "second_wave": 1})
C("water-cooling", "Water and cooling constrain the site and reshape capex",
  ["force:water:cooling-water-availability", "force:sites:water-rights", "force:water:evaporative-limits",
   "force:water:closed-loop-retrofit", "force:providers:capex-intensity"],
  "Water stress turns into rules, rules force closed loop retrofits, and the retrofit spend lands on the "
  "provider's capex line, tightening the absorption chain.",
  "Water constraints bind locally before they bind globally, so the effect is site by site.",
  "Retrofit announcements cluster in basins under drought measures.",
  {"shortage": 1, "buildout": 1, "overbuild": 1})
C("labour-gate", "Labour is the slowest gate and the fastest cost",
  ["force:labor:epc-backlog", "force:labor:electricians", "force:grid:utility-capex-plan",
   "force:grid:rate-case-lag", "force:policy:energy-price-caps"],
  "Backlogs pull crews, wage pressure raises installed cost, utilities stretch plans, recovery lags, and "
  "the political response shows up as price caps that remove the next cycle's signal.",
  "The political channel binds before the capital channel does.",
  "Wage settlements and rate case outcomes move together in the same jurisdictions.",
  {"shortage": 1, "buildout": 1, "overbuild": -1, "shakeout": -1})
C("financing-flip", "Financing flips the sign of the build",
  ["force:financing:policy-rate", "force:cycles:capital-inflow", "force:providers:neocloud-funding",
   "force:cycles:capacity-overbuild", "force:cycles:price-collapse"],
  "Cheap money funds the marginal builder; expensive money removes the marginal buyer exactly when "
  "capacity is arriving, which is how cycles turn without a demand shock.",
  "The marginal entrant is funded, not retained earnings funded.",
  "Independent capacity announcements stop within two quarters of a funding shock.",
  {"shortage": 1, "buildout": 1, "overbuild": -1, "shakeout": -1, "second_wave": 1})
C("demand-elasticity", "Elasticity converts price cuts into volume",
  ["force:demand:inference-price-elasticity", "force:demand:token-volume", "force:demand:model-efficiency",
   "force:demand:agentic-workloads", "force:silicon:accelerator-resale-value"],
  "Cheaper inference pulls new workloads; always on agents lift the utilisation floor; the floor is what "
  "keeps old silicon economically alive, which is what holds resale values and financing terms.",
  "Unused use cases exist below the current price and get adopted within quarters.",
  "Token volume rises in the same quarters that unit prices fall, across two independent price series.",
  {"shortage": 1, "buildout": 1, "overbuild": 1, "shakeout": 1, "second_wave": 1})
C("tenant-power", "Tenant concentration moves the margin from the provider to the buyer",
  ["force:providers:tenant-concentration", "force:providers:rental-spread", "force:providers:revenue-per-mw",
   "force:providers:capex-intensity", "force:financing:abs-capacity"],
  "A few large tenants negotiate hard, spreads compress, revenue per megawatt stalls while capex keeps "
  "running, and the funding window depends on the contracts those same tenants sign.",
  "The largest tenants have a credible self build threat at all times.",
  "Renewal pricing falls while utilisation stays high, in at least two providers.",
  {"shortage": 1, "buildout": 1, "overbuild": -1, "shakeout": -1, "second_wave": 1})
C("margin-incidence", "Where the scarcity margin actually lands",
  ["force:power:firm-capacity-scarcity", "force:grid:transformer-lead-time", "force:providers:rental-spread",
   "force:providers:revenue-per-mw", "force:providers:equity-multiple"],
  "Scarcity runs from power to equipment to capacity rent; the question the chain asks is who keeps it. "
  "Equipment keeps it through lead time pricing, providers keep it only while tenants cannot self build, "
  "and the multiple is where the market decides which of the two it believes.",
  "The margin is retained by whoever has the least substitutable position.",
  "Supplier gross margins and provider revenue per megawatt move in opposite directions in at least one "
  "tight window, and the multiple follows the supplier.",
  {"shortage": 1, "buildout": 1, "overbuild": -1})
C("forced-flow-micro", "Forced flow and the dislocation it leaves",
  ["force:micro:forced-deleveraging", "force:micro:depth-liquidity", "force:micro:reversion-candidate",
   "force:micro:options-positioning"],
  "A leveraged account is forced out, the order consumes displayed depth, the dislocation is measurable, "
  "and the reversal is available to whoever is already there without needing to be first.",
  "The forced seller is finite, and the reversal is larger than the cost of providing liquidity.",
  "Post event paths reverse inside fifteen minutes more often than random times do, on the recorded tape.",
  {"shortage": 1, "buildout": 1, "overbuild": -1, "shakeout": -1, "second_wave": 1})

# --------------------------------------------------------------------------------------- assumptions
A("queue-is-a-queue", "Grid interconnection is a queue rather than a price.",
  "Compare queue position against energization date across the panel.",
  "Projects buy their way forward and energization order stops matching queue order.",
  "force:power:interconnection-queue", "the whole power chain and every provider spread read", load=5)
A("equipment-is-capacity-gated", "Heavy equipment lead times are capacity gates rather than price signals.",
  "Compare order books against delivered units and price realisations.",
  "Prices clear the backlog and lead times fall while order books stay full.",
  "force:grid:transformer-lead-time", "equipment margin chains", load=5)
A("firm-load", "Data centre load is firm and does not curtail at system peaks.",
  "Compare data centre load profiles against system peak events.",
  "Load curtails voluntarily or under contract at peaks.",
  "force:power:firm-capacity-scarcity", "capacity prices and provider siting", load=4)
A("elasticity-above-one", "Inference demand is elastic at current prices.",
  "Compare unit price changes against usage changes at the same intervals.",
  "Usage is flat or falls when unit prices fall.",
  "force:demand:inference-price-elasticity", "the whole compute demand curve", load=4)
A("depreciation-lands-first", "Capacity spending lands in earnings before it lands in revenue.",
  "Compare capex announcements against revenue and depreciation timelines.",
  "Revenue arrives with the capex or ahead of it.",
  "force:financing:depreciation-schedule", "the capex absorption chain and every provider multiple", load=5)
A("tenants-can-self-build", "The largest tenants have a credible self build alternative.",
  "Compare tenant contract terms against their own capacity announcements.",
  "Tenants sign long deals at posted prices with no own build programme.",
  "force:providers:tenant-concentration", "provider pricing power and spreads", load=4)
A("forced-seller-is-finite", "A forced seller is finite and identifiable after the fact.",
  "Compare open interest and funding signatures at dislocation events.",
  "Dislocations arrive with no identifiable forced side.",
  "force:micro:forced-deleveraging", "the cascade family and its cost hurdle", load=4)
A("reversal-exceeds-cost", "The post flow reversal is larger than the round trip cost of taking it.",
  "Compare gross reversion against fees and spreads at the same events.",
  "Reversion is smaller than costs at every level.",
  "force:micro:reversion-candidate", "the whole cascade family", load=5)
A("subsidy-discipline", "Subsidised capital is less disciplined than equity funded capital.",
  "Compare cancellation rates of subsidised against unsubsidised capacity.",
  "Subsidised projects cancel at lower rates.",
  "force:policy:investment-credits", "the policy pull forward chain", load=3)
A("water-binds-locally", "Water constraints bind locally before globally.",
  "Compare local drought measures against project announcements by basin.",
  "Constraints appear as a global rule rather than site by site.",
  "force:water:cooling-water-availability", "site selection and retrofit capex", load=3)
A("core-steel-gate", "Transformer core steel is the binding input rather than labour.",
  "Compare lead times against steel availability and mill expansions.",
  "Lead times shorten while steel stays tight or vice versa.",
  "force:materials:goes-steel", "the equipment scarcity chain", load=4)
A("measured-truth-can-lie", "Every measured association can be an artifact of sample, timing or specification.",
  "Re-run a finding on a disjoint sample and specification.",
  "A finding holds across samples, periods and specifications.",
  "any measured result", "every mechanical claim in the repository", load=4)
A("graph-is-the-object", "The graph is the research object and the trade is a path through it.",
  "Check that every trade claim names a path with a payer and a kill.",
  "Trades are proposed without a path or a kill.",
  "the repository", "how research is sequenced and reported", load=3)
