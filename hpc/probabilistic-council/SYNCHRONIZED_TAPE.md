# Synchronized tape development protocol

This is the next engineering gate after [the book-only experiment](INFORMATION_VIEWS.md).
It does not introduce a trading rule or reopen a competition holdout. The strategy's economic
mechanism still lives in the shared research documents; this component tests whether a fast
probabilistic model can consume different information streams without leaking future data.

## Declared before inspecting the candidate

Select the first lexicographic nonpartitioned `l4_l2book` and `l4_trades` Parquet files from
`gionuibk/hyperliquidL2Book-v2` at revision
`e28ac5f9139033a3e991b3db52702dad1350683e`. Select by catalog names and publisher byte sizes,
never price movements, model scores or liquidation frequency. Verify publisher LFS SHA-256 and
byte size before parsing. The two files total 50,879,390 bytes. The acquisition plan is
[pinned here](synchronized_candidate_plan.json).

**Hypothesis:** these two archive families contain overlapping BTC book and trade observations
with sufficient resolution to construct a causal, development-only multi-stream panel.
**Falsifier:** empty overlap, ambiguous trade identity/side, unsuitable timestamp resolution,
or insufficient continuous history prevents a valid panel. A failed candidate is reported;
we do not silently replace it after observing outcomes.

Readiness precedes training: inspect schemas, exact integer timestamp units, coin coverage,
clock ranges, duplicate identities, book ordering and gap distributions. File prefixes containing
`l4` do not prove order-level data. Do not treat trade prints as account fills, or infer liquidation
markers from price moves. Do not interpret a `server_time` column as a verified local receive
clock without source evidence. An assumed latency must stay labelled `retrospective_assumption`.

If readiness passes, retain the existing seven-view experiment: A book liquidity, B observed trade
flow, C trailing price/volatility; AB/AC/BC/ABC combinations; numeric and tiny JevLike baselines.
Use the existing five chronological roles and fixed training budgets. No architecture selection
on the evaluation block. Separate sessions, recording gaps and overlapping trailing histories
must be audited before claiming independent evidence. If readiness fails, build and test the
validation seam, but do not manufacture a training result.

The engineering floor is ten minutes of overlapping recorded clocks. This is only a rejection
rule for a tiny smoke sample, **not** a claim that ten minutes, two years, or any calendar span
is adequate evidence of trading performance. The competition split remains owned by
[the frozen brief](../../docs/brief.md). No price-return labels are computed in this audit.

## Why these distinctions matter

The official [node schemas](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/nodes/l1-data-schemas)
describe separate trade, order-status, raw-book-diff and liquidation-ledger streams. Order-level
snapshots plus subsequent order statuses are needed to reconstruct queue information. The
mirror's snapshot columns must be inspected against that distinction; an aggregated book cannot
support claims about exact queue position or fill probability.

The original [acquisition utility](https://github.com/sebastbernal2-ship-it/gqh-delivery-gap/blob/research/handoff-event-readiness/src/event_readiness/mirror_candidates.py)
lives on the teammate's `research/handoff-event-readiness` branch. It pins revisions, checks SHA-256/size,
uses verified HTTPS and suppresses signed redirect URLs in receipts. This experiment uses that
utility for acquisition only; the adapter and audit must be runnable within this component.
Raw Parquet, account identifiers, per-case forecasts and checkpoints stay outside Git. Public
receipts contain only provenance, aggregate coverage and quality results.

## Candidate result and what changed

The generated [audit receipt](experiment_receipts/btc_synchronized_audit_20261003.json) is the
owner of the measurements. The selected BTC streams overlap for about 288 seconds. Their
payloads conform to the official [WebSocket snapshot and trade shapes](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket/subscriptions),
including venue millisecond clocks; the outer Parquet clock has nanosecond resolution.
Despite the filenames, these are aggregated L2 snapshots and trade prints. They contain neither
order-level queue identities nor verified liquidation events. The initial recorded/event offsets
are much larger than subsequent offsets. An event-only join would make information appear
available before it was recorded.

`synchronized_tape.py` now verifies file hashes/sizes and exact schema, extracts BTC only,
projects away wallet/hash payload fields, and deduplicates exact retransmissions at their first
recorded availability. Trade identity uses `(event time, coin, tid)` as the official documentation
specifies, not `tid` alone; this adapter fixes coin to BTC. Conflicting identities fail. Books must
have positive finite, strictly ordered, uncrossed depth. A late older book never rewinds the state.

The causal join uses only messages with recorded clock at or before decision time. It rejects
book age and history gaps above two seconds. Fixed six-second decision spacing produces
liquidity, observed trade flow and trailing price/volatility features with source references.
Observed flow uses reported B-minus-A sizes; aggressor-side meaning remains unverified. Absence
of observed trades is explicitly not proof of zero venue volume or a complete feed. Initial stale
books are rejected. There are usable feature states, but the candidate fails the duration gate;
no training, model selection, return labels, P&L or quantum experiment was run on it.

Book lookup uses a monotonic prefix of already-recorded states with binary searches; rolling
features scan the retained window instead of repeatedly scanning the full archive. This is a
research adapter, not a measured HFT serving implementation.

## Reproduce

Use Python 3.12 with PyArrow 23.0.1 at the Parquet boundary. Core clock/join tests need only the
standard library. From this component directory, download the two public files using their pinned
revision and store each under its SHA-256 filename in a local `OBJECTS` directory. The URLs are
formed from the dataset/revision/path in the committed plan. For each entry, the command is:

```sh
curl --fail --location --proto '=https' --proto-redir '=https' \
  --max-filesize EXPECTED_BYTES \
  'https://huggingface.co/datasets/DATASET/resolve/REVISION/PATH' \
  --output OBJECTS/SHA256
```

Replace the placeholders with the corresponding plan values; do not use a floating `main` URL.
Then run:

```sh
python synchronized_tape.py --plan synchronized_candidate_plan.json \
  --objects OBJECTS --output NEW_AUDIT_DIRECTORY
python -m unittest discover -s tests -p test_synchronized_tape.py -v
```

The audit refuses changed bytes or an existing output directory. `audit.json` is aggregate and
shareable; `states.jsonl` contains research feature states and stays outside Git. The receipt pins
both source hashes, the plan, adapter and normalized states. The published receipt was generated
using the checked adapter; no raw data or outcome-dependent choice is committed.

Ten adversarial tests cover declared clock units, early-arrival rejection, retransmissions,
identity conflicts, invalid prices/side/coin, future-arrival and future-price isolation, late old
books, staleness/history gaps, old initial trade batches, file tampering, short-sample rejection
and aggregate receipt projection. Full HPC verification passes 55 tests (17 kdb and 38 council).

## Next data gate

Extend acquisition by a declared chronological rule over multiple sessions, chosen on coverage
metadata before outcomes. Reconcile cross-file retransmissions, recording gaps and availability
semantics, then define future labels and purge all five role boundaries. A long outer-clock range
with missing sessions does not count as continuous coverage. Liquidation specialists require a
separate synchronized marked source; queue/fill specialists require order-level events. This
candidate resolves the existence of overlapping book/trade data, not these remaining blockers.
