#!/usr/bin/env python3
"""Conceptual seed, part one: helper functions, the forces, and the demand, silicon and power interactions.

The content is data: every force, every push, every assumption and every kill. `build_conceptual_layer.py`
validates it and writes the JSONL that the connection index reads.
"""
from __future__ import annotations

PHASES = ("shortage", "buildout", "overbuild", "shakeout", "second_wave")

FORCES: list[dict] = []
INTERACTIONS: list[dict] = []
ASSUMPTIONS: list[dict] = []
CHAINS: list[dict] = []


def F(identifier: str, name: str, meaning: str, direction: str, observables: str, payer: str,
      evidence: str = "E4", source: str = "conceptual layer") -> None:
    domain = identifier.split(":")[1]
    FORCES.append({"id": identifier, "domain": domain, "name": name, "meaning": meaning,
                   "direction": direction, "observables": observables, "payer": payer,
                   "evidence": evidence, "source": source})


def I(source: str, target: str, relation: str, channel: str, condition: str, assumption: str, kill: str,
      lag: str = "1-4q", load: int = 3, signs: dict | None = None, evidence: str = "E4") -> None:
    INTERACTIONS.append({"from": source, "to": target, "relation": relation, "channel": channel,
                         "condition": condition, "assumption": assumption, "kill": kill, "lag": lag,
                         "load": load, "sign_by_phase": signs or {}, "evidence": evidence})


def A(slug: str, statement: str, test: str, kill: str, owner: str, blast: str, load: int = 3) -> None:
    ASSUMPTIONS.append({"id": f"assumption:{slug}", "statement": statement, "test": test, "kill": kill,
                        "owner": owner, "blast_radius": blast, "load": load})


def C(identifier: str, title: str, hops: list[str], intuition: str, greatest: str, observation: str,
      signs: dict | None = None) -> None:
    CHAINS.append({"id": f"chain:concept:{identifier}", "title": title, "hops": hops,
                   "intuition": intuition, "greatest_assumption": greatest, "observation": observation,
                   "sign_by_phase": signs or {}})


# --------------------------------------------------------------------------------------- demand
F("force:demand:token-volume", "Token volume", "the volume of inference and training tokens demanded",
  "pushes compute, power and rental demand up", "provider token disclosures, inference API traffic, model releases",
  "rental capacity owners")
F("force:demand:inference-price-elasticity", "Inference price elasticity", "how much usage expands when the price per token falls",
  "pushes usage up as price falls", "price per million tokens against usage growth", "end users")
F("force:demand:model-efficiency", "Model efficiency", "tokens produced per unit of energy and silicon",
  "dampens compute demand per unit of output", "tokens per watt, model architecture releases", "capacity owners")
F("force:demand:enterprise-adoption", "Enterprise adoption", "the share of enterprise workloads that use models in production",
  "pushes durable demand up", "enterprise software disclosures, survey data", "software and cloud vendors")
F("force:demand:agentic-workloads", "Agentic workloads", "always-on agents that consume compute continuously rather than in bursts",
  "pushes baseload compute and power demand up", "agent product launches, API concurrency", "capacity owners")
F("force:demand:consumer-apps", "Consumer AI usage", "consumer usage of generative products",
  "pushes bursty demand up", "app download and engagement data", "consumer platforms")
F("force:demand:sovereign-ai", "Sovereign AI", "national programs building domestic compute capacity",
  "pushes demand up and diversifies the buyer set", "government tenders, national compute plans", "taxpayers")
F("force:demand:training-scale", "Frontier training scale", "the frontier scale of training runs",
  "pushes concentrated high-end demand up", "model card disclosures, cluster announcements", "model labs")

# --------------------------------------------------------------------------------------- silicon
F("force:silicon:hbm-supply", "HBM supply", "high bandwidth memory capacity",
  "gates accelerator output", "memory maker guidance, HBM capacity announcements", "accelerator buyers")
F("force:silicon:cowos-packaging", "Advanced packaging capacity", "CoWoS and equivalent packaging lines",
  "gates accelerator output", "foundry packaging capacity disclosures", "accelerator vendors")
F("force:silicon:accelerator-lead-time", "Accelerator lead time", "quoted delivery time for accelerators",
  "signals scarcity and pushes rental prices up", "vendor lead time commentary, reseller quotes", "capacity buyers")
F("force:silicon:accelerator-resale-value", "Accelerator resale value", "secondary market price of installed accelerators",
  "reveals the economic life and financing quality of the fleet", "resale marketplaces, auction data", "financiers")
F("force:silicon:export-controls", "Export controls", "rules restricting accelerator and tool exports",
  "splits markets and pushes domestic buildout", "regulatory notices, licence filings", "vendors and buyers")
F("force:silicon:asic-substitution", "ASIC substitution", "in-house accelerator programs replacing merchant silicon",
  "shifts demand between vendors and dampens merchant pricing", "hyperscaler accelerator programs, tape-outs", "merchant silicon vendors")
F("force:silicon:node-capacity", "Leading edge node capacity", "wafer capacity at the leading nodes",
  "gates accelerator and networking output", "foundry capex and capacity disclosures", "foundry customers")
F("force:silicon:networking-optics", "Networking and optics", "switch, transceiver and optical interconnect supply",
  "gates cluster build rates", "transceiver vendor guidance, optics lead times", "cluster builders")

# --------------------------------------------------------------------------------------- power
F("force:power:interconnection-queue", "Interconnection queue", "the backlog of generation and load requests awaiting study",
  "delays connection and raises cost", "queue publications, study cycle times", "project developers")
F("force:power:energization-delay", "Energization delay", "the time from a signed request to actual power delivery",
  "pushes project timelines and rental economics", "queue milestone dates, utility reports", "capacity owners and tenants")
F("force:power:firm-capacity-scarcity", "Firm capacity scarcity", "the shortage of dispatchable capacity at peak",
  "pushes capacity prices and contract values up", "capacity auction results, reserve margins", "loads paying capacity")
F("force:power:gas-turbine-slot", "Gas turbine slot", "the booked manufacturing slots for heavy duty turbines",
  "gates new dispatchable power", "turbine vendor backlogs and slot disclosures", "developers")
F("force:power:nuclear-ppa", "Nuclear PPA", "long dated power contracts with nuclear plants",
  "prices firm power above merchant and anchors tenant economics", "PPA announcements, utility filings", "ratepayers and tenants")
F("force:power:merchant-power-price", "Merchant power price", "the spot and forward price of power in merchant markets",
  "reveals scarcity and drives margin for unhedged generation", "power futures, nodal prices", "merchant generators")
F("force:power:capacity-auction", "Capacity auction", "the market that pays for firm capacity",
  "prices reliability and reveals scarcity", "auction clearing prices", "loads")
F("force:power:grid-operator-reform", "Grid operator reform", "queue reform, fast track lanes and cluster studies",
  "accelerates or gates interconnections", "tariff filings, FERC and RTO orders", "developers")
F("force:power:onsite-generation", "On site generation", "behind the meter generation built by the load itself",
  "bypasses the queue and shifts the bottleneck to fuel and equipment", "permit filings, genset orders", "site owners")
F("force:power:power-cost-pass-through", "Power cost pass through", "the contract structure that passes energy cost to tenants",
  "protects provider margin and moves volatility to tenants", "lease and service contracts", "tenants")

# demand -> demand, demand -> silicon, demand -> power
I("force:demand:token-volume", "force:demand:model-efficiency", "competes_for",
  "More tokens can be served by better models, so efficiency substitutes for raw capacity.",
  "Model efficiency improves faster than usage grows.",
  "Efficiency gains are absorbed by new uses rather than reducing capacity demand.",
  "Capacity demand falls in absolute terms while token volume rises.", lag="2-8q", load=4,
  signs={"shortage": 1, "buildout": 1, "overbuild": -1})
I("force:demand:token-volume", "force:demand:inference-price-elasticity", "reveals",
  "Volume growth at falling prices is the evidence that demand is elastic.",
  "Price and volume move in opposite directions in the same window.",
  "Observed volume growth is measurable independent of price changes.",
  "Volume falls while price falls.", lag="1-2q", load=2)
I("force:demand:inference-price-elasticity", "force:demand:token-volume", "drives",
  "Falling unit prices pull new workloads into production.",
  "Elasticity above one at the current price point.",
  "Demand for inference is elastic and unused cases exist at lower prices.",
  "Token spend falls when price per token falls.", lag="1-3q", load=3)
I("force:demand:agentic-workloads", "force:demand:token-volume", "amplifies",
  "Agents keep consuming when a human session would have ended.",
  "Agent products run continuously rather than per request.",
  "Always-on workloads lift the utilisation floor rather than the peak.",
  "Agent traffic is spiky and does not change the floor.", lag="2-6q", load=3)
I("force:demand:training-scale", "force:silicon:accelerator-lead-time", "drives",
  "Frontier runs reserve capacity far ahead, lengthening quoted lead times.",
  "A small number of very large commitments dominate the order book.",
  "Training demand is concentrated enough to clear the vendor backlog.",
  "Lead times shorten while training commitments grow.", lag="1-2q", load=3)
I("force:demand:token-volume", "force:silicon:hbm-supply", "crowds_in",
  "More served tokens pull memory bits through the same fabs.",
  "Memory content per accelerator rises with model size.",
  "HBM capacity is the binding constraint on accelerator shipments.",
  "Accelerator shipments rise while HBM supply is flat.", lag="1-2q", load=4)
I("force:demand:token-volume", "force:power:firm-capacity-scarcity", "drives",
  "Continuous inference load raises the peak and the floor of power demand at once.",
  "Load is firm rather than interruptible.",
  "Data centre load does not curtail at system peaks.",
  "Firm capacity prices stay flat while data centre load grows.", lag="2-6q", load=4)
I("force:demand:sovereign-ai", "force:silicon:export-controls", "drives",
  "Export rules push sovereign buyers toward domestic or licensed capacity.",
  "Controls bind on the specific part numbers the buyer needs.",
  "Sovereign demand exists and is funded.",
  "Sovereign programmes are announced and never built.", lag="4-12m", load=3)
I("force:demand:sovereign-ai", "force:power:onsite-generation", "crowds_in",
  "Isolated national sites often bring their own generation.",
  "Grid connection is unavailable on the programme schedule.",
  "On site generation clears the permit faster than the queue.",
  "Sovereign sites wait for the grid and cancel generation.", lag="6-18m", load=3)
I("force:demand:model-efficiency", "force:power:energization-delay", "dampens",
  "Cheaper tokens per wait soften the urgency of new connections.",
  "Efficiency gains arrive before the connection is needed.",
  "Efficiency gains are not immediately absorbed by new demand.",
  "Efficiency improves and power demand for the same workload rises.", lag="2-8q", load=4)

# silicon -> power, silicon -> demand
I("force:silicon:accelerator-lead-time", "force:power:energization-delay", "complements",
  "A cluster needs silicon and power in the same window; the shorter of the two decides.",
  "Both inputs are required before the site earns revenue.",
  "Silicon and power lead times are comparable and not substitutable.",
  "Clusters energise with siloed silicon or idle powered sites without silicon.", lag="1-4q", load=4)
I("force:silicon:hbm-supply", "force:providers:rental-spread", "drives",
  "Memory constrained supply keeps rental prices firm for installed capacity.",
  "Installed capacity is scarce relative to demand.",
  "Rental price clears on availability rather than on cost.",
  "Rental prices fall while accelerator shipments are constrained.", lag="1-3q", load=3)
I("force:silicon:cowos-packaging", "force:silicon:accelerator-lead-time", "drives",
  "Packaging lines gate finished accelerators even when wafers are available.",
  "Packaging is a separate bottleneck from wafer capacity.",
  "Packaging capacity does not expand as fast as wafer capacity.",
  "Lead times shorten while packaging capacity is flat.", lag="1-3q", load=3)
I("force:silicon:asic-substitution", "force:silicon:accelerator-resale-value", "dampens",
  "In-house silicon reduces the future demand for merchant parts and their resale value.",
  "The substitute reaches production at scale.",
  "ASIC programmes replace rather than complement merchant parts.",
  "Resale values hold while substitution scales.", lag="2-6q", load=4)
I("force:silicon:accelerator-resale-value", "force:financing:abs-capacity", "reveals",
  "Resale value is the collateral story that securitisation depends on.",
  "Deals are underwritten against residual value.",
  "Residual value is measurable and financeable.",
  "Securitisation spreads do not move with residual values.", lag="1-3q", load=3)
I("force:silicon:accelerator-resale-value", "force:financing:depreciation-schedule", "reveals",
  "Residual prices are the outside evidence on useful life.",
  "An active secondary market exists.",
  "Depreciation policy is a judgment that the market can contradict.",
  "Reported useful life and market residual values diverge without any consequence.", lag="1-4q", load=3)
I("force:silicon:export-controls", "force:silicon:asic-substitution", "accelerates",
  "Restricted buyers accelerate their own programmes.",
  "Controls bind on merchant parts for that buyer.",
  "The buyer has the scale and talent to build its own part.",
  "Restricted buyers keep buying merchant silicon through third parties.", lag="4-12m", load=3)
I("force:silicon:networking-optics", "force:sites:latency-geography", "bounds",
  "Optics determine how far compute can sit from users at a given latency.",
  "Latency budget is the constraint rather than cost.",
  "Latency requirements are stable across the workload set.",
  "Workloads tolerate any distance and geography stops mattering.", lag="1-4q", load=3)

# power -> power, power -> grid
I("force:power:interconnection-queue", "force:power:energization-delay", "delays",
  "Queue position is the clock on the project.",
  "The queue is processed in order rather than by fast track.",
  "Queue positions are real and not reordered by policy.",
  "Projects jump the queue without paying or a rule change.", lag="1-4q", load=4)
I("force:power:grid-operator-reform", "force:power:interconnection-queue", "dampens",
  "Reform shortens the study phase and clears backlogs.",
  "Reform is implemented rather than filed.",
  "Reform targets the binding step rather than the easy one.",
  "Queue times are unchanged after reform is implemented.", lag="4-12m", load=3)
I("force:power:gas-turbine-slot", "force:power:firm-capacity-scarcity", "dampens",
  "New turbines add dispatchable capacity, easing scarcity later.",
  "Slots convert to operating plants.",
  "Slot bookings are not cancelled by financing or permits.",
  "Scarcity persists after booked slots are delivered.", lag="8-24m", load=3,
  signs={"shortage": 1, "buildout": 1, "overbuild": -1, "shakeout": -1, "second_wave": 1})
I("force:power:capacity-auction", "force:power:merchant-power-price", "reveals",
  "Auction clearing is the priced version of scarcity.",
  "Auction and energy markets clear the same reliability product.",
  "Prices reflect scarcity rather than administratively capped values.",
  "Auction clears low while energy prices spike.", lag="1-2q", load=2)
I("force:power:merchant-power-price", "force:power:onsite-generation", "crowds_in",
  "High merchant prices make self generation cheaper than the grid.",
  "On site generation is permitted and fuelled.",
  "The load can build generation faster than it can buy power.",
  "Loads pay record prices and build nothing.", lag="2-6q", load=3)
I("force:power:nuclear-ppa", "force:power:firm-capacity-scarcity", "dampens",
  "Long dated nuclear contracts convert scarcity into contracted supply.",
  "Plants extend or restart rather than retire.",
  "Contract volumes are additional rather than reshuffled.",
  "Scarcity persists while nuclear PPAs are signed for existing volumes.", lag="4-16q", load=3)
I("force:power:onsite-generation", "force:power:interconnection-queue", "dampens",
  "Behind the meter load never joins the queue.",
  "Permitting allows on site generation at scale.",
  "On site capacity is large enough to matter to the queue.",
  "Queue growth continues at the same rate while self generation scales.", lag="2-6q", load=3)
I("force:power:power-cost-pass-through", "force:providers:contracted-share", "drives",
  "Pass through contracts let providers offer fixed prices and win longer commitments.",
  "Tenants value price certainty.",
  "Providers are willing to pass through rather than absorb energy risk.",
  "Tenants refuse pass through and demand fixed all in pricing.", lag="1-3q", load=2)
I("force:power:energization-delay", "force:providers:rental-spread", "drives",
  "Delay keeps installed capacity scarce and rental spreads wide.",
  "Demand outruns connections.",
  "The bottleneck is real rather than announced.",
  "Spreads narrow while energization delays lengthen.", lag="1-3q", load=4)
I("force:power:firm-capacity-scarcity", "force:grid:utility-capex-plan", "drives",
  "Scarcity forces utilities to plan capacity and grid work.",
  "Utilities are the ones who build the response.",
  "Regulators allow the recovery of the spend.",
  "Capex plans shrink while scarcity is priced higher.", lag="2-6q", load=3)
I("force:power:grid-operator-reform", "force:grid:interconnection-study-backlog", "dampens",
  "Cluster studies and automation cut the study backlog.",
  "The bottleneck is study labour rather than siting.",
  "Study capacity can be expanded with process rather than people.",
  "Backlog grows while reform is claimed implemented.", lag="2-6q", load=3)
