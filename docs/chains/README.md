# Chain logs

One append-only log per thesis: `docs/chains/<thesis-id>.jsonl`. One JSON event per line.
This is the mechanism that keeps a chain from becoming scope creep or quiet overfitting, because the
dangerous moves fail `make check` instead of depending on discipline.

## Events

| Event | Fields | Notes |
|---|---|---|
| `edge_added` | edge, status, conditions, if_false, exposure_bound, mode, evidence (required when measured) | `if_false` must say what changes when the edge is false. "nothing" means delete the edge |
| `status_changed` | edge, from, to, evidence | An upgrade to `measured` needs an evidence path that exists |
| `bound_changed` | edge, from, to, reason | Raising a bound after the sealed window opens is an error |
| `edge_removed` | edge, reason | Removal is recorded, not silent |
| `decision` | choice, value, reason | Every degree of freedom we choose. The count feeds the multiple-testing deflation |
| `sealed_opened` | revision, run_plan | After this event: no new edges, no upgrades, no raised bounds |

Every event carries `ts`, `chain`, `event` and `phase` (development or sealed).

## The caps

- At most **8** active edges in the pilot.
- At most **3** edges without a measurement.
- At most **1** P&L-carrying role. The pilot holds one expression.

Exceeding a cap is an error, and the fix is to shorten the chain, not to raise the cap. If the work
genuinely needs a longer chain, it is a **new chain id** and a new study with its own record.

## Why a log and not a table

A table can be quietly edited. A log cannot: every status change, every bound change and every choice
stays visible with its date and its phase, so an upgrade after the sealed window opens is recorded
rather than hidden. A downgrade is as reportable as an upgrade.
