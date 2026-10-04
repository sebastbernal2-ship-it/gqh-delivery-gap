# Regime and factor program

Owner: `docs/plan/regime-factor-program.md`.

Status: development proposal.

The phase model remains owned by `docs/plan/regimes.md`.
The state machine remains owned by `docs/plan/regime-state-machine.md`.
This file owns the factor register, hedge map, conditional-risk tests, and acceptance gates.

## Purpose

Regimes describe the state of the world that can change an edge's size, sign, or tradability.
Factors describe return exposures carried by an instrument.
Hedges reduce unintended exposure without changing the intended edge.
A low full-sample correlation is not enough to call something a hedge.

Every regime and factor unit needs one definition, one unit, one clock, one source, one availability rule,
one owner, one falsifier, and one status.
Unknown is a risk state and is never treated as neutral.

## State vector

The first version uses separate dimensions rather than one composite score.
A composite score would hide which sensor failed and would create an uncounted model choice.

| Dimension | Primary readings | Current role |
|---|---|---|
| Demand tightness | Compute rental level versus trailing family baseline, family dispersion, compute capex | Phase marker and conditional input |
| Physical supply tightness | Queue survival, withdrawal hazard, reserve margin, equipment lead time, energization | Physical confirmation and size gate |
| Construction cycle | Construction spending, unfilled orders, delivery times, labor pressure | Phase marker and control |
| Contract conversion | Backlog burn, RPO growth, contract duration, cancellations, change orders | Cash-flow bridge |
| Financing stress | Real rates, credit spreads, DSCR distance, refinancing dates, dilution | Duration and credit gate |
| Market stress | Volatility, spread, depth, borrow, funding, open interest | Capacity and no-trade gate |
| Policy state | Tax credits, tariffs, export controls, permits, utility regulation | Regime control and falsifier |
| Physical disruption | Heat, drought, storms, water restrictions, outages | Physical confirmation and tail control |

## Factor register

Factors enter in this order.

1. Cash and funding factors cover financing cost, margin, funding, and liquidity.
2. Market factors cover market beta, sector beta, size, value, momentum, reversal, and volatility.
3. Macro and sector factors cover rates, credit, dollar, inflation, industrial activity, power, gas, copper,
   uranium, and construction.
4. Theme factors cover compute demand, grid expansion, and data center activity.
5. Supply-chain factors cover transformers, advanced packaging, HBM, cables, turbines, labor, and water.
6. Name-specific factors cover issuer, project, tenant, supplier, contract, and parent-company exposure.

A factor with no tradable vehicle remains a bounded assumption or a control.
It does not become residual risk by default.

## Compute-conditioned delivery gap

The surviving compute hypothesis is not `compute price rises, buy provider equities`.
The candidate is:

```text
high compute tightness
+ physical supply bottleneck
+ dated negative delivery revision
+ concentrated issuer exposure
```

The compute signal is the rental level relative to its trailing family baseline.
The event signal is a point-in-time delivery or capacity revision against an earlier public expectation.
The issuer term is a verified project, contract, segment, and security exposure chain.
The physical term is a confirmed queue, equipment, energization, or realized-delivery observation.

The interaction is a candidate relation, not a promoted edge.
The direct provider-capex, provider-revenue, and provider-family rental studies remain retired as standalone
transmission paths.

## Hedge map

| Unintended exposure | First control or hedge | Rule |
|---|---|---|
| Market beta | Market benchmark or beta-neutral construction | Remove common movement before interpreting the event |
| Sector beta | Sector control or matched sector hedge | Do not remove the mechanism with the hedge |
| Rates and duration | Rate control or duration offset | Use only when the issuer has duration exposure |
| Credit and refinancing | Credit spread control, cash, or smaller size | Do not use broad equity as a credit hedge without evidence |
| Commodity input | Commodity control or direct pass-through hedge | Require a verified margin or contract channel |
| Compute demand | No direct hedge is currently authorized | Use compute as a gate or conditioning variable |
| Liquidity and borrow | Participation cap, borrow check, no-trade rule | A smaller position is the default hedge |
| Event clusters | Issuer, project, week, region, and parent caps | Treat shared filings as one risk |
| Policy shock | Policy state control and size reduction | Do not claim a policy hedge without an instrument |
| Physical disruption | Cash, size reduction, or verified physical offset | Drought and weather are not universal hedges |

## Conditional-risk test

Before any state changes position size, run the same-state null and report the comparison count.
The primary event test uses the five-session horizon and reports 1, 2, 5, 10, and 20 sessions.
The model includes the delivery revision, the state reading, their interaction, market and sector controls,
rates, credit, power or fuel controls when available, and event-cluster controls.
The result must be stable under issuer, project, and reporting-week leave-outs.

The state gate fails if the interaction disappears after controls, changes sign across nearby thresholds,
depends on one issuer, or cannot be built from an available historical timestamp.
A hedge fails if it changes the intended exposure, adds more cost than risk reduction, or only works in the
same regime as the core position.

## Admission gates

1. The event has an ordered observation, publication, usable, decision, and fill clock.
2. The factor has a point-in-time value and a source receipt.
3. The exposure chain reaches a named issuer and security with verified evidence.
4. The payer and transfer are stated at contract or cash-flow level.
5. The instrument has borrow, spread, depth, capacity, and cost evidence.
6. The conditional result beats its same-state null and survives doubled costs.
7. The realized factor exposure is attributed against the risk budget.
8. Missing evidence remains a no-trade or size-reduction reason.

No factor or regime creates a new P&L sleeve until these gates pass.
The compute index remains a monitor and conditioning input unless a future instrument and a new study are approved.
