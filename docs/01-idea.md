# The idea: the AI capex complex is a book of delivery options priced as certainties

Written 2026-10-02. This is the strategy. The system document is only the execution plan.

---

## 1. The idea in one paragraph

The AI capex complex is priced on **announced** capacity: MW and GW pipelines, signed
agreements, guidance. Capacity is not deliverable unless it is **energized**, and power is
the binding constraint: interconnection queues, gas turbine backlogs, and transformer lead
times are all measured in years, while the generation mix actually planned does not serve
coincident firm data center load. So the complex holds a book of claims on delivery dates
and the market prices those claims as if delivery were certain. The claim is not certain.
We measure the size of the uncertainty from official dated data, and we trade the spread
between the names that can deliver and the names that are priced as if they already had.

The single state variable is **the transport cost between the promised delivery-date
distribution and the realized delivery-date distribution**, per region. Delivery promises
move; the movement is a transport plan between two measures over dates; its cost is the
slippage. That quantity is not in any headline, and it is computable from public files.

---

## 2. Why the gap exists, in physical facts

These are the load-bearing facts, all dated, all public.

- **The promise is mostly not firm capacity.** In the December 2025 EIA-860M vintage, the
  record 86 GW of planned 2026 utility-scale additions was 51 percent solar, 28 percent
  storage, 14 percent wind, and only 6.3 GW natural gas. Data center load is coincident and
  firm, so the planned mix is not equivalent to the load it is meant to serve.
- **The promise slips, and EIA measures how much.** EIA's own analysis found 19 percent of
  planned solar MW had their scheduled online date pushed back in 2023, after 23 percent in
  2022. Slippage is a measured, recurring property of the pipeline, not an anecdote.
- **Independent estimates put the delivery shortfall near 40 percent.** Goldman Sachs
  (June 2026) estimated US data center demand rising from 31 GW in 2025 to 41 GW in 2026,
  with roughly 60 percent of the capacity scheduled for the next year arriving on time
  after delivery-risk adjustment. Press reporting in the same period concluded that about
  half of planned US data center builds have been delayed or canceled, limited by power
  infrastructure and part shortages.
- **The constraint is physical, so it cannot be arbitraged away.** Gas turbine slots are
  sold out years ahead. High-voltage transformer lead times are reported at roughly 120
  weeks and up to about four years. Nobody can short a transformer queue. This is why the
  mispricing can persist: the correcting action is a factory, not a trade.

The captain's own question, "are they following their schedule, are cells missing, is it
visual rather than numeric", is exactly right, and the answer is that it is numeric. The
promised dates and the realized dates are both published, monthly, in files nobody reads.

---

## 3. Who is on the other side, and why they do not fix it

- **The momentum and index buyer.** They must own the announcement, and the announcement is
  the thing that is wrong. Their bid is not a view on delivery dates.
- **The developer or utility equity holder.** Their valuation capitalizes a pipeline. They
  cannot mark the pipeline to a delivery schedule they do not publish.
- **The option seller who treats these names as trending.** They price disclosure windows as
  continuation, not as the moment the schedule is revised.
- **The informational constraint.** Slippage lives in monthly EIA vintages and in ISO
  interconnection queue filings. It is not in a headline, so it is not in the price. That is
  the whole edge, and it is an attention and processing constraint, not a claim about
  intelligence.

---

## 4. The state variable, precisely

**Definition.** For each ISO region and technology, and MW-weighted:

1. Take the promised delivery-date measure from an EIA-860M vintage. Each unit is a mass at
   its planned in-service month, matched across vintages by plant ID and generator ID.
2. Take the realized measure from later vintages, using the transition into the Operating
   tab as the realization flag, and the annual EIA-860 for the initial commercial operation
   date.
3. The slippage is the optimal transport cost between the two measures. Report W1 and W2,
   MW-weighted, plus the share of mass that disappears (cancellation) and the median delay
   in months.

**Why this exact object.** Slippage is not a number, it is a *movement of mass across date
buckets*. The principled measure of that movement is a transport cost, and the principled
estimate of the optimal plan is entropic optimal transport, which is Sinkhorn. This is the
same machinery as arXiv 2609.39256 (Stochastic Knothe-Rosenblatt), which matches prescribed
marginals exactly with Martingale Sinkhorn while staying closest to a reference dynamic.
There, the marginals come from option smiles. Here, they come from delivery schedules. Same
mathematics, second application, and that is why the paper is load-bearing rather than
decorative.

**Signal.** The change in transport cost, per region, month over month, and its level
against its own history. Rising transport cost in a region, while that region's names are
priced on the pipeline, is the short trigger.

---

## 5. The trade

**Core leg, relative value.**

- Long the constraint: gas turbine OEMs, transformer and switchgear suppliers, grid
  engineering and construction, cooling and water equipment, and generation owners with
  energized capacity and signed long-dated offtake.
- Short the dependence: names in the same region whose valuation rests on announced
  capacity that has slipped, sized by that region's scheduled MW exposure.
- Neutralize market beta and the known factors (market, value, momentum, and the
  gas-and-nuclear versus solar-and-storage spread) so the residual is the delivery spread.
- Rebalance on the EIA-860M release calendar, which is scheduled and therefore testable.

**Event overlay.** The moments the gap becomes public are rule-dated. An 8-K is due within
four business days for most items, so power agreements, delays, terminations, and guidance
revisions arrive on a calendar set by federal rule. Measure the implied move from the
pre-event session as (ATM call + ATM put) / spot against the realized move to expiry,
categorized by what the filing actually says, with a placebo cohort of non-AI categories.
Sell the implied move where the hedge demand is structural, buy it where the chain
underprices an upside surprise. This is the Massive bonus sub-challenge, and it is the same
mechanism in the options venue.

**Fundamental anchor, and the reason the complex can be measured at all.** OCPI, the Ornn
Compute Price Index, is a daily settled price of executed GPU rental transactions in USD
per GPU hour. H100 settled near 2.79 on 2026-10-02, with a three-month range of 2.46 to
3.17. ICE has listed an Ornn Compute Price Index H100 future. So the price of the thing the
complex sells now has a **listed forward curve**, which means the equity complex can be
measured against its own commodity curve rather than against a narrative. Compute price is
the fundamental; energized capacity is the supply constraint; the delivery gap is the
timing wedge between them.

**Live monitor and unwind.** On Hyperliquid, perp funding on AI-narrative names is a
real-time price of narrative leverage with no equity equivalent, and liquidation cascades
are the unwind of that leverage. Full L4 book history is published, so execution cost can
be modeled from the book instead of assumed. This leg is a monitor and an execution
laboratory, not the main source of edge.

---

## 6. Falsifiers, and the simple explanations we must rule out

Written before any run, as the rubric requires.

1. **The gas-and-nuclear versus solar-and-storage factor explains it.** Then the trade is a
   known technology spread, not a delivery-gap claim. Test by orthogonalizing.
2. **Market beta explains it.** Then it is a directional bet. Test with beta-neutral
   construction and with the market factor.
3. **It is already priced.** The power-bottleneck theme is well known and the constraint
   names trade rich. This is the most serious objection, and it is why the edge must be the
   **measurement** (vintage-level slippage mapped to a specific regional exposure and a
   specific pair), not the theme. If the pair's return is explained by the theme's factor,
   the idea fails and the note must say so.
4. **The transport cost does not predict the spread.** If a rising regional transport cost
   does not predict the regional pair's underperformance net of costs, the state variable is
   wrong.
5. **Costs kill it.** Turnover is low because the release is monthly, so the honest test is
   the doubling test at realistic bps.

---

## 7. Honest limitations to state in the note

- EIA-860M covers utility-scale generation of about 1 MW and up. Behind-the-meter and
  on-site turbines at data centers, which are a real part of how these sites get powered,
  are not fully captured. This biases measured slippage in an unknown direction, and we say
  so.
- The regime is short. The AI capex cycle becomes measurable from 2023, so the in-sample
  panel has on the order of 30 to 40 monthly observations for the fundamental leg. Power is
  low. State it, and use the scheduled release calendar to get cleaner identification than
  the sample size alone would allow.
- OCPI full history begins in January 2025 with sparse observations from mid 2024. Under the
  mandated out-of-sample rule, the shorter of 20 percent or two years, the compute-price leg
  has roughly a four-month out-of-sample window. Free access covers only the trailing three
  months, and full history is a paid tier. The delivery-gap leg is the one with usable
  history, so it carries the note.
- The realized-date measure depends on the Operating tab transition, which is preliminary
  and revised. We freeze vintages and never revise a vintage after use.

---

## 8. What is cut, and why

- **Langlands, affine Kac-Moody algebras, grand unified theory.** Explained in the system
  document: real kinship to optimal transport through Weyl-group integration, no testable
  prediction inside the window. Cut from the note.
- **Visual or satellite tracking of construction.** The keys exist and the question is real.
  A labeled series does not exist yet, so it is mechanism evidence in section 1 of the note,
  not a signal.
- **Forex, deferred but not dead.** The physical bottleneck is largely imported: turbines,
  transformers, and high-voltage cable come from a small set of exporters. The same trade
  expressed in those exporters' currencies and order books is a real fourth leg. It is
  deferred because three legs already fill five pages.
- **Any model that forecasts returns.** Not needed. Every input here is an official dated
  publication.

---

## 9. Why this is not the blackbox you objected to

Every input is a dated official publication or a traded price: EIA vintages, ISO queue
filings, Form 8-K text, option chains, the compute price index and its new futures curve.
The signal is a transport cost between two published distributions. The only learned
component is a typed extractor over filing text that outputs schema-validated fields, so a
bad extraction raises a validation error instead of quietly funding a trade. The quantum and
high-performance computing layer only solves a bounded scheduling problem and samples from
the calibrated joint law, and it reports where it loses to classical methods. Nothing in the
strategy is "data in, hope out".
