# src/live

Collect the public tape for the pre-registered cascade protocol in `docs/plan/cascade-protocol.md`.

The object is a forced deleveraging: a leveraged position closed by the venue's engine when maintenance margin
is crossed, so the flow is price insensitive by rule. The question is the distribution of the path after the
threshold fires, and the reason speed matters at all is only that it lets a participant be present.

This module reads the venue's own public endpoint: order book snapshots with sizes, funding, open interest,
oracle and mark price. No key, no account, no order. It parses responses into flat rows and computes the
derived quantities the protocol names, so the trigger rule can be tested offline against recorded rows rather
than against a live connection.

## Owner

`sebastbernal2-ship-it` claims `src/live/` in `OWNERS.md`.

## Use

```sh
python scripts/collect_tape.py --minutes 30 --interval 15
```

Samples land in `data/tape/`, which git ignores, so the tape stays local while the protocol stays reviewable.
The trigger rule is applied afterwards, from the recorded rows, so a change of mind about the rule cannot be
mistaken for a property of the data.

## What this cannot conclude

A tape of hours describes that window and nothing more. No result from it may be called a strategy, and every
conclusion must name its sample length.
