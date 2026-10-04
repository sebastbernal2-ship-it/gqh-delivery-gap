# Regimes: why the rationale must survive the cycle

The last five years of this complex went up. That is not evidence, it is one phase of one cycle, and a
strategy that only describes that phase is a description of the past. This file owns the regime
discipline: the phase model, the markers that identify each phase, the analogue requirement, and the
rule that every chain declares its sign per phase or admits it has none.

## The phase model

Infrastructure buildouts repeat in five phases. The names are ours, the pattern is not.

| Phase | State | Markers | Who earns |
|---|---|---|---|
| 1. Shortage | demand outruns capacity | price spikes, utilisation near full, waiting lists | incumbents with capacity |
| 2. Buildout | capital floods in | capex growth, debt issuance, new entrants, equity issuance at high multiples | suppliers, contractors, early builders |
| 3. Overbuild | capacity passes demand | price collapse, utilisation falls, discounting, contract renegotiation | no one; shorts and hedgers |
| 4. Shakeout | capital is destroyed | bankruptcies, asset sales below cost, dividend cuts, credit downgrades | distressed buyers |
| 5. Consolidation and second wave | survivors hold contracted assets | stable utilisation, regulated or long-contract returns, REIT and utility structures | consolidated owners, rate base |

The transitions are the dangerous part. Phase 2 and phase 3 look identical from inside the capex data
until price and utilisation turn, which is why the markers above are paired: capex alone never
identifies the phase.

## The analogue requirement

A phase claim is trusted only when the same mechanism has been observed in at least two independent
infrastructure cycles, with the same ordering of phases. The analogues are written down in
`docs/scan/analogue-cycles.jsonl`: railroads, electrification, merchant power, nuclear, fiber and
telecom, midstream, and cloud and colocation.

Each analogue carries its own dates, markers and equity outcomes, so a claim can be checked against
more than one history instead of against a story.

## The validity test for a twenty year rationale

A chain may claim a ten to twenty year rationale only if:

1. The payer exists in every phase of at least two analogues, even when the instrument changes.
2. The mechanism does not depend on a single technology, vendor or policy regime.
3. The chain names what would falsify it in phase 3 specifically, because phase 3 is when the story is
   most expensive to hold.

## Regime conditional signs

Every chain and every candidate declares its sign per phase, or declares `regime: unclear` and stays a
watch item. The sign flip is the point: the same mechanism is long the supplier in phase 2 and long the
consolidator in phase 5, and long nothing in phase 3.

## Compute as a regime instrument

The compute rental index is a read on provider behaviour under inventory conditions, not a clearing
price: our measures found ten essentially independent families and no listed instrument that isolates
them. The direct provider-capex, provider-revenue, and provider-family transmission studies did not support
the rental series as a standalone equity signal. So the compute index enters this framework the honest way:

- as a **phase marker**: falling rental prices with rising capacity can mark phase 3, while rising prices
  with constrained inventory can mark phase 1;
- as a **conditioning variable**: the rental level relative to its trailing family baseline can modify the
  measured effect of a delivery revision, subject to a new point-in-time interaction test;
- never as a required link, direct P&L sleeve, or hedge instrument. The chain must stand with the compute
  index removed, and the index may only shift timing, confidence, or position size after conditional evidence.

## The latency clause

An edge that requires a latency advantage is an execution business, not a research edge. Every chain in
this repo must be profitable without one. Latency and fast estimation may then be layered on to improve
entry, and the entry windows are written down in the entry windows dig so the improvement can be
measured rather than assumed.
