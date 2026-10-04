#!/usr/bin/env python3
"""Fetch filing documents into the ignored cache and write a committed manifest.

Protocol: docs/plan/filing-specialist.md. The raw HTML and extracted text stay in
`results/edgar-cache/`, which is git ignored; the manifest commits statuses, hashes and counts
only. The SEC client and its agent rules come from `src/edgar/filings.py`, which owns them.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from edgar.filings import AGENT_HELP, RETRY_STATUS, _agent_refused, session, user_agent  # noqa: E402
from filing_specialist.text import excerpt, html_to_text, text_sha256  # noqa: E402

CACHE = ROOT / "results" / "edgar-cache"
DEFAULT_MANIFEST = ROOT / "results" / "filing-text-manifest.json"


def select_rows(rows: list[dict], tickers: set[str], forms: tuple[str, ...]) -> list[dict]:
    return [row for row in rows
            if row.get("ticker") in tickers
            and any(row.get("form", "").startswith(form) for form in forms)
            and (row.get("document_url") or "").strip()]


def fetch_text(http: requests.Session, url: str, tries: int = 4, sleeper=time.sleep) -> str:
    delay = 20
    last: Exception | None = None
    for attempt in range(tries):
        try:
            response = http.get(url, timeout=45)
        except requests.RequestException as error:
            last = error
        else:
            if response.status_code == 200:
                sleeper(0.4)  # the SEC asks for fewer than ten requests a second
                return response.text
            if _agent_refused(response):
                raise requests.HTTPError(f"{response.status_code} for {url}: {AGENT_HELP}")
            if response.status_code not in RETRY_STATUS:
                response.raise_for_status()
            last = requests.HTTPError(f"{response.status_code} for {url}")
        if attempt < tries - 1:
            sleeper(delay)
            delay = min(delay * 2, 120)
    raise last if last is not None else RuntimeError(f"no attempt made for {url}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--register", type=Path, default=ROOT / "results" / "filings-register.csv")
    parser.add_argument("--tickers", default="PWR,ETN")
    parser.add_argument("--forms", default="8-K")
    parser.add_argument("--limit", type=int, default=0, help="0 fetches every selected filing")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--cache", type=Path, default=CACHE)
    args = parser.parse_args()

    rows = list(csv.DictReader(args.register.open()))
    tickers = {item.strip().upper() for item in args.tickers.split(",") if item.strip()}
    forms = tuple(item.strip() for item in args.forms.split(",") if item.strip())
    selected = select_rows(rows, tickers, forms)
    if args.limit:
        selected = selected[:args.limit]
    if not selected:
        raise SystemExit("no filings matched the selection")

    args.cache.mkdir(parents=True, exist_ok=True)
    http = session()
    documents = []
    counts = {"selected": len(selected), "fetched": 0, "cached": 0, "failed": 0, "bytes": 0}
    for row in selected:
        accession = row["accession"]
        html_path = args.cache / f"{accession}.html"
        text_path = args.cache / f"{accession}.txt"
        record = {"accession": accession, "ticker": row["ticker"], "form": row["form"],
                  "url": row["document_url"]}
        try:
            if html_path.exists() and text_path.exists():
                html = html_path.read_text(errors="ignore")
                text = text_path.read_text(errors="ignore")
                record["status"] = "cached"
                counts["cached"] += 1
            else:
                html = fetch_text(http, row["document_url"])
                text = html_to_text(html)
                html_path.write_text(html)
                text_path.write_text(text)
                record["status"] = "fetched"
                counts["fetched"] += 1
        except Exception as error:  # a failure is a record, never a silent drop
            record["status"] = "failed"
            record["error"] = f"{type(error).__name__}: {error}"
            counts["failed"] += 1
            documents.append(record)
            continue
        record.update({
            "html_bytes": len(html.encode()),
            "html_sha256": text_sha256(html),
            "text_sha256": text_sha256(text),
            "text_chars": len(text),
            "excerpt_chars": len(excerpt(text)),
        })
        counts["bytes"] += record["html_bytes"]
        documents.append(record)

    manifest = {
        "schema": "filing-text-manifest-v1",
        "scope": "development_only",
        "user_agent": user_agent(),
        "selection": {"tickers": sorted(tickers), "forms": list(forms), "limit": args.limit,
                      "register": str(args.register.relative_to(ROOT))},
        "counts": counts,
        "cache": str(args.cache.relative_to(ROOT)),
        "documents": documents,
    }
    args.manifest.write_text(json.dumps(manifest, indent=1) + "\n")
    print(json.dumps({"counts": counts, "manifest": str(args.manifest)}, indent=1))
    return 0 if counts["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
