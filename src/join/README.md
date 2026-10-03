# src/join

Join a measured project revision to a firm that has a price, and show what cannot be joined.

The naive version of this join is a name lookup, and it does not work. EIA names the entity that developed
or operates a plant, and most of those are project companies. In the nine-vintage panel, 274,176 MW of
slipped capacity sits across 1,070 entities, and **6.2 percent** of it belongs to an entity whose name
carries a large listed owner. **80 percent** belongs to project or holding companies, so most slipped
capacity has no equity to price.

## The rule this module enforces

**Attribution needs evidence.** `docs/entity-crosswalk.csv` is the only path to a ticker, and a row counts
only with `status: verified` and an evidence reference. `entities.py` proposes candidates with a score and
an audit trail, and nothing more. That is not caution for its own sake: on this data the matcher attributed
capacity to a preferred share series (Georgia Power rather than the parent common) and to a mortgage
insurer, so an unattended join would have produced a confidently wrong answer.

Three outcomes, all honest:

- **matched** means one registrant dominates and the first significant word agrees
- **ambiguous** means two registrants score within a hair, so no attribution is claimed
- **unmatched** means nothing clears the bar, which is the common case

## Owner

`sebastbernal2-ship-it` claims `src/join/` in `OWNERS.md`.

## Use

```sh
python scripts/build_exposure_panel.py
```

It writes `results/entity-matching.csv` (the proposals, with scores) and `results/exposure-panel.csv`
(slipped capacity by entity and vintage pair, stamped with when the revision became public).

## What it cannot tell you

An EIA entity is a developer or operator. **The contractor and the equipment vendor are not in this data at
all**, so PWR or ETN exposure to a slipped project cannot be derived here. That path runs through the
filings ledger and the obligation panel, which measure what a firm discloses about itself.
