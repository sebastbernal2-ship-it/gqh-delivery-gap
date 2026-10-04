# Specialist registry

A specialist is a data bundle with a declared question, never an architecture in search of data.
The council may only admit a specialist that appears in `registry.jsonl` with every required field.

## Required fields

`id`, `data_bundle`, `modality`, `information_cutoff`, `horizon`, `target`, `features_ref`,
`recipe`, `calibration`, `decision_type`, `owner`, `status`, `evidence`.

`status` is one of `evaluated` (has a result artifact), `implemented` (runs, no published result),
`data_gated` (code ready, waiting on data), or `retired`.

## Rules

1. One bundle per specialist. Two specialists that read the same input must be merged or one must
   justify a distinct question in writing.
2. Architecture variation is a separate axis. When two architectures read the same bundle, they are
   compared under declared budgets and the loser is recorded, not deleted.
3. Every entry names the artifact that carries its evidence. An entry whose artifact is missing is
   invalid.
4. The registry is checked by `tests/test_specialist_registry.py` on every `make test`.
