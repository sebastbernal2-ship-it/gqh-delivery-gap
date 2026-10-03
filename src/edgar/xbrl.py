"""Structured facts from XBRL, joined to the moment they became public.

Why this instead of reading filing prose: every XBRL fact carries the accession that reported it, so a
fact can be joined to the acceptance timestamp in the filings register. That gives a number, its period,
and the moment it was public, without parsing a document.

Two honesty rules, both from the filings audit:

1. **A field is not a delay label.** A fall in remaining performance obligations is a revision to
   contracted promises, not proof that a project slipped, and it does not identify a project. Fields are
   reported one at a time and never pooled into a single delay score.
2. **A quantity is not an expectation.** These are reported balances at a period end. A promised date is
   a different object, and it lives in the monthly inventories, not here.
"""
from __future__ import annotations

import json
from pathlib import Path

COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
DEFAULT_CACHE = Path(__file__).resolve().parents[2] / "results" / "edgar-cache"

# Fields that describe promised or disputed work. Each is reported separately on purpose.
INTERESTING = (
    "RevenueRemainingPerformanceObligation",
    "UnapprovedChangeOrdersAmount",
    "OrderBacklog",
)


def facts_url(cik: int) -> str:
    return COMPANY_FACTS_URL.format(cik=cik)


def load_company_facts(cik: int, session, cache_dir: Path | None = None) -> dict:
    """Company facts, cached by CIK. One request per firm, so the cache is the whole rate-limit story."""
    cache_dir = cache_dir if cache_dir is not None else DEFAULT_CACHE
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached = cache_dir / f"companyfacts-{cik}.json"
    if cached.exists():
        try:
            return json.loads(cached.read_text())
        except (OSError, ValueError):
            pass  # a damaged cache must never be fatal
    response = session.get(facts_url(cik), timeout=120)
    response.raise_for_status()
    payload = response.json()
    cached.write_text(json.dumps(payload))
    return payload


def extract(payload: dict, cik: int, ticker: str, concepts=INTERESTING) -> list[dict]:
    """One row per fact for the requested concepts, newest period first."""
    wanted = set(concepts)
    rows: list[dict] = []
    for namespace, entries in (payload.get("facts") or {}).items():
        for name, body in entries.items():
            if name not in wanted:
                continue
            for unit, facts in (body.get("units") or {}).items():
                for fact in facts:
                    rows.append({
                        "ticker": ticker,
                        "cik": cik,
                        "concept": f"{namespace}:{name}",
                        "unit": unit,
                        "period_end": fact.get("end") or "",
                        "value": fact.get("val"),
                        "form": fact.get("form") or "",
                        "accession": fact.get("accn") or "",
                        "filed": fact.get("filed") or "",
                        "frame": fact.get("frame") or "",
                        "source_receipt": facts_url(cik),
                    })
    rows.sort(key=lambda r: (r["concept"], r["period_end"], r["filed"]))
    return rows


def attach_availability(rows: list[dict], register: list[dict]) -> list[dict]:
    """Join each fact to the acceptance timestamp and earliest availability of its own accession."""
    by_accession = {r.get("accession"): r for r in register if r.get("accession")}
    for row in rows:
        filing = by_accession.get(row["accession"], {})
        row["acceptance_utc"] = filing.get("acceptance_utc", "")
        row["earliest_availability_utc"] = filing.get("earliest_availability_utc", "")
        row["availability_status"] = ("acceptance recorded" if filing.get("acceptance_utc")
                                      else "no matching filing row")
        row["in_sealed_window"] = filing.get("in_sealed_window", "")
    return rows


def revisions(rows: list[dict]) -> list[dict]:
    """Period-over-period change in one field, per unit, with the lag to public availability.

    A negative change means contracted work left the book. That is a revision to a promise. It is not a
    delayed project, and this function refuses to call it one.
    """
    by_key: dict[tuple, list[dict]] = {}
    for row in rows:
        by_key.setdefault((row["concept"], row["unit"]), []).append(row)
    out: list[dict] = []
    for (concept, unit), group in by_key.items():
        ordered = sorted(group, key=lambda r: (r["period_end"], r["filed"]))
        previous = None
        for row in ordered:
            change = ""
            if previous is not None and isinstance(row["value"], (int, float)) \
                    and isinstance(previous["value"], (int, float)):
                change = row["value"] - previous["value"]
            out.append({**row, "previous_value": "" if previous is None else previous["value"],
                        "change": change})
            previous = row
    return out


def days_to_public(row: dict) -> int | None:
    """Days from the period end to the moment the number was public. This is the information lag."""
    if not row.get("period_end") or not row.get("earliest_availability_utc"):
        return None
    import datetime as dt
    try:
        period = dt.date.fromisoformat(row["period_end"][:10])
        public = dt.date.fromisoformat(row["earliest_availability_utc"][:10])
    except ValueError:
        return None
    return (public - period).days
