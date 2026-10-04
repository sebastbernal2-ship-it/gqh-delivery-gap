#!/usr/bin/env python3
"""Declare the positioning and leverage family, so leverage stops living in prose.

Why: `docs/alignment.md` section 18.4 names "crowding and narrative leverage" as a node fed by perpetual
funding and open interest, and until now it had no node id, no layer, no representation, no clock and no
measurement anywhere in the graph. The cascade protocol and the Hyperliquid tape exist, so the family can be
declared with the tape as its representation and the genuine blockers written in.

The family it writes, all of it idempotent by id prefix:

- the tape as a dataset, which is forward only and 440 minutes old
- four features the tape actually carries: funding rate, open interest, basis and book depth
- one feature it cannot carry, margin distance, because account level leverage is not public
- the mechanism, the event, the claim and the experiment that test it
- the four markets as assets

Rules it obeys: every node connected, no orphan, a blocker on every blocked node, and no node claiming a
measurement the artefacts do not contain.

Usage:
    python3 scripts/declare_positioning_nodes.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "docs" / "scan" / "quantgraph.jsonl"
PREFIXES = ("positioning:", "leverage:", "asset:perp:", "dataset:hyperliquid:", "feature:positioning:",
            "mechanism:leverage:", "event:leverage:", "claim:cascade:", "experiment:cascade:",
            "e-positioning-")

TAPE = "dataset:hyperliquid:tape"
NODES = [
    {"kind": "node", "id": TAPE, "layer": "dataset", "type": "dataset",
     "meaning": "Forward tape of the perpetual venue: ten book levels each side, funding rate, open interest, "
                "mark and oracle price, fifteen second cadence, markets BTC, ETH, GAS and SPX",
     "status": "declared", "unit": "sample every fifteen seconds",
     "availability": "results/cascade-tape.json summarises it and data/tape holds the samples, written by "
                     "scripts/collect_tape.py. Forward only: the archive begins at its first sample",
     "sources": ["source:perp-venue"], "roles": ["provenance"],
     "falsifier": "The venue stops serving public endpoints, or the collector stops running"},
    {"kind": "node", "id": "feature:positioning:funding-rate", "layer": "feature", "type": "derived_feature",
     "meaning": "The rate a leveraged position pays to hold, the price of carry on the venue",
     "status": "declared", "unit": "rate per interval",
     "availability": "on the tape every fifteen seconds from the first sample",
     "sources": [TAPE], "roles": ["input", "conditioning_variable"],
     "falsifier": "Funding carries no information about the path of the price after a forced closing"},
    {"kind": "node", "id": "feature:positioning:open-interest", "layer": "feature", "type": "derived_feature",
     "meaning": "Contracts outstanding, which falls when positions are closed by the engine rather than by choice",
     "status": "declared", "unit": "contracts",
     "availability": "on the tape every fifteen seconds from the first sample",
     "sources": [TAPE], "roles": ["input", "throughput"],
     "falsifier": "Open interest falls without any subsequent path difference, which would make the trigger "
                  "meaningless"},
    {"kind": "node", "id": "feature:positioning:basis", "layer": "feature", "type": "derived_feature",
     "meaning": "Mark price minus oracle price, the venue's own statement of premium or discount to the index",
     "status": "declared", "unit": "price difference",
     "availability": "on the tape every fifteen seconds from the first sample",
     "sources": [TAPE], "roles": ["conditioning_variable"],
     "falsifier": "Basis returns to zero instantly, which would say the venue reprices without friction"},
    {"kind": "node", "id": "feature:positioning:book-depth", "layer": "feature", "type": "derived_feature",
     "meaning": "Size available within ten basis points of the mid, which is what a forced flow consumes",
     "status": "declared", "unit": "notional at ten basis points",
     "availability": "on the tape every fifteen seconds. Median 3.5 million dollars on BTC, 8.7 million on ETH, "
                     "1,169 on GAS and 3,991 on SPX",
     "sources": [TAPE], "roles": ["throughput", "measurement_proxy"],
     "falsifier": "Depth is unchanged through a cascade, which would say the flow is absorbed without cost"},
    {"kind": "node", "id": "feature:leverage:margin-distance", "layer": "feature", "type": "derived_feature",
     "meaning": "How far the marginal leveraged position sits from its maintenance margin threshold",
     "status": "blocked", "unit": "percent of notional",
     "blocker": "account level leverage is not public. Open interest and funding are visible, positions are not, "
                "so margin distance can only be inferred from a book and an aggregate",
     "availability": "not reachable",
     "sources": ["none"], "roles": ["conditioning_variable"],
     "falsifier": "A public leverage or margin aggregate appears and the inference becomes unnecessary"},
    {"kind": "node", "id": "mechanism:leverage:forced-deleveraging", "layer": "mechanism", "type": "mechanism",
     "meaning": "The venue engine closes a position when maintenance margin is crossed, so the resulting flow is "
                "price insensitive by rule rather than by opinion",
     "status": "declared", "unit": "not applicable",
     "availability": "stated in docs/plan/cascade-protocol.md, committed before collection",
     "sources": [TAPE], "roles": ["input"],
     "falsifier": "Observed closings turn out to be voluntary at the prices where the threshold should bind"},
    {"kind": "node", "id": "event:leverage:liquidation-cascade", "layer": "event", "type": "event",
     "meaning": "A sample where the price move exceeds three trailing deviations and open interest falls by one "
                "percent against its trailing median, the declared trigger",
     "status": "blocked", "unit": "event",
     "blocker": "zero triggers in roughly 440 minutes across four markets. The trigger is declared and armed, "
                "and no cascade has been observed yet",
     "availability": "results/cascade-tape.json counts triggers per market",
     "sources": [TAPE], "roles": ["event"],
     "falsifier": "Triggers are never observed, which would leave the conditional path untestable on this tape"},
    {"kind": "node", "id": "claim:cascade:conditional-path", "layer": "claim", "type": "claim",
     "meaning": "After a trigger fires, the path at one, five, fifteen and sixty samples is measurably different "
                "from an unconditional path in the same market",
     "status": "declared", "unit": "distribution of returns after the trigger",
     "availability": "not yet measurable: it needs triggers",
     "sources": [TAPE], "roles": ["outcome"],
     "falsifier": "Post trigger paths are indistinguishable from the unconditional distribution"},
    {"kind": "node", "id": "experiment:cascade:protocol", "layer": "experiment", "type": "experiment",
     "meaning": "The pre-registered cascade protocol: declared trigger, declared measurement points, clustering "
                "against a Poisson null, and a stated ceiling of descriptive until a cascade is observed",
     "status": "declared", "unit": "not applicable",
     "availability": "docs/plan/cascade-protocol.md, committed before the first sample",
     "sources": [TAPE], "roles": ["benchmark"],
     "falsifier": "The protocol is amended after data arrives, which would void it"},
]
for market in ("btc", "eth", "gas", "spx"):
    NODES.append({
        "kind": "node", "id": f"asset:perp:{market}", "layer": "asset", "type": "asset",
        "meaning": f"The {market.upper()} perpetual contract on the venue, a twenty four hour instrument where a "
                   f"short is available without borrow",
        "status": "declared", "unit": "contract",
        "availability": "taped every fifteen seconds since the first sample",
        "sources": [TAPE], "roles": ["outcome", "execution"],
        "falsifier": f"The {market.upper()} market is delisted or its book stops publishing",
    })

EDGES = [
    ("e-positioning-dataset-funding", TAPE, "feature:positioning:funding-rate", "feeds"),
    ("e-positioning-dataset-oi", TAPE, "feature:positioning:open-interest", "feeds"),
    ("e-positioning-dataset-basis", TAPE, "feature:positioning:basis", "feeds"),
    ("e-positioning-dataset-depth", TAPE, "feature:positioning:book-depth", "feeds"),
    ("e-positioning-oi-mechanism", "feature:positioning:open-interest",
     "mechanism:leverage:forced-deleveraging", "measures"),
    ("e-positioning-funding-mechanism", "feature:positioning:funding-rate",
     "mechanism:leverage:forced-deleveraging", "conditions"),
    ("e-positioning-mechanism-event", "mechanism:leverage:forced-deleveraging",
     "event:leverage:liquidation-cascade", "produces"),
    ("e-positioning-event-claim", "event:leverage:liquidation-cascade", "claim:cascade:conditional-path",
     "gates"),
    ("e-positioning-claim-experiment", "claim:cascade:conditional-path", "experiment:cascade:protocol",
     "tested_by"),
    ("e-positioning-depth-claim", "feature:positioning:book-depth", "claim:cascade:conditional-path",
     "measures"),
    ("e-positioning-margin-claim", "feature:leverage:margin-distance", "claim:cascade:conditional-path",
     "conditions"),
]
for market in ("btc", "eth", "gas", "spx"):
    EDGES.append((f"e-positioning-{market}-tape", f"asset:perp:{market}", TAPE, "observes"))

RECORDS = NODES + [{"kind": "edge", "id": edge_id, "from": source, "to": target, "relation": relation,
                    "status": "declared", "condition": "Declared in the positioning family on 2026-10-04",
                    "falsifier": "Remove the edge when its condition stops holding"}
                   for edge_id, source, target, relation in EDGES]


def main() -> int:
    lines = [line for line in MANIFEST.read_text().splitlines() if line.strip()]
    ids = {row["id"] for row in RECORDS}
    kept = [line for line in lines if json.loads(line).get("id") not in ids]
    with MANIFEST.open("w") as handle:
        for line in kept:
            handle.write(line + "\n")
        for record in RECORDS:
            handle.write(json.dumps(record) + "\n")
    fragment = ROOT / "docs" / "scan" / "positioning-nodes.jsonl"
    with fragment.open("w") as handle:
        for record in RECORDS:
            handle.write(json.dumps(record) + "\n")
    print(f"replaced {len(lines) - len(kept)} lines, wrote {len(NODES)} nodes and {len(EDGES)} edges, "
          f"and mirrored them to {fragment.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
