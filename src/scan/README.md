# src/scan

The association scan: every declared pair of nodes, measured against its own generated null.

This exists because an association study fails in one specific way. It measures the pairs it happens to
have, ranks them, and reports the best one, which presents multiplicity as discovery. The rules here are
about the space rather than the numbers.

1. **Coverage before measurement.** The node space is declared in `docs/scan/nodes.jsonl`, and
   `scripts/check_scan.py` refuses a node that has neither a representation with a clock and an
   availability rule, nor a blocker explaining its absence. Missing series are recorded, not skipped.
2. **Multiplicity counted first.** Every pair of declared nodes appears once, and the count is printed
   before any statistic.
3. **The null is generated, not assumed.** Each pair is measured against a block shuffle of one series,
   which keeps short-run autocorrelation and destroys alignment, and against a twelve-month seasonal
   shift, which keeps seasonality and destroys the calendar match. A pair counts as a survivor only if it
   beats its own placebo, and the number that do is compared with the number expected by chance.
4. **Two corrections after measuring**, in `report.py`: one canonical series per node, so a node cannot
   vote three times through three correlated representations, and a specificity test, because a relation
   that appears in unrelated industries is a common factor and not the mechanism.

A survivor is a candidate for a mechanism conversation, never a strategy. Nothing in this module takes a
position.

## Owner

`sebastbernal2-ship-it` claims `src/scan/` in `OWNERS.md`.

## Use

```sh
python scripts/check_scan.py                      # the node space and the pair count
python scripts/run_association_scan.py --draws 200
```

## What the first pass found

Fifty-one series-level pairs measured across twenty-one declared nodes, of which twelve beat their own
null against 2.6 expected by chance. Applying the two corrections leaves three cross-family survivors
against 0.9 expected, and the specificity test attributes the only mechanism-relevant one to the
datacenter group rather than to the mechanism groups. The honest reading is that the scan found structure
in asset co-movement and in known macro relations, and no survivor that belongs to this mechanism.
