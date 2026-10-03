# Terrain map: everything built, measured, ruled out and blocked

The ledger holds what we know about the market. This holds everything else: the instruments we built, the
measurements we took, the things we ruled out with evidence, and the data we can and cannot reach. Together they
are the asset, whichever way the strategy goes.

## 1. Instruments we built, and what each one is for

| Instrument | What it does | Where it lives |
|---|---|---|
| Filings register | every filing of a firm with EDGAR's own acceptance timestamp, sealed window fenced | `src/edgar/`, `results/filings-register.csv` |
| XBRL fact join | joins a reported number to the moment its filing became public, without reading prose | `src/edgar/xbrl.py`, `results/obligation-panel.csv` |
| Industry universe by frames | every filer reporting a field in a period, grouped by its own SIC code | `scripts/build_rpo_universe.py`, `results/rpo-universe.csv` |
| Vintage reader | reads EIA-860M spreadsheets with no spreadsheet library, cached per vintage | `src/eia/xlsx.py`, `src/eia/vintages.py` |
| Delivery panel | promises compared across vintages: revisions, cancellations, realisations | `scripts/build_delivery_panel.py` |
| Survival panel | time to first revision per generator, with censoring handled | `scripts/build_promise_survival.py` |
| COG reader | reads a window out of a 100 MB satellite GeoTIFF with no geotiff library | `src/imagery/cog.py` |
| Site sampler | labelled sites with promise, realisation and coordinates | `scripts/build_site_labels.py` |
| Tape collector | public order book, funding and open interest at a fixed cadence, gap tolerant | `src/live/`, `scripts/collect_tape.py` |
| Node space registry | declared nodes with representations, clocks, availability and written blockers | `docs/scan/nodes.jsonl` |
| Scan engine | declared pairs, generated nulls, rate control, family correction, specificity | `src/scan/` |
| Variant ledger | every comparison tried, counted in one place, controls separated | `scripts/build_variant_ledger.py` |
| Hazard model | discrete time survival fit, bootstrap intervals, time split, exposures | `src/models/hazard.py` |
| Window and firewall | two declared study windows, holdouts closed by construction | `src/scan/windows.py` |
| Idea graph | ideas and directions with rationales, falsifiers and data needs, validated | `docs/ideas/graph.jsonl` |

## 2. Measurements that became truths

Beyond the thirteen in `truths.md`: the disclosure lag by field, the attribution ceiling, the compute family
structure, the modality mix of the buildout (solar 1,682 slipped promises, then wind, hydro, batteries, gas), the
cancellation count of 711, the 89 percent one signed aggregate signal, and the finding that a promise's hazard
rises with age.

## 3. Things ruled out, with the evidence

| Ruled out | Evidence |
|---|---|
| The disclosing firm's own equity responds to its obligation revisions | 382 firms, 4,634 events, no association; placebo produced more nominal hits than real data |
| A project's slip can be attributed to a listed owner | 274,176 MW of slipped capacity, 6.2 percent with a large listed owner, 80 percent in project companies |
| An aggregate capacity signal can be traded | three definitions, gross 0.29 percent a month, net minus 0.15 at doubled costs, drawdown 38 percent; and the signal was one signed in 89 percent of months |
| Market wide factors explain delivery | three factor sets, out of sample discrimination worse than controls each time |
| Pairwise series correlation reveals an edge | 135 comparisons, 6 survivors against 5.5 expected; the control over produced |
| Drought and weather matter for delivery | no payer, and the coefficient points the wrong way |
| Compute prices co-move as one market | median pairwise correlation of daily changes minus 0.01 across ten families |
| National lab, system operator and DOE queue data are reachable from here | 403, scripted tables, no usable catalog file |
| Two open GPU price datasets are usable | one is a collector with under a kilobyte of data, the other has no data |
| NAIP one metre imagery is usable without an account | requester pays bucket, s3 URL only |
| The QuantGraph holds our node space or any equity space | audited: no datacenter, compute, GPU, interconnection, backlog, guidance or equity nodes |

## 4. Data we can reach, and data we cannot

**Reachable**: SEC filings and XBRL with timestamps, EIA-860M monthly vintages, EIA-930 hourly grid files,
compute spot archive by family and day, NOAA statewide monthly weather, US Drought Monitor by state, public
Sentinel-2 imagery through STAC, the public perpetual venue, and the team's shared landings (Massive bars and
8-Ks, FRED, M3 orders and shipments and unfilled orders, Census construction spending, Philadelphia Fed delivery
times, New York Fed supply chain pressure).

**Blocked, with the reason recorded**: interconnection queues, spot power, executed compute rental history,
historical option chains, historical order book archive, NAIP metre imagery.

## 5. Findings that are about our own coverage rather than the world

The 6.2 percent attribution ceiling, the four fifths of slipped capacity inside project companies, the 36 percent
nudge share that forced the tail definition, the four month gap in the compute archive, the four firm limit on
the loaded 8-K set, and the frozen windows that make the compute era a twenty two month development sample.

## 6. What the map says about where an edge could live

Grouping by obstruction rather than by topic:

- **Blocked by instrument**: relative value across compute inventories, and any options-based distribution work.
- **Blocked by attribution**: the tail of delivery revisions expressed in equities, which needs names and a
  document path the market has not arbitraged.
- **Blocked by data**: anything ordered by the interconnection queue.
- **Not blocked at all**: forced flow on continuous venues, where the tape is running, the instrument exists and
  speed is the licence.
- **Cheap and untested**: the imagery probe at thirty to fifty labelled sites, and the same panel with the object
  redefined as cancellation or as revisions of six months or more.

That last row is the one that costs nothing to try and has never been tried.
