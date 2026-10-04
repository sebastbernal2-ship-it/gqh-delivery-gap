# Validation and outstanding gates

Checked locally on 2026-10-03 against base `6da2e4b`, then integrated with `8359a29`. The commit containing this file and the run
receipt component digest identify the delivered version. Tests use fabricated evidence only.

## Completed

- **47 component tests passed:** exact decimal revisions and normalization scale; label-column
  rejection; current/prior document hashes and source spans; review/exposure abstention; issuer
  definition/unit/scope/target/security mismatches; balances versus guidance; future and stale
  expectations; an adversarial sealed record; DST and naive clocks; zero/negative denominators;
  idempotence/conflicting duplicates including same accession under a different ID; amendments;
  current-cluster exclusion, zero/nonzero MAD after the history threshold; deterministic input order; holidays, pre-open lag, half-days and
  calendar exhaustion; original ZIP and document byte checks; mutable version-path collision;
  document-key/count/hash mismatches; missing/orphan records; traversal; no canary/full-batch
  blending; optional query failure reporting; read-only SQL; stripping text-context snippets;
  exclusive output creation, duplicate JSON keys and a complete file-based feature CLI run.
- The CLI demo writes a reproducible feature payload, source/code hashes and a timestamped run
  receipt. Wall-clock metadata changes across runs; feature row hashes do not.
- **6 existing kdb exporter tests passed**. This does not validate q or remote HDB execution.
- `make test`: the first 13 listed existing test programs pass, then it fails at missing
  the missing `test_strategy_contracts.py` test program. No omitted test was claimed to pass.
- The calendar defect in the existing delivery panel was reproduced using only its two AST-extracted
  helper functions and a synthetic January 2020 date; no data fetch or model rerun was involved.

## Not completed / cannot be inferred

- No authenticated cloud inventory, Snowflake stage-byte receipt, TigerData quota query or remote
  SEC-job reconciliation on this computer. The read-only collector is tested with a fake cursor,
  not certified against the team's live warehouse. Table names/columns were checked against the
  repository's actual DDL; absent tables/grants are reported as failures.
- No real reviewed event feature panel, human source/exposure audit, market/sector action-adjusted
  panel, label builder, costs, walk-forward return study or economic significance result.
- No source-license adjudication, live execution, model training, q execution, database migration,
  deletion, or new data-provider spend.
- Existing global `make check` is blocked by the tracked `.vscode` root and missing component
  READMEs under `src/factors/` and `src/models/`. `scripts/check_paths.py` additionally reports
  missing current-main paths referenced by the Makefile and stale owner/history references.
  These are existing shell/integration issues, not green gates for this branch.
- The SEC overwrite, delivery month shift, full-panel imputation, ablation/null and old market
  index problems described in the audit remain in their existing components. Detection and
  documentation are not claims that those components have been repaired.
- Split/action/dividend/missing-bar/label-end/overlap-purge tests from the handoff belong to the
  unbuilt market/label bridge. The calendar helper is not a substitute for those tests.

## Reproduce

```sh
PYTHONPATH=src python3 -m unittest event_readiness.test_readiness -v
PYTHONPATH=src python3 -m event_readiness.run demo --out data/readiness/demo-v2.json
python3 -m unittest discover -s hpc/kdb-timeseries/tests -v
make secrets
git diff --check
```

Use a fresh demo output filename on every run. Full repository gates remain meaningful; record
and repair their actual failures with the owning workstream, not by deleting checks or adding
empty files. Do not re-run financial tests to validate plumbing or open the sealed window.
