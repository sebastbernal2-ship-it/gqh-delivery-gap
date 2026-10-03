# Prompt for the algoterminal-data session: add the AI-infrastructure node space

Copy everything between the markers into the running algoterminal session.

--- BEGIN PROMPT ---

## Task

Add the AI-infrastructure node space, its representations and its missing sources to the QuantGraph, so
that a sibling study in the repo `projects/quanthacks` can resolve its nodes against this graph and run
the association engine over them. That sibling study is read-only against this repo: it never edits your
YAML, registries or code, and it resolves by node id.

Authoritative documents in this repo stay authoritative: `research/association_promotion_causal_implementation_plan.md`,
`research/association_system_plan.md`, `graph/edge_semantics.yaml`, `graph/opportunity_registry.yaml`,
`graph/source_inventory.yaml`, and the validators. This task adds nodes and sources; it does not
reinterpret their contracts.

## Hard constraints

Preserve every existing invariant, and in particular:

1. Do not change opportunity status, graph semantics, or causal status. No association result from this
   task promotes anything.
2. Do not fetch data. Enumerating metadata cases must not trigger a provider call.
3. Do not invent event, regime, control, residual, timing or availability inputs.
4. Do not manufacture evidence to obtain a supported result. If something is unverified, record it as
   unverified with its blocker.
5. Node identity is stable and separate from any analytical role. Do not assign a permanent role to a
   node in this task.
6. Meaning, epistemic status and origin stay separate fields, per `graph/edge_semantics.yaml`.
7. Preserve all dirty and untracked work. Do not reset, clean broadly, or edit
   `research/strategy-progress-explained.md`.
8. Keep the implementation Python-first, and add tests beside the code they exercise.

## Package 1: sources

Add these to `graph/source_inventory.yaml`, following the existing schema exactly (id, provider,
datasets, raw fields, availability, entitlement).

| id | provider | why | entitlement |
|---|---|---|---|
| `source:eia-860m` | EIA Form 860M monthly generator inventory | promised versus realized energization dates by plant and generator | public, no key |
| `source:databento-options` | Databento or Massive | option chains and intraday quotes for the expression and event windows | **unverified**, report as unverified with the blocker |
| `source:ornn-ocpi` | Ornn Compute Price Index | realized scarcity price of deliverable compute; executed rentals, not list prices | public current values, full history is a paid tier. Record that |
| `source:hyperliquid-archive` | Hyperliquid S3 archive | perpetual funding, open interest and order book history | public archive. Record that L4 exists and is not assumed continuous |

For each: the availability and point-in-time fields are the important part. If a release time, vintage
identity or archive coverage is unknown, say so rather than guessing.

## Package 2: nodes

Use these ids verbatim. The sibling study already declares them, and its link check compares ids, so a
rename breaks it. Each node carries `type`, `metadata.status`, and `layer` as existing nodes do. Where a
formula or mapping is not yet specified, use the existing convention for an unfinished definition, such
as `pending_preregistration`.

**Required by the sibling study's first chain (seven):**

| id | layer | type | meaning |
|---|---|---|---|
| `feature:power:planned-capacity-vintage` | feature | derived_feature | promised energization dates as published in a monthly vintage |
| `feature:power:energized-capacity` | feature | derived_feature | what actually came online, with its publication time |
| `feature:power:delivery-revision` | feature | derived_feature | the published change between promised and realized delivery for a named project |
| `outcome:firm:revenue-timing-revision` | outcome | outcome | whose revenue or cost timing moves, and by how much |
| `outcome:firm:abnormal-return` | outcome | outcome | the price side: return net of a matched benchmark at the chosen horizon |
| `feature:compute:rental-price-index` | feature | derived_feature | realized scarcity price of deliverable compute |
| `feature:positioning:perp-funding-rate` | feature | derived_feature | what leveraged participants pay to stay long |

**The wider space, so the graph covers the mechanism rather than one path through it (bounded to these):**

| id | layer | type |
|---|---|---|
| `entity:datacenter:site` | entity | entity |
| `event:sec:8k-material-agreement` | event | event |
| `feature:power:interconnection-queue-position` | feature | derived_feature |
| `feature:power:transformer-lead-time` | feature | derived_feature |
| `feature:equipment:turbine-backlog` | feature | derived_feature |
| `feature:water:cooling-supply-constraint` | feature | derived_feature |
| `feature:firm:backlog-timing` | feature | derived_feature |
| `feature:firm:guidance-revision` | feature | derived_feature |
| `feature:positioning:perp-open-interest` | feature | derived_feature |
| `feature:compute:rental-price-volatility` | feature | derived_feature |

If any of these already exists under a different id, do not duplicate it. Report the existing id instead,
so the sibling study can adopt it.

## Package 3: representations

For each node in Packages 2, declare representations as **metadata only**. No fetching. The fields that
matter, following the representation contract in `research/association_system_plan.md` section 3.2:
kind, source, dataset or field reference, unit, frequency and observation clock, observation timestamp,
usable timestamp, release timestamp, decision cutoff policy, vintage selector, missing-value policy,
availability and point-in-time status.

Examples of what "several representations of one node" means here, and the reason this matters:

- `feature:compute:rental-price-index`: the published index, a listed future if one lists, and a
  bilateral rental rate are three representations with different units and clocks, not one series.
- `feature:power:delivery-revision`: the monthly vintage difference and a single filing are two
  representations with different release timing.
- `feature:positioning:perp-funding-rate`: one representation per venue.

Where a representation cannot be bound yet, record it as metadata with a structured issue rather than
dropping it.

## Package 4: domain edges only

Add the semantic, domain-knowledge edges that are true regardless of any trade: for example that a
planned date is derived from a vintage, that the compute index measures rental scarcity, that an
interconnection queue gates energization. Use the existing semantic types, set epistemic status to
`hypothesized` or `proposed`, and set origin to `domain_knowledge` or `research_proposal`.

Do **not** add the sibling study's trade path as graph edges. Its claim path lives in its own chain log.
The graph carries what is true about the world; the study carries what it claims.

## Package 5: coverage and multiplicity

1. Ensure the new nodes fall inside the all-pairs coverage records, so every pair has exactly one
   canonical coverage record, with blocked or unsupported pairs recorded as structured issues.
2. Count comparisons before any ranking, as the design requires.
3. Keep the causal ceiling at descriptive for anything involving these nodes. No estimator or control
   search.
4. Do not run an all-pairs family over the new nodes unless it is metadata-only and cannot fetch.

## Package 6: report back

Reply in this session with:

1. The exact list of node ids and source ids that landed, and any that already existed under another id.
2. The exact list of representations declared, with the fields that could not be bound and why.
3. Validator output, verbatim, for the commands below.
4. Any new blocker, recorded as a blocker rather than worked around.
5. A one-line statement of what remains unverified, especially entitlement and availability.

## Verification

```sh foreign-repo=algoterminal-data
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'
python scripts/validate_quant_graph.py
python scripts/validate_source_inventory.py
python scripts/validate_opportunity_registry.py
python scripts/validate_decomposition_registry.py
python scripts/validate_representation_bindings.py
python scripts/validate_causal_envelopes.py
python scripts/validate_multi_model_decomposition.py
python scripts/validate_tradability.py
python scripts/validate_frozen_validation.py
python scripts/validate_artifact_registry.py
python scripts/report_graph_integrity.py
git diff --check
```

## Stop conditions

Stop and report if: a validator cannot pass without weakening a contract; a node id cannot be authored
without inventing an input; a source cannot be added without claiming unverified entitlement; or the work
needs a change to an opportunity, a causal status, or an existing node's identity.

## Out of scope

Opportunity promotion. Strategy status. Causal claims. Data downloads. Any edit to the sibling study's
repository. Any change to existing node identities, edge semantics or existing sources.

--- END PROMPT ---

## Coordination note for our side

When their session reports which ids landed, our `docs/chains/t-capacity-revision.jsonl` must flip those
lines from `node_proposed` to `node_resolved`, because our link check treats a proposed node that now
exists as an error, and the reverse as an error too. That is deliberate: it keeps the two repos agreeing
about what exists. The flip is a one-line-per-node edit and a new commit.

## Amendment, 2026-10-03, after the chain was tightened

1. One more required node: `outcome:firm:abnormal-return`. The price side of the chain had no node, so
   the price test had nothing to point at. Without it the mispricing claim cannot be represented.
2. Please also report, without creating anything, which of these already exist as `asset` nodes:
   `PWR`, `ETN`, `EME`, `DLR`. Our pilot universe is undecided and these are the candidates from both
   handoffs. If they exist, send the ids so we resolve them instead of authoring a placeholder.
