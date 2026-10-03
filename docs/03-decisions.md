# Decisions

Append only. Newest at the bottom. Every settled decision goes here, once.

A decision is anything that would be expensive to reverse: the mechanism, the universe, the
out-of-sample cut, the cost model, a schema change, who owns what.

---

## 2026-10-02: Build the full system design before writing engine code

**Decision.** Design all engines and the interface contract first, then distribute across four people.
**Context.** Four people had to work in parallel from the same night.
**Alternatives.** Building Engine 1 end to end first was proposed and rejected.

---

## 2026-10-02: Anchor every trade on one mechanism, and cut the rest

**Decision.** One mechanism (rule-dated disclosure plus forced hedging in the AI capex complex) with
one mathematical spine, the marginal-constrained coupling. Option smiles are the risk-neutral anchor.
**Context.** The track scores Economic Foundation first and the captain rejected blackbox pipelines.
**Alternatives.** A quantum-alpha or ML-forecast thesis was rejected. Langlands, affine Kac-Moody,
and grand unified theory were cut: real mathematical kinship, no testable prediction in the window.

---

## 2026-10-02: The strategy is the delivery gap

**Decision.** The trade is the spread between names that can deliver energized capacity and names
priced on announced capacity that has slipped. The state variable is the transport cost between the
promised and realized delivery-date distributions, computed from EIA-860M vintages.
**Context.** Announced capacity is not energized capacity. Power is the binding constraint: turbine
slots sold out years ahead, transformer lead times around 120 weeks and up to four years. EIA measured
19 percent of planned solar MW slipping in 2023 after 23 percent in 2022. Goldman Sachs put roughly
60 percent of scheduled data center capacity arriving on time. Press reporting said about half of
planned US builds were delayed or canceled.
**Alternatives.** A compute-price-only thesis was rejected because OCPI history is too short for the
mandated out-of-sample rule. A generic short-vol event study was rejected as insufficiently distinct.
**Open risk.** The power-bottleneck theme is well known and the constraint names trade rich. The edge
must be the measurement, not the theme.

---

## 2026-10-02: One public repo is the source of truth for shared memory

**Decision.** `github.com/sebastbernal2-ship-it/gqh-delivery-gap` is public and holds the shared
memory, the decision ledger, the ownership map, and the artifact schema. Local agent memory and chat
are caches. If it is not in the repo, it is not shared.
**Context.** Four devices, four people, one deadline. Chat and local memory stores do not converge on
their own.
**Alternatives.** A private repo until submission was offered and rejected: a broken link at the
deadline is a bigger risk than early visibility.
