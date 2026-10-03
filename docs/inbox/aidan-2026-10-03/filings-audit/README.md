# Filings feasibility audit

Research date: 2026-10-03. Owner: aidanq06. Status: manual source pilot, not a promoted thesis or a backtest dataset.

## Finding

Historical disclosures contain measurable delivery expectations. The difficult part is joining the same obligation across disclosures, identifying the first public revision, and attributing the resulting cash-flow exposure. A backlog increase or longer signing-to-start interval is not enough to label a delay.

The [observation register](observations.json) locates 15 annual filings across PWR, ETN and DLR for fiscal 2020–2024 and records 15 company-period observations. These are 15 portfolio snapshots, **not 15 independent delivery surprises**. Targeted sections were reviewed, with issuer mirrors used where SEC retrieval failed. DLR annual bodies could not be retrieved through the available tools; its observations come from quarterly earnings releases instead. This is not an exhaustive review of all 8-Ks and 10-Qs in the period.

No prices, stock returns, model fitting or performance tests were used. Every observation's first-public timestamp remains unresolved, so none is eligible for an intraday backtest yet. Fiscal 2024 reports published in 2025 must never be backdated to December 2024. Documents inspected during research design should be logged as development exposure; absence of price inspection does not by itself preserve a sealed test.

## What the five-year fields measure

| Company | Verified field | Use | Main limitation |
|---|---|---|---|
| Quanta / PWR | Annual consolidated backlog, remaining performance obligations, and expected next-12-month portions | Separate contracted obligations from estimated future business | Backlog includes estimates under master service agreements and short-term work; acquisitions and new awards alter the portfolio |
| Eaton / ETN | Approximate firm-order backlog and next-12-month percentage | Measure firm commitments and expected conversion horizon | Different annual order cohorts; recognition/delivery wording changes; acquisitions and mix need controls |
| Digital Realty / DLR | Q4 weighted-average interval from signing to contractual lease commencement | Measure the timing of newly contracted rental business | A contractual wait is not a missed deadline; new leases change every quarter |

Values, units, locators and source links belong in the observation register. Do not pool these three fields into a common delay score. PWR's consolidated history avoids a segment-definition trap, but does not eliminate acquisition effects. DLR's trust and operating partnership can appear under different CIKs in joint filings; deduplicate them.

## Actual promise-to-delivery cases

The [case ledger](cases.md) preserves three project clusters:

1. **Vogtle Unit 4:** a prior Q1 2024 expectation, an explicit revision to Q2 following a cooling-system issue, and April 2024 delivery. This is an out-of-basket methodology example, not an added equity-universe member or independent trades for every co-owner.
2. **Western Spirit Wind:** a year-end 2021 target, a later reaffirmation, and a retrospective 2021 commercial-operation record. This is a candidate successful-delivery control, with source-date and exact timing limitations. Blattner's later acquisition by PWR prevents treating the earlier private-company relationship as PWR exposure throughout.
3. **SunZia:** a concrete original expectation, but no verified like-for-like revision in this audit. Construction completion and commercial operation are different milestones. Keep this unresolved rather than manufacturing a delay label.

These cases were selected to inspect measurement, not sampled to estimate success rates. They provide no event-frequency estimate or evidence of alpha. The basket currently has **zero fully verified, first-public-timestamped, cash-flow-mapped surprise observations** ready for trading analysis.

## Older-history spot checks

- [Quanta's February 2011 results exhibit](https://www.sec.gov/Archives/edgar/data/1050915/000095012311016779/h79890exv99w1.htm) contains named-project schedules, including Central Maine Power and CapX2020. This establishes the presence of earlier promises, not a matched outcome panel.
- [Eaton's 2014 annual filing](https://www.sec.gov/Archives/edgar/data/1551182/000155118215000007/etn12312014form10-k.htm) reports firm-order backlog. The older accounting presentation needs a definition bridge before joining modern remaining-obligation fields.
- [Digital Realty's Q4 2014 release](https://investor.digitalrealty.com/static-files/c8a7b729-d3b5-421c-b666-4c829c90ea81) reports signing-to-commencement timing, supporting a longer-history collection route.

These are spot checks, not a completed ten- or twenty-year audit. They support further historical collection without establishing that older equities validate emerging compute futures.

## Collection contract

Enumerate all filings and relevant issuer releases for a predeclared universe and development window before searching for delays. Cover 8-K bodies and exhibits, 10-Q and 10-K MD&A/notes, and issuer supplements. For foreign issuers, map 6-K/20-F where applicable. Use project-level source receipts to connect obligations; generic risk-factor language is not a realized event.

Each record needs issuer and project identity, exact milestone, prior disclosure, prior target interval, new disclosure, new target interval, source availability times, quantity and units, contract/exposure evidence, confidence, and exclusion reason. Keep the actual delivery date in a separate outcome field. Preserve unknowns and explicit reaffirmations; silence is not evidence of an unchanged schedule. Quarter ranges must remain intervals rather than fabricated exact days.

For intraday use, reconcile EDGAR acceptance with issuer releases, calls, regulatory notices and earlier dissemination. Store the earliest defensible public availability and realistic processing lag; a filing date or a website's generic time-of-day is insufficient. Repeated announcements and co-owner filings share a project/shock identifier. Availability is field-specific: later labels never become earlier inputs.

The [SEC Form 8-K instructions](https://www.sec.gov/files/form8-k.pdf) do not make every project delay a standalone reportable event. Item 1.01/1.02 agreements, Item 2.02 earnings material, Item 7.01 disclosures and Item 8.01 other events are search routes, not guaranteed delay categories. Preserve whether material is filed or furnished and follow its exhibits. Use the [SEC APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) for enumeration subject to access rules. Direct raw retrieval was unsuccessful in this session; there is no immutable raw archive, checksum manifest or automatic extraction replay yet.

## Decision for the strategy

Proceed with a modest, development-only project ledger before buying a broad text history or training a model. Count independent matched shocks, missing baselines, timestamp failures, explicit reaffirmations and actual deliveries. Predeclare the mechanism, trade mapping, falsifier, baseline and costs before inspecting returns. The original three firms remain a convenience feasibility sample, not a survivorship-controlled investment universe.

The economic mapping must identify who bears the loss: contractors can recognize revenue during construction, equipment vendors may already have delivered, and facility owners may lose rent or incur financing costs. A physical delay cannot justify mechanically shorting every connected company. Test whether information is newly public and whether repricing remains after an executable lag.

This audit supports the feasibility of **measurement**, not an intraday edge, an HFT implementation, a sample-size claim or transfer to Ornn. The next missing deliverable is a complete enumerated filing corpus and matched event panel, with timestamps and exposure receipts. Track requirements remain owned by [the brief](../../../brief.md); this document does not approve a split or open OOS.
