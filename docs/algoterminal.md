# The algoterminal link

This study uses the QuantGraph and the association engine from `algoterminal-data`. This file owns the
linkage contract: what is read, what we must author, and what stays theirs.

## How the link works

Read only. We never edit their YAML, their registries or their code.

```
ALGOTERMINAL_DIR=/path/to/algoterminal-data    # optional; defaults to ~/algoterminal-data
make graph                                      # resolve every node, source and representation
```

`make check` runs the same resolution when the checkout is present, and **skips with a note when it is
not**. A missing sibling checkout must never fail this repo.

## The contract

| In our logs | Meaning | What the link checks |
|---|---|---|
| `node_resolved` | The graph already has this node | It exists in `graph/quant_graph.yaml` |
| `node_proposed` | The graph does not have it, and we need it | It does **not** exist, and it carries a layer, a type and a reason |
| `source_resolved` | The source inventory already reaches this | It exists in `graph/source_inventory.yaml` |
| `source_proposed` | It does not, and we need it | It does **not** exist, and it carries a reason |
| edge `from_node` / `to_node` | The two endpoints | Each is either in the graph or declared in the same log |
| edge `representation_source` | Where the measurement comes from | One source or a list; each is in the inventory or declared |

Three rules keep it honest. Every edge endpoint is declared. Every declaration is used by an edge, or it
is decoration and fails. And a node we propose must not already exist, because then we should be
resolving it instead.

## What the stack gives us

- **The schema.** Typed layers, node types, semantic edge types, and epistemic status separated from
  meaning: `structural, observed, derived, hypothesized, proposed, partial, supported, rejected,
  constrained`, with origins such as `source_schema`, `domain_knowledge`, `empirical_test`.
- **The association engine.** Role-polymorphic all-pairs enumeration, twenty registered methods,
  representation handling, blocked and unsupported outcomes kept as records, deterministic evidence
  records, causal envelopes with a declared ceiling, and an opportunity registry with promotion gates.
- **Validators.** Ten of them, plus graph integrity reporting.
- **Sources already reachable** (46 ids, 19 sources): SEC EDGAR submissions, EIA petroleum and EIA-930
  regional electricity, FRED, yfinance and stooq daily bars, CFTC COT, NOAA NCEI and AIS, EPA ECHO,
  USGS earthquake, NASA POWER, NASA FIRMS, Landsat, Copernicus, World Bank, Wikipedia pageviews.

## The audit finding: the machine is theirs, the node space is ours

Measured 2026-10-03 against 7,517 node ids: **our mechanism's node space is essentially absent from the
graph.**

| We need | In the graph |
|---|---|
| Datacenter, compute, GPU, interconnection queue, transformer, turbine, cooling, backlog, guidance, 8-K | **No nodes** |
| "Power" nodes | Present only in the refinery and petroleum sense |
| Feature nodes (63 in total) | Weather exposure, tanker arrival and draft, refinery observation — energy and refining |
| Assets, entities | 3,232 assets and 1,899 entities, dominated by a 5,933-line EPA refinery catalog |

So the linkage gives us the **method, the machine and public-source connectors**, not our content. The
content is authored here as `node_proposed` declarations, which is exactly what the schema is for.

The local cross-layer contract is `docs/scan/quantgraph.jsonl`. It declares identity, sources, raw fields,
features, mechanisms, controls, outcomes, evidence, experiments, strategies, rules and implementations.
It now contains 418 nodes and 1,056 edges, including 325 proposed registry nodes kept inactive until
their representations are verified. `scripts/check_quantgraph_manifest.py` validates it before data
arrives. It is a local mirror, not a write-through to the sibling repository. `make graph` remains
read-only and resolves the chain log against the sibling graph.

## Data we reuse, and data we must add

| Need | Reuse | Add |
|---|---|---|
| Filings and disclosures | `source:sec` | — |
| Generator schedule vintages | — | `source:eia-860m` |
| Regional electricity | `source:eia-930` | — |
| Site progress, thermal and optical | `source:landsat`, `source:nasa-firms`, `source:copernicus` | — |
| Macro, rates | `source:fred` | — |
| Daily equity bars | `source:market` (yfinance, stooq) | — |
| Option chains, intraday quotes | — | `source:databento-options`, or Massive |
| Compute price index | — | `source:ornn-ocpi` |
| Perpetual funding and order book | — | `source:hyperliquid-archive` |

## What stays theirs

Their validators and their engine remain authoritative in their repository, and their registries are not
ours to edit. Our chain logs, the assumption register, the scope caps and the freeze are ours. Their
node ids are the shared namespace, so an artifact we produce can be read on their side and the reverse.

## Open question for the captain

Running their association engine over **our** nodes requires the nodes to exist somewhere it can read.
Two routes: declare them in their graph through their own conventions, which edits a repository that is
not ours, or vendor the schema and the enumeration contracts into this repo. The first reuses everything
and makes artifacts portable; the second keeps their repo untouched. The vocabulary is identical either
way, so our logs written today work under both.
