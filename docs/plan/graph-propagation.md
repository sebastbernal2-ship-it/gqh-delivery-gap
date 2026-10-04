# Graph propagation and delineation

Method for the deepening pass. It exists to make the graph hold more truth and to read edge off the
graph, not to grade paths as alive or dead. The classification is decomposed or not yet decomposed.

## One, the quantitative layer

Every node that has data gets its distribution written down, not a verdict. For each sample attached to a
node the builder records the count, the centre, the spread, the shape, and the tails: mean and standard
deviation, quantiles, the ratio of the ninetieth percentile to the median, skew, kurtosis, and the share
of the top one percent. A node with no data is marked `to_be_sampled`. A tight distribution and a fat tail
are both structure.

## Two, the delineation layer

The graph keeps an index of itself:

- counts by layer, by status and by connection type, with the degree distribution;
- coverage: how many nodes carry evidence, how many connections carry a condition and a falsifier;
- chain integrity: every hop address `hop:<chain>:NN` must have its neighbours `NN-1` and `NN+1`;
- islands: which components are unreachable from an anchor.

## Three, the hidden layer

Hidden objects are the point of this pass. Four kinds:

- **Hidden nodes**: identifiers that are referenced by a connection, a chain or a dig and have no node
  record of their own.
- **Hidden edges**: sibling sub-nodes under the same parent whose names share semantic tokens and which
  have no direct connection. Each proposal carries a condition and a falsifier, like every inferred edge.
- **Hidden gaps**: broken hops, digs with no payer, core nodes under the connection target, and nodes
  without evidence.
- **Hidden assumptions**: inferred connections missing a condition or a falsifier, and links in a chain
  with no declared evidence tier.

## Four, the propagation layer

Propagation walks from measured truth to a payer along typed links, in the order the economics move:

    constraint -> price -> margin -> capex -> cash flow -> equity

Each move is a rule with a name, the edge types it may traverse, and the assumption it needs. A path
carries its nodes, its rule sequence, its evidence floor, the greatest assumption on it, and whether the
data to test it is already in the repository. Paths are ranked by evidence floor and testability, never
discarded, because an untestable path today is a data request, not a dead end.

The cascade branch is a parallel propagation family with its own order:

    disclosure -> forced hedge -> flow -> depth -> dislocation -> reversion

## Five, what this produces

- `docs/scan/distributions.jsonl`: per-node empirical description of every sample we hold.
- `docs/scan/hidden-objects.jsonl`: hidden nodes, edges, gaps and assumptions, each with its reason.
- `docs/scan/propagation.jsonl`: propagated paths from measured truth to payers, with their greatest
  assumption and their test status.
- `docs/scan/graph-delineation.json`: the self index of the graph.
- `results/graph-propagation-summary.json`: the counts for all of the above.

## Reproduce

    python3 scripts/build_graph_propagation.py
    python3 scripts/render_graph_propagation.py
