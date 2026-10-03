# Follow-up message for the algoterminal-data session

Copy everything between the markers.

--- BEGIN MESSAGE ---

## Context

This is the sibling study that keeps a read-only link into this repo. Your graph already carries six of
our seven chain nodes, all four sources, eighteen representations and the canonical coverage, and that
work is committed here as `38d122e`. Nothing of yours was touched by that commit.

## 1. One node is still missing

`outcome:firm:abnormal-return` was added to our chain after you had started. Please author it the same
way as its siblings:

- id: `outcome:firm:abnormal-return`, layer `outcome`, type `outcome`
- meaning: the price side, return net of a matched benchmark at the chosen horizon
- `epistemic_status: unverified`, `origin: research_proposal`, `availability_status: unverified`,
  `point_in_time_status: unverified`, and a `status_blocker` in your usual form

Add its representation with the standard field set and a blocking issue where a field cannot be bound,
and any domain edges that are true regardless of any trade, for example that a revenue-timing revision
is hypothesized to lead the abnormal return. Do **not** add our trade path: our claim path lives in our
chain log, and the graph carries what is true about the world.

The id must match exactly. Our link check compares ids, and it fails on a rename in either direction.

## 2. Report, do not create: do any of these exist as asset nodes

`PWR`, `ETN`, `EME`, `DLR`. Send the ids if they exist, plus any representation ids attached to them.
Our pilot universe is undecided and these are the candidates from both handoffs, so we would rather
resolve an existing asset than author a placeholder.

## 3. Keep your invariants

No opportunity promotion, no causal status change, no comparison run that would need inputs you do not
have, and the causal ceiling stays descriptive for anything involving these nodes. Blocker recorded, not
worked around.

## 4. Housekeeping worth five minutes

- **About 165 untracked entries sit on this branch**, including the association engine, its tests and the
  research reports. Nothing is committed, so one `git clean -fd` or a hard reset destroys days of work.
  Commit them, or park them deliberately and say so.
- **An unzipped spreadsheet sits at the repo root**: `[Content_Types].xml`, `_rels/`, `docProps/`, `xl/`.
  Do not commit it, and remove it if it is not input data you need.

## 5. Reply with

1. The exact ids that landed, and any that already existed under another id.
2. The asset lookup result from section 2.
3. Validator output, verbatim, for the commands below.
4. Any new blocker, recorded as a blocker.
5. One line on what remains unverified.

```sh foreign-repo=algoterminal-data
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'
python3 scripts/validate_quant_graph.py
python3 scripts/validate_source_inventory.py
python3 scripts/validate_ai_infrastructure.py
python3 scripts/report_graph_integrity.py
git diff --check
```

**Stop and say so** if the node cannot be authored without inventing an input, or if a validator needs a
contract weakened to pass.

--- END MESSAGE ---

## Note for our side

When the node lands, flip its line in `docs/chains/t-capacity-revision.jsonl` from `node_proposed` to
`node_resolved`, because the link check treats a proposed node that exists as an error. That is the last
of the seven.
