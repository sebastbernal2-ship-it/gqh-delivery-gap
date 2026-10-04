# Deep chaining: every node carries its own connections

The decomposition pass wrote the graph at sub-node resolution. This pass writes the connections inside
each node, typed, so a node is no longer a label with edges somewhere else. It is a record that says:
I am connected to B by this relation, B is connected to C by that relation, and here is the chain id and
hop number where that path lives. The captain's picture is exactly right: A holds B with an edge type,
B holds C as chain step one, and the whole thing is data.

## The node record

Every node in the graph gets one record in `docs/scan/connection-index.jsonl.gz`:

    {"id": "<node id>", "layer": "...", "meaning": "...", "degree": 63,
     "by_status": {"declared": 12, "curated": 8, "inferred": 43},
     "by_type": {"splits_into": 6, "ties_by_player": 9, "chain_precedes": 2, "...": 0},
     "connections": [{"to": "...", "type": "...", "status": "...", "why": "...",
                      "condition": "...", "falsifier": "..."}],
     "chains": [{"chain": "...", "hop": "hop:...:03", "position": 3,
                 "prev": "hop:...:02", "next": "hop:...:04", "relation": "requires"}]}

`degree` is the count of typed connections. The target is at least fifty per node, and the index reports
how many nodes reach it. The status field keeps that honest: `declared` comes from the manifest,
`curated` from the digs, `inferred` from the rules below, and an inferred connection is a question with
a type, never a fact.

## The connection types

Structural and declared types come from the existing vocabulary: `splits_into` (parent to child),
`part_of`, `feeds`, `measures`, `observes`, `indicates`, `affects`, `governs`, `gates`, `derives_from`,
`supports`, `tested_by`, `exposes`, `identifies`, `instantiates`, `makes_available`, `conditions`,
`candidate_for`, `contains`, `belongs_to`, `has_field`.

This pass adds the chaining vocabulary:

| Type | Meaning |
|---|---|
| `chain_precedes` | this node is the step before the target inside a named chain |
| `chain_follows` | this node is the step after the target inside a named chain |
| `bridges_to` | a curated cross-dig link, such as rhenium to molybdenum roasting |
| `ties_by_player` | the same named company or institution appears on both sides |
| `ties_by_observable` | both nodes are read from the same source family, such as USGS or LME |
| `ties_by_source` | both nodes point at the same dataset or filing stream |
| `shares_semantics` | the meanings share vocabulary and likely describe related things |
| `sibling_subnode` | two children of the same parent, connected through the parent |

## The inference rules

Each rule names its own falsifier, because an inferred connection without a kill condition is noise:

- **Shared player.** Two nodes naming the same company are tied. Falsifier: the player is not material
  to one of the two sides.
- **Shared observable family.** Two nodes read from the same source program (USGS, EIA, LME, BLS,
  USITC, DOE, NRC, trade press, company filings) are tied as monitoring pairs. Falsifier: the two reads
  come from different products of the same publisher.
- **Semantic overlap.** Meanings sharing enough vocabulary are tied as related mechanisms.
  Falsifier: the overlap is generic vocabulary, and the two nodes move for different reasons.
- **Structural.** Parent, child and sibling links from the decomposition skeleton. Falsifier: the
  decomposition was wrong for this node, which the status field already flags.

Inferred connections are capped per node, ranked by rule strength, and every one carries its rule name
in `why`. The file makes the counts visible so nobody mistakes a large degree for knowledge.

## Chains as addresses

A chain is a first-class object with hops. For a chain A to B to C, the index writes:

- `hop:<chain>:01` from A to B, with the relation, condition and falsifier,
- `hop:<chain>:02` from B to C, with its own,

and each node's record lists every hop it participates in, with position, prev and next. That is the
captain's "C is chain sub-one": a sub-address, resolvable from either endpoint.

Cross-dig bridges are chains of length one: `chain:bridge:<name>`.

## Commands

    python3 scripts/build_connection_index.py --manifest docs/scan/quantgraph.jsonl
    python3 scripts/build_connection_index.py --show mechanism:capacity:transformer-bottleneck
    python3 scripts/build_connection_index.py --chain dig:fcc:catalyst-minerals
    python3 scripts/render_connection_index.py

## What this enables

A search no longer starts from a pair of tickers. It starts from a node, reads its typed connections,
follows a hop into another layer, and arrives at a payer with the conditions written down at every step.
New connections proposed by a model are appended to the index in the same schema, and the index answers
the only question that matters for promotion: what does this path assume, and what would kill it.
