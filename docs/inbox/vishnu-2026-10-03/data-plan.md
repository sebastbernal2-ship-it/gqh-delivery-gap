# Instrument-specific data plan

Status: candidate audit universe, not approved trades. Owner: Vishnu.
Provider coverage/access receipts live in [source-audit.md](source-audit.md).

## Clocks and depth

The current economic signal is disclosure/revision-driven, likely daily or slower. Price
precision, granular timestamps and reliable execution are important, but do not change that
signal into an HFT strategy. Decide the horizon and order-size policy before buying depth.

- Daily OHLCV and corporate actions: historical return, volatility and benchmark studies.
- L1 plus trades: bid/ask spread, top-of-book size, trade intensity, inferred aggressor direction
  and modest-order execution analysis. Quotes alone cannot measure selling acceleration.
- L2: multiple displayed price levels for larger-order depth and impact studies. A snapshot
  cannot establish queue priority, hidden liquidity or guaranteed fills.
- L3/MBO: order identifiers plus adds/changes/cancels/executions for queue-aware research.
  One venue is not the whole US market. Trader identity is generally not exposed.
- Crypto "L4": provider-specific wallet attribution, not a universal exchange data standard or
  part of the first equity test. It needs its own field/coverage verification.

## First candidates, not a preassigned pair

| Instrument | Economic role to investigate | Required signal data | First market data | Additional depth |
|---|---|---|---|---|
| PWR | Grid/infrastructure project execution | Electric-segment total and 12-month backlog, guidance, named contract schedules, revisions, acquisitions | Raw/adjusted daily OHLCV/actions; L1 + trades for event windows | L2 optional for bigger intraday orders; L3 not required |
| ETN | Electrical equipment supply and conversion of orders to sales | Electrical orders/backlog/book-to-bill, capacity announcements, sales/margin guidance, revisions | Same daily and event-window L1/trades | Same conditional L2 policy |
| EME | Installation/construction execution | Segment RPO/backlog, expected revenue timing where disclosed, margins, guidance and acquisitions | Same daily and event-window L1/trades | Same conditional L2 policy |
| DLR | Data-center capacity becoming rental revenue | Signed-but-not-commenced leases, contractual commencement lag, development capacity/costs, forecast changes | Same daily/actions including dividends and event-window L1/trades | Same conditional L2 policy |
| SPY | Market benchmark; possible beta hedge | No delivery-event extraction | Daily total-return series if benchmark only; L1/trades if actually traded | No initial L2 |

PWR is the initial correctness test because useful historical numeric disclosures have been
located. ETN, EME and DLR offer distinct mechanisms to audit. None has been shown to have a
hole-free comparable ten-year operational series. Confirm continuity before admitting it to
the final universe. SPY is not the presumed short leg.

Second-wave watchlist: HUBB/POWL for equipment constraints, VRT for power/cooling, GEV for
generation equipment, EQIX for data-center operating capacity, NVDA/AMD for compute hardware.
These are brainstorming candidates, not a verified data shortlist. Short listing histories,
spin-offs, acquisitions, differing fiscal calendars and changing AI exposure may limit them.
Do not join a predecessor's unrelated history to manufacture a long record.

## Futures and perpetuals: no required initial leg

| Candidate | Condition for inclusion | Required observations |
|---|---|---|
| Equity-index futures hedge | A justified replacement for the equity benchmark hedge, with viable access | Individual contracts; prices/volume; expiry and roll policy; multiplier, tick value, currency, margin/cost policy; L1 for execution |
| Energy futures | A named contract with a demonstrated transmission from the measured shock | Contract-specific prices/curve, volume/open interest, delivery/expiry conventions, rolls, L1; L2 only if order size/execution calls for it |
| Compute index/futures | Verified methodology, entitlement, history and actual trading activity | Index vintages/prices/methodology; real contracts/settlements, volume/OI, expiry/specifications and executable bid/ask |
| Hyperliquid/HIP-3 perps | Exact venue/market verified, with a separate short-history study | Prices/trades, funding, mark/index prices, specifications, listings, quotes/depth and fees; wallet/order events only if required and obtainable |

A futures listing is not evidence of liquidity. A settled price is not an executable quote.
A continuous futures series is not a sufficient ledger for fills/rolls/P&L. A short-history
perpetual cannot borrow validation from older equity or commodity data.

## Event data: observations to collect

Use original releases and 8-K exhibits plus 10-Q/10-K disclosures, not only event tags. Collect
earlier forecasts as well as revisions. A complete event record needs:

- Company CIK/security ID, segment, project/contract identity and source accession.
- Source publication/acceptance time, earliest verified availability and timezone semantics.
- Observation date, economic period and target date/horizon; these are different clocks.
- Metric name, numeric value/range, units, prior comparable expectation and target period.
- Changed forecast date, MW/revenue/backlog affected, scope changes and cancellation evidence.
- Original text/table provenance, acquisition/definition flags and extraction/review status.
- Exposure mapping known at that time, missingness reason and event-cluster identifier.

Preserve original releases and amendments independently. Do not treat a later comparison table
as the first availability of the old number. When the exact first public time is unknown, use
a documented conservative availability rule, not an assumed intraday timestamp. Keep date
ranges as ranges: "mid-year" does not mean an exact day.

## Sufficiency audit before scaling

Intersect market history, operational field coverage, availability evidence and usable firm
exposure. Count independent projects/shocks as well as firms and releases. Multiple amendments,
monthly updates and correlated firms are not independent event replications.

Report missing periods, definition breaks, amendments, excluded events, common-shock clusters
and regime coverage. Enough calendar years is not the same as enough independent examples.
Define the universe historically or disclose and assess survivorship/selection limitations.

## Extra controls, not a kitchen sink

EIA-860M generator schedules are a potential capacity-context stream, not direct data-center
construction schedules. Require defensible historical regional/company exposure. ALFRED
vintages can provide macro controls; Ken French factors can provide return benchmarks, with
an appropriate publication lag if used as trading inputs. Satellite/permit/hearing data require
an independent historical feasibility audit before inclusion.

## What market data does not fix

Historical borrow availability/fees, corporate identity/universe history, point-in-time consensus,
hidden liquidity and uncertain operational definitions remain real gaps. Record borrow cost
scenarios and shortability limitations; do not certify an executable long/short strategy without
addressing them. Liquidity/capacity is dynamic: measure volume/spreads and constrain sizing rather
than labeling a ticker permanently liquid or illiquid.
