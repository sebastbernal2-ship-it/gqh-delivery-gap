#!/usr/bin/env python3
"""Build a development-only index reconstitution coverage inventory.

The public history page is a discovery source. Without primary announcement
clocks and pre-effective quantity inputs, rows remain excluded from returns.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
from html.parser import HTMLParser
from pathlib import Path
import sys
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from strategy.index_mandate import event_eligibility, validate_event  # noqa: E402

WIKI_URL = "https://en.wikipedia.org/wiki/Historical_components_of_the_S%26P_500"
EVENT_FIELDS = [
    "event_id", "index_id", "ticker", "security", "direction", "announcement_date",
    "effective_date", "availability_date", "source_url", "evidence_status",
    "target_weight_change", "tracking_assets", "fund_assets_date", "pre_event_price",
    "price_date", "forced_shares", "eligibility", "exclusion_reason",
]
SUMMARY_FIELDS = ["metric", "value", "notes"]


class _FirstTableParser(HTMLParser):
    """Collect the first HTML table without requiring an HTML dependency."""

    def __init__(self) -> None:
        super().__init__()
        self.table_state = 0
        self.row: list[tuple[str, list[str]]] | None = None
        self.cell_parts: list[str] | None = None
        self.cell_links: list[str] = []
        self.rows: list[list[tuple[str, list[str]]]] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "table" and self.table_state == 0:
            self.table_state = 1
        elif self.table_state == 1 and tag == "tr":
            self.row = []
        elif self.table_state == 1 and tag in {"td", "th"} and self.row is not None:
            self.cell_parts = []
            self.cell_links = []
        elif self.table_state == 1 and tag == "a" and self.cell_parts is not None:
            href = dict(attrs).get("href", "")
            if href:
                self.cell_links.append(href)

    def handle_data(self, data: str) -> None:
        if self.table_state == 1 and self.cell_parts is not None:
            self.cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.table_state == 1 and tag in {"td", "th"} and self.row is not None:
            text = " ".join("".join(self.cell_parts or []).split())
            self.row.append((text, list(self.cell_links)))
            self.cell_parts = None
            self.cell_links = []
        elif self.table_state == 1 and tag == "tr" and self.row is not None:
            if self.row:
                self.rows.append(self.row)
            self.row = None
        elif tag == "table" and self.table_state == 1:
            self.table_state = 2


def fetch_html(url: str) -> str:
    request = Request(url, headers={"User-Agent": "GQH public research contact research@example.org"})
    with urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8", errors="replace")


def _parse_date(value: str) -> dt.date | None:
    try:
        return dt.datetime.strptime(value.strip(), "%B %d, %Y").date()
    except ValueError:
        return None


def _ticker(value: str) -> str:
    value = value.strip().replace("\u2014", "").replace("-", "")
    return value if value and value.lower() not in {"n/a", "none"} else ""


def parse_events(html: str, start: str, end: str, source_url: str = WIKI_URL) -> list[dict]:
    start_date = dt.date.fromisoformat(start)
    end_date = dt.date.fromisoformat(end)
    parser = _FirstTableParser()
    parser.feed(html)
    events = []
    for cells in parser.rows:
        if len(cells) < 7:
            continue
        effective = _parse_date(cells[0][0])
        if effective is None or not start_date <= effective <= end_date:
            continue
        additions = (_ticker(cells[1][0]), cells[2][0])
        deletions = (_ticker(cells[3][0]), cells[4][0])
        for direction, (ticker, security) in (("addition", additions), ("deletion", deletions)):
            if not ticker:
                continue
            row = {
                "event_id": f"sp500-{effective.isoformat()}-{ticker}-{direction}",
                "index_id": "sp500",
                "ticker": ticker,
                "security": security,
                "direction": direction,
                "announcement_date": "",
                "effective_date": effective.isoformat(),
                "availability_date": "",
                "source_url": source_url,
                "evidence_status": "secondary_public",
                "target_weight_change": "",
                "tracking_assets": "",
                "fund_assets_date": "",
                "pre_event_price": "",
                "price_date": "",
                "forced_shares": "",
                "eligibility": "excluded",
                "exclusion_reason": "",
            }
            validate_event(row)
            eligible, reason = event_eligibility(row, end)
            row["eligibility"] = "eligible" if eligible else "excluded"
            row["exclusion_reason"] = "" if eligible else reason
            events.append(row)
    events.sort(key=lambda row: (row["effective_date"], row["direction"], row["ticker"]))
    return events


def summary(events: list[dict], start: str, end: str) -> list[dict]:
    dates = sorted({row["effective_date"] for row in events})
    additions = sum(row["direction"] == "addition" for row in events)
    deletions = sum(row["direction"] == "deletion" for row in events)
    eligible = sum(row["eligibility"] == "eligible" for row in events)
    primary = sum(row["evidence_status"] == "primary" for row in events)
    quantities = sum(bool(row["forced_shares"]) for row in events)
    return [
        {"metric": "development_start", "value": start, "notes": "inclusive"},
        {"metric": "development_end", "value": end, "notes": "inclusive; no holdout opened"},
        {"metric": "event_legs", "value": str(len(events)), "notes": "one row per added or removed ticker"},
        {"metric": "effective_dates", "value": str(len(dates)), "notes": "unique dates"},
        {"metric": "additions", "value": str(additions), "notes": "discovery inventory"},
        {"metric": "deletions", "value": str(deletions), "notes": "discovery inventory"},
        {"metric": "primary_evidence_rows", "value": str(primary), "notes": "required for returns"},
        {"metric": "forced_quantity_rows", "value": str(quantities), "notes": "requires pre-effective holdings and price"},
        {"metric": "eligible_return_rows", "value": str(eligible), "notes": "none may use guessed clocks or quantities"},
        {"metric": "conclusion", "value": "coverage inventory only", "notes": "No return study until primary clocks and quantities are verified."},
    ]


def _write(path: Path, fields: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=WIKI_URL)
    parser.add_argument("--start", default="2015-07-01")
    parser.add_argument("--end", default="2022-09-30")
    parser.add_argument("--out", default="results/index-mandate-events.csv")
    parser.add_argument("--summary-out", default="results/index-mandate-study.csv")
    args = parser.parse_args(argv)
    html = fetch_html(args.url)
    events = parse_events(html, args.start, args.end, args.url)
    if not events:
        raise SystemExit("no historical index events found in the declared window")
    _write(ROOT / args.out, EVENT_FIELDS, events)
    _write(ROOT / args.summary_out, SUMMARY_FIELDS, summary(events, args.start, args.end))
    print(f"wrote {args.out} ({len(events)} event legs)")
    print(f"wrote {args.summary_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
