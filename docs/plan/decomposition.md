# Decomposition: the sub-node law

The graph at 569 nodes was a map at the wrong resolution. The edge usually lives one or two levels
below the node everyone already names. Gasoline demand lifting the crack spread is a fact the market
knows. The same demand, chased into the fluid catalytic cracking unit, lands on the catalyst, then on
the Y-zeolite in the catalyst, then on the lanthanum and cerium that stabilise the zeolite, then on the
separation plants that make them, and that chain is not in any model. The crack spread is the visible
end of it. The minerals are the edge.

This file is the law for writing the graph down at that resolution.

## The law

Every node decomposes into **at least five children** along the dimensions of its own layer. Each child
is node-shaped, carries its parent, its dimension, its meaning, its status and the ask that would verify
it. Children get written down whether or not we have data for them yet, because the shape of the missing
piece is itself information.

Two rules keep this honest:

1. **Count is not depth.** A generated child with no observable, no payer and no ask is padding.
   The status field exists to separate the skeleton from the seeded content.
2. **A child is not evidence.** A `proposed_unverified` child may be cited as a question, never as a
   fact, and never in the note.

## Dimensions by layer

| Layer | The six dimensions |
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
| physical assets and raw materials | composition, inputs, constraints, observables, substitutes, payers |
| anything else | composition, inputs, constraints, observables, substitutes, payers |

## Recursion policy

- **Manifest skeleton depth 3.** Every manifest node gets its layer dimensions, each child gets five generic children, and each grandchild gets four generic children.
  The rows remain `proposed_unverified` and exist to expose missing questions, not to claim evidence.
- **Curated depth 4.** Where a chain carries edge, a human or a model with domain knowledge fills the levels with named minerals, named suppliers, named data sources and named payers.
  That is where `deep-digs.jsonl` lives, and it is the part worth reading.
- **Conceptual depth 2.** Forces and assumptions receive their own first and second conceptual children so their payers, tests and failure modes remain countable.

## Statuses

| Status | Meaning |
|---|---|
| `measured` | backed by an artifact in `results/` or a ledger row |
| `seeded` | curated from domain knowledge, with a named source to verify |
| `proposed_unverified` | generated skeleton, an ask without an answer yet |

## Child schema

    {"kind": "subnode", "id": "sub:<parent>:<dimension>", "parent": "<parent_id>",
     "dimension": "<one of the six>", "layer": "<layer guess>", "meaning": "<what it is>",
     "status": "measured|seeded|proposed_unverified", "ask": "<the observation that verifies it>",
     "tie_to": ["<existing manifest node the child connects to>"]}

Split edges are rows of `kind: split` with `from`, `to`, `relation: splits_into`, so the whole file is
graph-shaped and can merge into the manifest when the viewer is ready to carry it.

## The artifacts

- `docs/scan/decomposition.jsonl.gz`: the mechanical skeleton, every node and child with split edges.
- `docs/scan/decomposition-summary.json`: counts by layer, status and depth.
- `docs/scan/deep-digs.jsonl`: the curated digs, FCC catalyst first, each with its own chain of named
  inputs, suppliers, observables and payers.
- `docs/scan/decomposition.md` and `.html`: the rendered view.

Run:

    python3 scripts/decompose_graph.py --manifest docs/scan/quantgraph.jsonl
    python3 scripts/render_decomposition.py

## What this fixes and what it does not

It fixes resolution: the reasons an aggregate moves are now written down as nodes with owners, rather
than staying tacit. It does not find the edge by itself. It gives every future chain search the right
grain to search in, which is the difference between a story about gasoline demand and a position in the
minerals under the catalyst.
