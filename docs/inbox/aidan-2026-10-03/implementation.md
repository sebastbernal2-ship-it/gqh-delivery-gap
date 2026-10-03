# Proposed implementation contracts and scaling plan

Owner: aidanq06. Design handoff only. No engines or cluster jobs are created by this document.

Use the existing technical-boundaries proposal for component homes. This document specifies the
seams so different implementations can be developed without sharing internal code or assumptions.
The workflow and ownership files remain authoritative. Claim components before implementation.

## Flow and boundaries

Source adapters → immutable observations → reviewed facts → as-of event panel → signal → target
positions → execution/accounting → result artifacts → figures and note.

Data processing cannot make trade decisions. Strategy functions cannot call a current API during
historical replay. Cluster wrappers cannot implement a different trading rule. Reporting cannot
recompute performance using undocumented alternative accounting. A faster engine implements the
same contract and is checked against the reference implementation on identical fixtures.

## Contract checklist

Every implemented component's INTERFACE.md must specify:

- Named owner, contract version, purpose, input/output schema and compatible consumer versions.
- Identifier rules, units/currencies, price scales, null semantics, timestamp precision/timezone.
- Ordering, duplicate handling, corrections, late arrivals, idempotence and failure behavior.
- Information cutoff and output availability, not just economic reference dates.
- Minimal fixture and run command; expected output and numeric tolerances.
- Resource requirements and budget, provenance, retry/resume behavior and limitations.

Proposed artifact boundaries, to be finalized when implemented:

| Artifact | Required meaning |
|---|---|
| Observation | Source identity/version, source and receive/availability times, immutable content reference/hash |
| Extracted fact | Entity/project, field, value/unit, economic period, source span, extractor version and review status |
| Event | Earlier expectation and new measurement for comparable scope, first availability, exposure links and shock cluster |
| Feature panel | As-of cutoff, historical eligibility, input manifest, feature definitions; future labels stored separately |
| Target positions | Decision time, instrument, signed quantity, reason/event IDs, policy and risk configuration |
| Fill/accounting ledger | Order/fill times, quantity/price, fees, financing, corporate actions, marks and cash/inventory reconciliation |
| Run result | Code revision, configuration/input/environment hashes, split identity, seed, metrics and failure/coverage report |

Never coerce unknown exposure to zero. Never give the strategy future realization labels as inputs.
Preserve missing and censored observations. Raw bytes plus transformations own reproducibility;
database tables are versioned views, not independent competing truths.

## HiPerGator approaches stay separate

A classical research path handles extraction evaluation, event-panel computation, development
folds and risk simulations. An experimental path handles quantum circuit/sampling benchmarks or
constrained optimization. Optional extractor training can have its own job directory and owner.
These are different workloads, not multiple copies of strategy logic.

Each job calls a versioned component contract and records resource requests, environment, inputs,
seed, output destination, completion and resource usage. Start with a tiny CPU fixture. Scale only
when the same result survives the environment change. Coordinate the reported shared allocation;
do not treat it as exclusive capacity. Use checkpoint/resume and avoid redundant raw-data downloads.

Quantum outputs are scenario/risk or optimization artifacts. Compare against a classical result
with the same inputs and downstream decision rule. Include full runtime and quality, not circuit
runtime alone. A cluster queue or remote model is not assumed to sit in the live order loop.

## Test and promotion gates

1. Contract fixtures: units, dates, nulls, splits/dividends, shorts/fees, partial fills and accounting identities.
2. Tiny integration: source parsing to final result; input hashes and deterministic rerun.
3. Historical development: point-in-time exclusions, costs, factor attribution and declared variants.
4. Cluster/fast parity: equivalent output within stated tolerance, plus failure/restart tests.
5. Frozen final evaluation: designated owner, locked configuration, full reporting regardless of outcome.

Do not proliferate languages, services, directories or tests without a real boundary to validate.
The small pilot establishes engineering feasibility, not an inductive proof of market profitability.

## Reproducible delivery

The judge-facing path should run a bounded study without the team's cluster account. If licensed
inputs cannot be redistributed, supply exact retrieval instructions, hashes and cost/access needs,
plus distributable fixtures; distinguish fixture reproduction from reproducing licensed results.
Pin dependencies when runtime code is added. Keep raw data, credentials and large checkpoints out
of Git. A final manifest links every reported figure and number to the run that produced it.
