# How a crosswalk row is verified, with one worked example

The attribution ceiling is not a data problem. It is a checked mapping problem: 274,176 MW of measured slippage
sits with 1,070 entities, the candidate matcher proposes a ticker for 51 of them, and the panel accepts a ticker
only when a row in `docs/entity-crosswalk.csv` carries evidence.

## The procedure, five steps

1. **Take the entity name exactly as the panel holds it.** The join is by name, so a tidy name is a broken join.
2. **Find the registrant.** The SEC's own company search by name returns the CIK and the filer title. If the entity
   files its own reports, that is the filer. The ticker map gives the holding company.
3. **Establish the link with a citable mechanism**, in order of strength: the entity files jointly in the parent's
   report and the accession prefix is the parent's filer id; the parent's report lists the entity as a subsidiary;
   the entity's own cover page names the parent. A name similarity is not evidence, which is why the matcher is not
   allowed to write rows.
4. **State the economic channel**, meaning how the slippage reaches the instrument: rate base, capex, revenue
   recognition, lease, or debt service.
5. **Record the receipt**: the accession, the document, the filing date, and the URL.

## The worked example

`Georgia Power Co` was the second largest slipped entity in the panel at 9,245 MW. Its own CIK is 41091 and it has
29 annual reports. Its latest annual report is filed under accession `0000092122-26-000006`, **whose prefix is The
Southern Company's own filer id**, and the primary document is `so-20251231.htm`, Southern's consolidated report.
So the slippage is inside Southern's regulated construction plan, and the row now records that with the receipt.

## What it demonstrates

The join is checkable, the receipts are public, and the work is bounded: roughly fifty entities carry most of the
slipped megawatts. The hard part is not evidence, it is labour, and it is the same artefact the contract forced
chain needs.

## What a verified row does not mean

It does not mean the parent's price responds to the slippage. That was measured and it did not, across 382 firms.
It means the instrument is now correctly identified as the place where the slippage lands, which is gate four, and
gate four has been the one failing most often.
