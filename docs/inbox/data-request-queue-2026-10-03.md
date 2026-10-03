# Data request: interconnection queue history

**Owner asked:** vshnu1 (holds the cloud pipeline and the Snowflake landings). **Requested by:**
sebastbernal2-ship-it. **Why it matters:** queue position is the real gate on whether a site can get power. It
is the one factor that names its payer directly, because whoever cannot get an interconnection position cannot
energize a project at any price, and the alternative is to wait.

## What we need, in order of value

1. **Queue snapshots over time**, not just the current queue. A single current snapshot cannot show a wait
   growing, and the wait is the signal. Monthly or quarterly vintage files, 2015 onward.
2. **Per request**, one row: a stable project identifier, the point of interconnection or county, state, fuel
   type, capacity in MW, the date the interconnection request was submitted, the queue position or cycle,
   the current status, the latest expected in-service date, and the date of withdrawal or energization if
   either has happened.
3. **The same fields in every vintage**, so a request can be followed across files rather than matched by hand.

## Sources, in the order I would try them

| Source | What it holds | Access notes |
|---|---|---|
| LBNL "Queued Up" annual workbook | the national queue assembled from operators, with wait times | emp.lbl.gov refused this host with 403; a browser or a different egress may work |
| MISO interconnection queue | queue table | page is scripted; the export behind it, or their API, is what is needed |
| PJM queue and planning data | queue and status | their data catalog did not answer from this host |
| ERCOT interconnection queue | queue for Texas, which is a large part of our panel | timed out from this host |
| CAISO, SISO, ISO-NE, NYISO queue pages | the rest of the footprints | CAISO URL I tried is stale; the current library path differs |
| FERC eLibrary filings | queue-related dockets and amendments | unstructured, but a fallback that needs no operator cooperation |
| DOE Open Energy Data Initiative | national lab datasets | catalog reachable, no usable queue file found from here yet |

## Fields that decide whether this is usable

- **Point in time**: each row needs the date the operator published it, so a vintage can be used without
  leaking later information.
- **Stability of identity**: if the request id changes between vintages, we need whatever field is stable.
- **Withdrawal and energization dates**: a queue that only grows cannot distinguish a slow queue from a
  hostile one.
- **Status vocabulary**: the operator's own status strings, unchanged, so we can map them ourselves and
  record the mapping.

## What we will do with it

Join it to the project panel we already hold: 6,407 generators with their promised and realized dates, by
state and technology. Then ask the question that has a payer: **does a fuller or slower queue push promised
dates out, and does a shorter wait pull them in.** That is a physical question, with no price in it, and it is
the first link we have not been able to test.

## What is explicitly not being asked for

No credentials in a file that Git tracks, no raw scrape committed, and no assumption that the data is
redistributable. A landing table in Snowflake or TigerData with a count and bounds, plus a documented source
and vintage field, is enough for our purposes, exactly as the AWS compute archive was handled.

## Acceptance check on our side

For each source: row count, earliest and latest publication date, distinct states, distinct fuels, the share
of rows with a usable submission date, and the share with a usable in-service estimate. If a source cannot
supply publication dates, say so and we will decide whether it can be used at all.
