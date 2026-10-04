# From live captures to movement-risk training

The off-cluster adapter `prepare_live_execution_risk.py` closes the gap between
`record_execution_tape.py`, `export_execution_capture.py`, and the risk model.
It verifies the capture receipt, journal, inventory and every source object, then
checks that the exported Parquet records reproduce the journal exactly. It rejects
unsegmented clock reversals or wall/monotonic drift above the recorder's 100 ms bound.
No raw parsing or book reconstruction belongs on HiPerGator.

## Freeze the development role plan first

Create this JSON locally, outside the repo. Paths below are placeholders, not deployment paths.
The two digests pin bytes; obtain them with `sha256sum` before generating labels.

```json
{
  "schema_version": "execution-live-role-plan-v1",
  "scope": "development_only",
  "captures": [
    {
      "capture": "LOCAL_CAPTURE_DIRECTORY",
      "objects": "LOCAL_EXPORTED_OBJECT_DIRECTORY",
      "capture_receipt_sha256": "SHA256_OF_CAPTURE_JSON",
      "inventory_sha256": "SHA256_OF_INVENTORY_JSON"
    }
  ],
  "session_roles": {
    "2026-10-04": "training",
    "2026-10-05": "specialist_calibration",
    "2026-10-06": "gate_fit",
    "2026-10-07": "pool_calibration",
    "2026-10-08": "evaluation"
  }
}
```

Dates illustrate chronological roles, not an approved experiment or sufficient sample.
Assign whole UTC dates; repeated connections within a date are not independent sessions.
Every captured receive date must have a role. Roles must advance chronologically.
The adapter processes each capture/connection/UTC-date separately, so a reconnect or
midnight boundary requires fresh history and cannot borrow future labels from another segment.
An initial trade snapshot is available at receipt time, not at its older venue timestamp.

```bash
python export_execution_capture.py --capture LOCAL_CAPTURE --output LOCAL_OBJECTS
python prepare_live_execution_risk.py --plan LOCAL_PLAN_JSON --output NEW_LOCAL_CACHE
```

If any of the five roles has no usable cases, the output is only `coverage.json`.
It contains no prices, features, targets, paths or prediction rankings. No partial
cache is packaged as a training dataset. A complete development cache has the same
four arrays used by the existing risk trainer, with `availability_basis=local_receipt`
and row-level segment identifiers tied to pinned capture journals. The existing
[training and deployment contract](EXECUTION_RISK.md) remains the model authority.

## What the adapter establishes

It establishes data lineage, local receive-time ordering, segment isolation, whole-date
role separation and observed snapshot labels at 5/15/60 seconds. It does not prove
trade completeness, clock synchronization with the venue, fills, causal trading
advantage, calibration, HFT latency or statistical sufficiency. A 30-second history
and 60-second longest label require more than 95 seconds of overlapping book/trade
coverage for even the first candidate under the existing sampling rule. Book gaps
and staleness can exclude it. Large byte counts alone do not establish coverage.

The risk trainer still requires at least three dates each in training, gate-fit and
evaluation unless the explicitly named development smoke flag is used. This is an
engineering floor, not a power calculation. Capture substantially longer sessions
across different dates and regimes before comparing scratch, masked-pretrained,
A (book), B (trades), and AB specialists. Freeze that comparison before fitting;
select on development gate data, then evaluate once on its assigned development dates.
The competition holdout remains separate and unopened by this pipeline.

HiPerGator runs model fitting/calibration/evaluation on validated arrays. The public
[Hyperliquid subscription specification](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket/subscriptions)
defines the five-level fast book and trade stream used here. A successful smoke run
checks deployment only; it is not a substitute for a fresh multi-date experiment.
