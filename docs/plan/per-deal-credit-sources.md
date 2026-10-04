# Per deal credit data: the FINRA route, what it costs, and the free route beside it

Owner: sebastbernal2-ship-it. Written 2026-10-03 after running every route rather than reading about it. This
file owns the procedure for getting deal level credit data, and the correction it contains replaces the phrase
"a free FINRA API registration" that appeared in earlier drafts of the credit work.

## 1. The correction: FINRA is not a signup, it is an entitlement

The 401 from `api.finra.org/data/group/fixedIncomeMarket/name/corporateBondTrade` is an entitlement gate, not a
missing account. Verified from FINRA's own developer documentation and support page.

| Credential | Cost | What it reaches |
|---|---|---|
| Mock | free | mock data only, for building a client |
| Public | **free** | publicly available data, equity and fixed income, capped at 10 GB per month |
| Firm | 1,650 dollars per month | FINRA member firms, public data plus firm specific data |
| Organization | 1,650 dollars per month | organizations not regulated by FINRA: insurers, funds, transfer agents, clearing firms, service providers |
| SRO, Fingerprint | free | not relevant here |

Onboarding for anything beyond Public runs through the firm SAA under a signed FINRA Entitlement Agreement. The
SAA submits an API Console Entitlement Request, FINRA processes it in three business days, and only then are
credentials provisioned. Organizations outside FINRA regulation use the Organization credential, and their first
step is confirming an FEA, an Organization ID and a designated account administrator. Five credentials per firm,
10 GB per month each, invoiced through E-Bill. Test mode with a mock credential is open, so the client can be
built today at zero cost.

## 2. What the fixed income catalogue actually holds

Twenty five datasets, read from the developer documentation. The relevant ones: Corporate 144A Debt Market
Breadth and Sentiment, Corporate Debt Market Breadth and Sentiment, Corporate And Agency Capped Volume, Daily and
Weekly CMBS Pricing by Deal Vintage, Non Agency CMO Pricing by Deal Vintage, Non Agency CMO and ABS Pricing by
Product, Securitized Product Capped Volume, Securitized Products Trading Activity, TRACE Treasury aggregates, and
TRACE Quality of Markets report cards.

Every entry is an aggregate. Breadth, sentiment, capped volume, pricing by vintage cohort, pricing by product,
report cards. There is no per CUSIP trade record in the catalogue. A per trade TRACE history is a separate
licensed product and it is not what the free credential serves.

So FINRA cannot watch one site's bond daily at any credential level in that catalogue. It is the right route
for market level readings of the 144A and securitized markets and the wrong route for one deal.

## 3. The route that reaches deal granularity today, free, with no application

All verified by SEC full text search on 2026-10-03.

| Route | Verified example | What it gives |
|---|---|---|
| Form ABS-15G, securitizer asset level disclosure | Flexential Corp CIK 1889928, Cologix US Inc CIK 1896619, Phoenix Data Center Acquisitions LLC CIK 2025997, DataBank Holdings Ltd CIK 1822808 | deal structure and asset level data, point in time, free |
| Form 10-D, monthly trustee report | a registered CMBS trust carrying data center collateral, BBCMS Mortgage Trust 2019-C5, filing 0001056404-20-005041 | monthly pool cash flows, delinquencies, current factors |
| A holder filing carrying the private position | Blue Owl Real Estate Net Lease Trust CIK 1944366, 10-Q filed 2025-11-07, names Beignet Investor LLC, the Meta Hyperion issuer | par, coupon, maturity and fair value per position, quarterly |

Reg AB and Rule 15Ga-1 make a securitizer file even when the deal is not registered. Pure 144A project bonds with
no securitization wrapper do not file, and there the holder's own reporting is the only free view.

## 4. The order to do it in

1. EDGAR first, today, free. Wire the ABS-15G, 10-D and holder filings for a named deal set. Already inside our
   pipeline, no entitlement, and it produces the covenant and cash flow layer that makes any later price series
   interpretable.
2. The free Public credential second. It costs nothing, carries the 144A breadth and sentiment and the
   securitized pricing series, and it proves the client against real data.
3. The mock credential in parallel. Build and test the client against mock data so the day an entitlement exists
   the pull is one command.
4. The Organization credential only if a question survives steps 1 to 3, because it needs a signed FEA, an
   Organization ID, an SAA and 1,650 dollars a month.

## 5. What would change this plan

- A team entity that already holds a FINRA Entitlement Agreement.
- A paid vendor with per CUSIP corporate bond history at a price a small book can justify.
- A deal set whose tranches trade often enough for a print to matter, testable from the ABS-15G and holder
  filings before any tape is bought.

## 6. What the EDGAR layer actually contains, verified by opening the filings

Built 2026-10-03 by `scripts/build_credit_deal_registry.py`. Artifacts: `results/credit-deal-registry.csv`,
`results/credit-deal-registry.json`. The sweep covers the securitizer and trustee forms, ABS-15G, 10-D, 424B2,
424B3, 424B5 and S-3, over eighteen declared data center names plus one phrase sweep.

**Result: 133 deal level filings from 29 data center securitization programs, with no entitlement and no key.**
The programs, by filing count: BBCMS Mortgage Trust 2019-C5 (16, a CMBS trust carrying data center collateral),
Vantage Data Centers Holdings (16) plus four Vantage related entities, DataBank (12), Flexential (10), STACK
Infrastructure (16 across parent and issuer), Switch (10), Sabey (11 across holdings and issuer), Phoenix Data
Center Acquisitions (8), Compass Datacenters (4), CyrusOne (7), Cologix (5), Aligned (1), EdgeConneX (1),
Urbacon (1), Vault DI Issuer (1), MECP1 Mesa Intermediate (1).

**What each form carries, verified by reading one.** The forms are not interchangeable and two of them are
weaker than the name suggests.

| Form | Verified content | What it is not |
|---|---|---|
| ABS-15G | the securitizer's attestation plus the Rule 15Ga-2 third party due diligence report on the tenant lease portfolio, naming the deal, the series and the class, for example "Sabey Data Center Issuer LLC, Secured Data Center Revenue Term Notes, Series 2020-1, Class A-2" and "Vantage Data Centers Issuer LLC, Secured Data Center Revenue Term Notes, Series 2018-1, Class A-2" | it does not carry the lease schedule, the cash flows or a price. The exhibit describes the procedures applied to the lease portfolio, not the rents |
| 10-D | the monthly trustee distribution report for a registered trust, with pool cash flows, delinquencies and current factors. The one reached here is a CMBS conduit, BBCMS 2019-C5, with sixteen filings from 2019 to 2026 | a data center deal on its own. It is a diversified conduit that happens to hold data center collateral |
| 424B | for a registered deal, the tranche sizes, coupons, ratings and waterfall | reached only through fund holdings in this sweep, so the data center deals' own 424B filings are the next thing to hunt by CIK rather than by phrase |

**Two boundary findings, both worth keeping.** First: the deal names confirm the structure the mechanism
assumes. These are "Secured Data Center Revenue Term Notes", which is a securitized rent stream, not a corporate
obligation, so the constrained party is the issuer ring fenced per deal, exactly as the six gates want. Second:
the sweep's own rules mattered. A query for "Iron Mountain" returned Sunrun and Vivint Solar ABS filings,
because the documents mention the tenant. A name query is a discovery route, not a classification, and the
registry now separates confirmed off topic filers from unresolved ones. Two filers are unresolved and need a
document read before anything is claimed about them: ADC Holdco LLC and DI PROPCO LLC.

**What the layer does and does not give.** It gives, free: deal identity and structure, the class and series
naming, the due diligence trail, monthly cash flows for the registered trusts, and holder fair value marks from
fund filings. It does not give, at any price on EDGAR: a daily price for one tranche or one 144A project bond.

## 7. The 424B package is dead, and the reconnaissance that killed it

The last plan was to parse each deal's own 424B prospectus for the tranche table. That plan was checked before
building it, by listing the forms on file for all 28 data center securitizer CIKs through the submissions API.
The result: **not one 424B, not one S-3, not one prospectus anywhere in the set.** Every data center
securitizer in the register files **ABS-15G only**, some with a 15Ga-1 repurchase report beside it.

| Filer type in the register | Forms on file |
|---|---|
| Every data center securitizer, 25 of 28 | ABS-15G, and ABS-15G/A |
| CyrusOne LP | ABS-15G plus corporate debt forms, 424B2, 424B5, S-3ASR, S-4, which are its corporate notes and its merger, not the securitization |
| Citigroup Commercial Mortgage, BBCMS | ABS-15G, 424B2, 10-D, FWP: CMBS conduits, registered, with data center collateral inside a mixed pool |

These are 144A securitizations. There is no registered offering, so there is no prospectus, so **the tranche
table is not on EDGAR at any price.** The plan to parse it was wrong and it is dropped rather than built.

## 8. The deal register that is buildable, and it is built

    make deal-structure     # python3 scripts/build_deal_structure.py

Artifacts: `results/deal-structure.csv`, `results/deal-structure.json`. It walks every securitizer CIK in the
register, fetches each ABS-15G cover page and its exhibit, and writes one row per filing.

**Coverage: 324 ABS-15G filings parsed from 28 securitizers, naming 191 distinct issuing entities, 25 of which
carry their own CIK.**

**Correction, 2026-10-03, later the same day: the first published count in this section was wrong and low by
half.** It said 68 data center filings and 42 deals. It is **125 filings and 81 deals**, and the error is worth
recording because of how it was found. The content flag that decides whether a filing is a data center deal was
tested against the cover page only, and DataBank and Flexential describe their data center collateral in the
exhibit rather than on the cover, so 22 filings across two programmes were silently excluded. The agency
enumeration in section 11, built to find deals the register *lacked*, immediately showed DataBank and Flexential
missing, which is how a false negative inside the register was caught by a sweep looking outward. The flag now
tests the cover and the exhibit. Two errors of the same family, one false positive and one false negative: the
Sunrun filing that a name query admitted, and these two programmes that a cover page rule excluded.

**The data center subset, which is the set that matters: 125 filings carrying data center terms, of which
121 are pure play and 4 sit inside mixed pool conduit trusts. They name 81 deals, 77 pure play and 4 conduit,
each with an issuing entity, a series and the filing dates.** The difference between the two kinds is not
cosmetic: a pure play issuer's collateral is data center rent only, so the site's constraint is the whole
instrument, while a conduit holds a data center loan inside a diversified pool and dilutes it before the note.
The issuer families, from the filings themselves:

| Issuer | Series named |
|---|---|
| Vantage Data Centers Issuer, LLC | 2018-1, 2018-2, 2019-1, 2020-1, 2021-1, 2023-1, 2024-1, 2025-1, 2025-2 |
| Vantage Data Centers Canada, LP | 2019-1, 2020-1, 2021-1, 2023-1, 2024-1, 2025-1, 2025-2 |
| Vantage Data Centers Canada QC4, LP | 2023-1, 2024-1, 2025-1 |
| Retained Vantage Data Centers Issuer, LLC | 2023-1, 2024-1, 2025-1 |
| Compass Datacenters Issuer II, LLC | 2024-1, 2024-2, 2025-1, 2025-2 |
| Compass Datacenters Issuer III, LLC | 2025-1, 2025-3, 2026-1 |
| Centersquare Issuer LLC and its co-issuer | 2024-1, 2025-1, 2025-3, 2025-5 |
| Cologix Data Centers US Issuer and co-issuer | 2021-1, 2026-1 |
| EdgeConneX Data Centers Issuer, LLC | 2022-1, 2024-1 |
| DataBank | 2020-1, 2021-2, 2023-1, 2024-1, 2025-1, 2026-1 |
| Flexential | 2021-1, 2022-1, 2023-1, 2025-1, 2026-1 |
| Scalelogix, EDI | one series each |
| Sabey, Aligned, Phoenix Data Center Acquisitions, CyrusOne | filed ABS-15G, with the series or the entity recovered on some filings and not others |

The pure play programmes by deal count: Vantage 19, DataBank 12, Switch 10, Flexential 10, Centersquare 8,
Compass 7, Cologix 4, Retained Vantage 3, EdgeConneX 2, Scalelogix 1, EDI 1. Four further deals are conduit
trusts: Benchmark and BBCMS pools carrying data center collateral inside a mixed portfolio.

Rows that recovered a series but no issuing entity name are left empty and counted rather than filled in.

**The register is stable across runs, which took a fix.** A first run lost one EdgeConneX filing to an SSL
handshake timeout and the reported deal count moved. Filing fetches now retry four times. Two consecutive runs
after the fix agree exactly: 324 filings, 68 data center filings, 42 deals, zero errors.

**A content check was needed, and it is the fix that made the register trustworthy.** A conduit securitizer files
every deal it ever issues under one CIK, so listing Citigroup Commercial Mortgage Securities by name pulled in
unrelated CMBS deals such as the Benchmark trusts and 225 Liberty Street. A filing now counts as a data center
deal only when its own text says so, which dropped the conduit noise and left 68 filings. Nine rows recovered a
series but not an issuing entity name and are left visible rather than filled in.

Fields and their measured parse rate, over the 114 filings that are confirmed Rule 15Ga-2 due diligence
reports, which are the ones that name a deal:

| Field | Parse rate | Note |
|---|---|---|
| deal series | **103 of 114, 90 percent** | Series 2025-1 leads with 20 filings, then 2024-1 with 15, 2021-1 with 13, 2026-1 with 11 |
| accountant report date | 103 of 114 | the independent accountant's agreed upon procedures report date |
| issuing entity CIK | 93 of 114 | the registration a future filing would come from, distinct from the securitizer's |
| accountant | 94 of 114 | for example Deloitte and Touche for the Switch master trust |
| issuing entity name, depositor CIK | 82 of 114 | |
| class | **21 of 114, 18 percent** | genuinely rare on the cover exhibit. The class table is in the ratings publication, not here |

Three fixes were needed and all three are recorded rather than hidden, because each one was a silent error
first: the rule field detected a mention instead of the ticked box and labelled all 324 filings as answering
both rules, the accountant pattern failed on an ampersand in a firm's name, and the series pattern required
digits after the dash, which skipped every conduit deal named 2019-C5. Fields that stayed unreliable were cut
rather than shipped: the signature block, whose layout varies by filer and which adds nothing the securitizer
CIK does not already say.

## 9. Where the tranche table actually lives

Verified on the Switch ABS Issuer LLC Series 2025-2 press release from Morningstar DBRS, which is fetchable and
free:

    Class A-2-I at (P) AAA (sf)     Class A-2-II at (P) AA (low)     Class A-2-III at (P) A (low)
    Class B at (P) BBB (low)        all trends Stable

with the collateral described as fee simple and leasehold interests in **10 data center properties, 11
buildings, four states, Georgia, Michigan, Nevada, Texas**, structured as a Master Trust where Series 2025-2 is
the fourth issuance and the A-2 notes apply interest and principal pro rata while the 2025 A-2 notes apply
theirs sequentially. What the press release does **not** carry: coupon, spread, WAL, or LTV. Those sit in the
rating report behind the agency's subscription, or in the private placement memorandum, which is not public.

So the free per deal record is: identity and parties from EDGAR, the rated class ladder and the collateral
description from the agency press releases, and monthly cash flows only for the registered CMBS trusts. A
coupon and a size per class are not free, and the price of one tranche is not free at all.

## 10. The agency layer: the class ladder, the coupon, and the operating profile

    make deal-ratings     # python3 scripts/build_deal_ratings.py

Artifacts: `results/deal-ratings.csv`, `results/deal-ratings.json`, `results/deal-operation-metrics.csv`.
Seventeen declared seed pages, fifteen fetched, two refused.

**The class ladder is extractable and it is ground truthed.** For Switch ABS Issuer Series 2025-2 the
extractor returns Class A-2-I AAA, Class A-2-II AA (low), Class A-2-III A (low), Class B BBB (low), all
provisional, which is exactly what the release states. Sixteen rated class rows across seven deals, with
**five rows carrying a stated coupon** and **seven carrying an original amount**, for example the Vantage
Jersey SPV at GBP 600.0 million Class A-2 paying an indicative fixed coupon of 6.172 percent to an anticipated
repayment date in May 2029.

**The operating profile comes free with a plain fetch, and this is the valuable part.** KBRA releases state the
portfolio's revenue and net operating income per deal, which is what gate 3 needs in order to size a transfer:

| Deal | Data centers | Sellable sf | Critical load MW | Annualised revenue | AANOI |
|---|---|---|---|---|---|
| DataBank Issuer Series 2026-1 | 36 | 1,621,139 | 257.6 | not stated | 217.6 million |
| Flexential Issuer Series 2026-1/2 | 28 | not stated | 199.0 | 663.3 million | 353.2 million |
| Centersquare series | 40 | 1,914,134 | 296.6 | not stated | 415.4 million |
| TierPoint Issuer Series 2025-3/4 | 33 | 647,314 | 96.0 | not stated | 240.3 million |

**Two agencies are blocked, and the reasons are different.** S&P returns 403 to a non browser client. KBRA
serves its operating metrics as static text but renders the rated class table on the client, so its pages come
back with no rating token at all: 67 kilobytes of HTML containing the string AAA zero times. The fix for KBRA
is a JS capable fetch, and this repo already renders the note through a headless chromium, so the capability
exists rather than needs buying.

**The universe finding matters more than the parser work, and it cut both ways.** Section 11 enumerates
KBRA's own data center category and diffs it against the register. It found deals the register lacked, including
TierPoint, QTS and Lohrasp, whose collateral includes data centers but whose names carry no data center token.
It also, and more usefully, found a **false negative inside the register**: DataBank and Flexential were being
dropped by a flag that read only filing covers. Fixing that took the register from 42 deals to 81. A sweep
looking outward is what exposed an error looking inward.

**Three parser versions were needed and two were wrong**, both caught by checking against a published ladder
rather than by looking at the output. The first lost the coupon by reading only 200 characters after a class
mention. The second shared one rating across every class on the page, turning the Switch ladder into AAA four
times. The version that works pairs a rating to the class printed before it, then merges repeated mentions of
the same class so a coupon stated elsewhere still attaches.

## 11. The six gates, applied to the deals

    make gate-scorecard     # python3 scripts/build_gate_scorecard.py

Artifacts: `results/gate-scorecard.csv`, `results/gate-scorecard.json`. The gate rules are fixed in the script
header before any of them is applied, and a gate that no measured field can decide is written BLANK rather than
argued.

**Count correction first.** The register holds 81 issuing entities across **60 deals**, because an issuer and
its co-issuer file two ABS-15G cover pages for one series. The graph keeps the 81 legal entities, because that
is what a filing names. The gates are scored on the 60 deals, because that is what a note is collateralised by.
Of the 60: **56 pure play and 4 mixed pool conduit**.

| Gate | Result | Reading |
|---|---|---|
| 1. Constrained counterparty | **60 PASS** | every deal is a ring fenced issuer named in a filing. The covenant type is blank: no free source states the debt service thresholds |
| 2. Price insensitive flow | **2 PASS, 58 PARTIAL** | every deal here is a rent securitisation, so the flow is contractual by construction. Only two deals carry a document level record in this pass, so the rest are recorded as structural rather than measured |
| 3. Transfer and concentration | **0 PASS, 2 PARTIAL, 58 BLANK** | the gate that decides a trade is the gate with no evidence. Two deals have a magnitude from an agency release and neither has a concentration number |
| 4. Instrument without dilution | **56 PARTIAL, 4 FAIL** | pure play deals have no dilution by construction, with reachability unverified. The four conduits fail: a data center loan inside a diversified pool is diluted before the note |
| 5. Economics and capacity | **2 PARTIAL, 58 BLANK** | coupons and amounts exist for a handful of deals, matched on programme and series |
| 6. Barrier | stated for the layer | attention and processing: reading lease and indenture documents, and holding local power market knowledge. Never scored as a pass per deal |

**What the scorecard actually says.** The structural half of the method is satisfied across the whole layer:
60 ring fenced counterparties, each with a contractual rent stream, 56 of them undiluted, every one named in a
public filing with a date. The empirical half is empty. **The concentration number, which is the only thing that
turns a counterparty into a trade, exists for zero deals in the register.**

**And the one deal with a published concentration number is not in the register at all.** The Vantage Data
Centers Jersey Borrower SPV reports a largest tenant at 73.2 percent and a top tenant group at 98.5 percent of
revenue, which is exactly the concentration statement gate 3 asks for, and it is a European SPV with no ABS-15G
in the EDGAR set. That is where the next hour belongs: the deals whose agencies state concentration.

**Attribution rule, and the error that forced it.** Agency evidence decides a gate only where the programme and
the series both match. The first version matched on the programme, which put the Vantage Jersey concentration of
73.2 percent on three unrelated Retained Vantage deals and the same coupon on all of them. Programme level
numbers are now reported as programme scope evidence and leave the gate blank. The rule is in the JSON as
`attribution_rule`, so the next reader can see it was a decision rather than an accident.

## 12. The agency named deals outside the register, and their blockers

    make agency-deals     # python3 scripts/build_agency_only_deals.py --workers 10

Artifacts: `results/agency-only-deals.csv`, `results/agency-only-deals.json`. Every located agency page is
fetched concurrently and split into deals the register holds and deals it does not.

**164 agency pages, 89 deals already in the register, 75 outside it.** Of the outside deals, **8 carry operating
terms from an agency release and no SEC filing at all**:

| Issuer | Series | Data centers | MW | AANOI |
|---|---|---|---|---|
| TierPoint Issuer LLC | 2026-1 | 34 | 104.8 | 241.4 million |
| TierPoint Issuer LLC, TierPoint LLC | 2025-1, 2025-3 | 33 | 95.7, 96.0 | 237.4, 240.3 million |
| TierPoint | 2024-1 | 31 | 64.6 | 206.3 million |
| Lohrasp Enterprise II LLC | 2026-1 | not stated | 80.0 | not stated |

**The concentration figure turns out to be rarer than the operating metrics, and that is the finding.** Across
all 164 pages, **zero** state a largest tenant percentage. The single deal in the whole effort that states one,
the Vantage Jersey SPV at 73.2 percent, is a DBRS page and a European SPV, so it sits outside the KBRA derived
set entirely. Concentration, which is the number gate 3 needs, is stated by almost nobody in public.

**The blockers are now written into the graph rather than remembered.** The 47 agency-only deals entered the
manifest as blocked nodes, each carrying its own blocker sentence, with two edges each and a dataset node that
holds them. Manifest clean at **554 nodes and 1,318 edges**: 81 filing backed deals and 47 agency only.

## 13. The tranche table, from the holders rather than the issuers

    make tranche-table     # python3 scripts/build_tranche_table.py --workers 6

Artifacts: `results/tranche-table.csv`, `results/tranche-table.json`. **This closes the gap the whole effort
kept hitting.** A 144A securitization files no prospectus, so the class terms were declared unreachable. But the
registered trusts that hold these deals must file the instruments defining their security holders rights as
Exhibit 4, and a series supplement states the class, the initial balance, the note rate, the rating, the
anticipated repayment date and the post-ARD spread.

Seventeen class rows across ten series, seven with the full term set. The cleanest reading is one programme's
secured notes over five years, a term structure for the same collateral family:

| Series | Class | Initial balance | Note rate | Rating | Anticipated repayment | Post-ARD spread |
|---|---|---|---|---|---|---|
| 2021-1 | A-2 | 400,000,000 | 1.877% | A-(sf) | March 2026 | 0.95% |
| 2023-1 | A-2 | 250,000,000 | 5.900% | A-(sf) | March 2028 | 2.100% |
| 2023-2 | A-2 | 250,000,000 | 5.900% | A-(sf) | July 2028 | 2.414% |
| 2023-3 | A-2 | 290,000,000 | 5.900% | A-(sf) | October 2028 | 2.45% |
| 2024-1 | A-2 | 240,000,000 | 5.900% | A-(sf) | March 2029 | 1.80% |
| 2025-1 | A-2 | 345,000,000 | 5.00% | A-(sf) | May 2030 | 1.45% |
| 2026-1 | A-2 | 695,000,000 | 5.00% | A-(sf) | March 2031 | 1.85% |

Ground truthed against the Series 2025-1 supplement: 345 million at 5.00 percent, rated A-(sf), repayment May
2030, final May 2050, post-ARD spread 1.45 percent.

**What this does for the gates.** Gate 5 now has a number per class. The cost of secured data center debt for
this programme ran from 1.877 percent in 2021 to 5.9 percent in 2023 and back to 5.0 percent in 2025 and 2026,
with the post-ARD penalty spread moving from 0.95 to 2.45 and back to 1.85. That is the transfer, stated by the
instruments themselves. Gate 3 still lacks concentration and gate 4 still lacks reachability.

**Two boundaries that keep this honest.** A rate printed at issue is not a current yield, so nothing here is a
price series and no signal can be built from it yet. Seventeen class rows came from seventeen documents and the
full term set is present for seven, so the parse rate is stated rather than assumed.

A second artifact, `results/indenture-layer.csv`, searches the same documents for the covenant families: a debt
service coverage clause appears in 3 documents, a cash trap in 1, a reserve account clause in 11, and
cross-default and concentration clauses in none. That is a coverage statement and not a finding about the deals:
a series supplement is a short instrument that defines the series, and the base indenture that holds the
covenants is a separate, longer document.

