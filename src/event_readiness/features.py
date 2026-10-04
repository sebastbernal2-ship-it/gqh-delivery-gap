"""Deterministic reviewed statement revisions. No market returns, model fitting or warehouse writes."""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, fields
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, localcontext
import hashlib
import re
from statistics import median
from zoneinfo import ZoneInfo

from .archive import canonical_hash, SHA, ACCESSION

UTC = timezone.utc
ET = ZoneInfo("America/New_York")
VERSION = "reviewed-statement-v1"
# Canonical mechanism development fence; no --open-sealed or custom later end in this component.
START = datetime(2015, 7, 1, tzinfo=UTC)
END = datetime(2022, 10, 1, tzinfo=UTC)


def timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(UTC)


def publication_time(basis: str, value: str) -> datetime:
    if basis == "date_upper_bound":
        return datetime.combine(date.fromisoformat(value) + timedelta(days=1), time.min, ET).astimezone(UTC)
    if basis not in ("verified_public_time", "sec_acceptance"):
        raise ValueError("publication basis cannot be inferred from retrieval or period end")
    return timestamp(value)


def exact(value: str) -> Decimal:
    if not isinstance(value, str):
        raise ValueError("decimal values must be source-preserving strings, never floats")
    result = Decimal(value)
    if not result.is_finite():
        raise ValueError("nonfinite decimal")
    # SQL NUMBER(38,12) input boundary. Do not silently round a source measurement.
    if result.as_tuple().exponent < -12 or abs(result) >= Decimal(10) ** 26:
        raise ValueError("decimal exceeds NUMBER(38,12) boundary")
    return result


def decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    with localcontext() as ctx:
        ctx.prec = 64
        value = value.quantize(Decimal("0.000000000001"))
    return format(value, "f")


@dataclass(frozen=True)
class Fact:
    fact_id: str
    event_cluster_id: str
    issuer_cik: str
    ticker: str
    security_id: str
    accession: str
    form: str
    metric_name: str
    fact_kind: str
    unit: str
    currency: str
    scope: str
    definition_version: str
    target_period: str
    comparability_group: str
    value_text: str
    value_decimal: str
    source_document_url: str
    document_sha256: str
    source_span_start: int
    source_span_end: int
    source_quote: str
    input_batch_sha256: str
    publication_basis: str
    published_at: str
    review_status: str
    reviewer_id: str
    reviewed_at: str
    exposure_status: str
    exposure_evidence_id: str
    extractor_version: str
    expectation_id: str | None = None
    supersedes_id: str | None = None
    value_scale_decimal: str = "1"

    @classmethod
    def from_dict(cls, record: dict) -> "Fact":
        allowed = {field.name for field in fields(cls)}
        if set(record) - allowed:
            raise ValueError("unknown fact fields: labels and extra inputs are not allowed")
        obj = cls(**record)
        for field in fields(cls):
            if field.name in ("expectation_id", "supersedes_id"):
                if getattr(obj, field.name) is not None and not isinstance(getattr(obj, field.name), str):
                    raise ValueError("optional identifiers must be strings or null")
            elif field.name not in ("source_span_start", "source_span_end"):
                if not isinstance(getattr(obj, field.name), str):
                    raise ValueError("fact fields must use declared string types")
        for name in ("fact_id", "event_cluster_id", "issuer_cik", "ticker", "security_id", "accession",
                     "metric_name", "fact_kind", "unit", "scope", "definition_version", "target_period",
                     "comparability_group", "source_document_url", "source_quote", "value_text", "extractor_version"):
            if not getattr(obj, name).strip():
                raise ValueError("missing required fact identity or provenance")
        if not obj.issuer_cik.isdigit() or len(obj.issuer_cik) != 10:
            raise ValueError("issuer CIK must be zero-padded to ten digits")
        if not ACCESSION.fullmatch(obj.accession):
            raise ValueError("invalid accession")
        for digest in (obj.document_sha256, obj.input_batch_sha256):
            if not SHA.fullmatch(digest):
                raise ValueError("invalid input digest")
        if not obj.source_document_url.startswith("https://"):
            raise ValueError("source URL must be HTTPS")
        if (type(obj.source_span_start) is not int or type(obj.source_span_end) is not int
                or not 0 <= obj.source_span_start < obj.source_span_end):
            raise ValueError("invalid source byte span")
        normalized = exact(obj.value_decimal)
        scale = exact(obj.value_scale_decimal)
        if scale <= 0 or not re.fullmatch(r"[+-]?(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)(?:\.[0-9]+)?", obj.value_text):
            raise ValueError("source numeric token or normalization scale invalid")
        with localcontext() as ctx:
            ctx.prec = 64
            if Decimal(obj.value_text.replace(",", "")) * scale != normalized:
                raise ValueError("normalized value disagrees with source token and explicit scale")
        obj.available_at()
        if obj.review_status not in ("reviewed", "unreviewed", "rejected"):
            raise ValueError("invalid review status")
        if obj.exposure_status not in ("verified", "ambiguous", "unmatched"):
            raise ValueError("invalid exposure status")
        if obj.reviewed_at and timestamp(obj.reviewed_at) < obj.available_at():
            raise ValueError("review timestamp precedes source publication")
        return obj

    def available_at(self) -> datetime:
        return publication_time(self.publication_basis, self.published_at)

    def series_key(self) -> tuple:
        return (self.issuer_cik, self.security_id, self.metric_name, self.fact_kind, self.unit,
                self.currency, self.scope, self.definition_version, self.comparability_group)

    def comparison_key(self) -> tuple:
        return self.series_key() + (self.target_period,)


def evidence_problems(fact: Fact, documents: dict[str, bytes]) -> list[str]:
    reasons = []
    if fact.review_status != "reviewed" or not fact.reviewer_id or not fact.reviewed_at:
        reasons.append("human_review_missing")
    if fact.exposure_status != "verified" or not fact.exposure_evidence_id:
        reasons.append("exposure_not_verified")
    content = documents.get(fact.document_sha256)
    if content is None:
        reasons.append("document_bytes_missing")
    elif hashlib.sha256(content).hexdigest() != fact.document_sha256:
        reasons.append("document_hash_mismatch")
    elif content[fact.source_span_start:fact.source_span_end] != fact.source_quote.encode("utf-8"):
        reasons.append("source_span_mismatch")
    if fact.value_text not in fact.source_quote:
        reasons.append("value_text_not_in_quote")
    return reasons


def _subtract(a: str, b: str) -> Decimal:
    with localcontext() as ctx:
        ctx.prec = 64
        return exact(a) - exact(b)


def build_features(records: list[dict], documents: dict[str, bytes], *, min_history: int = 5,
                   processing_seconds: int = 60) -> dict:
    """Build a retrospective, source-time-safe DEVELOPMENT feature panel with explicit exclusions.

    Today's reviews reconstruct historical source information. They do not establish historical
    model availability. Future-source records are counted as fenced before numeric interpretation.
    """
    if type(min_history) is not int or min_history < 2 or type(processing_seconds) is not int or processing_seconds < 1:
        raise ValueError("declare positive processing lag and at least two prior clusters")
    facts = {}
    duplicates = 0
    fenced = 0
    # The narrow header gate avoids reading/validating numerical content beyond the sealed fence.
    for record in records:
        header = {k: record[k] for k in ("publication_basis", "published_at")}
        public = publication_time(header["publication_basis"], header["published_at"])
        if not START <= public < END:
            fenced += 1
            continue
        fact = Fact.from_dict(record)
        if fact.fact_id in facts:
            if facts[fact.fact_id] != fact:
                raise ValueError("conflicting duplicate fact ID; version the amendment")
            duplicates += 1
        facts[fact.fact_id] = fact
    natural_keys = set()
    for fact in facts.values():
        key = (fact.accession, fact.comparison_key())
        if key in natural_keys:
            raise ValueError("duplicate economic statement within accession; resolve before feature generation")
        natural_keys.add(key)
    ordered = sorted(facts.values(), key=lambda f: (f.available_at(), f.fact_id))
    candidate = []
    excluded = []
    for fact in ordered:
        reasons = evidence_problems(fact, documents)
        decision = fact.available_at() + timedelta(seconds=processing_seconds)
        if decision >= END:
            reasons.append("decision_outside_development")
        prior = facts.get(fact.expectation_id)
        if prior is None:
            reasons.append("no_comparable_prior_expectation")
        else:
            if prior.available_at() >= fact.available_at():
                reasons.append("expectation_not_strictly_earlier")
            if prior.comparison_key() != fact.comparison_key():
                reasons.append("expectation_definition_scope_or_target_mismatch")
            if prior.fact_kind != "management_guidance" or fact.fact_kind != "management_guidance":
                reasons.append("unsupported_expectation_family")
            if prior.accession == fact.accession:
                reasons.append("same_accession_is_not_prior_expectation")
            reasons.extend("prior_" + reason for reason in evidence_problems(prior, documents))
            # A later already-public version cannot be skipped to manufacture a larger revision.
            intervening = [f for f in ordered if f.comparison_key() == fact.comparison_key()
                           and prior.available_at() < f.available_at() < fact.available_at()]
            if intervening:
                reasons.append("prior_expectation_superseded")
        if fact.supersedes_id:
            original = facts.get(fact.supersedes_id)
            if (original is None or original.available_at() >= fact.available_at()
                    or original.event_cluster_id != fact.event_cluster_id):
                reasons.append("invalid_amendment_lineage")
        if reasons:
            excluded.append({"fact_id": fact.fact_id, "ticker": fact.ticker,
                             "metric_name": fact.metric_name, "year": fact.available_at().year,
                             "reasons": sorted(set(reasons))})
            continue
        delta = _subtract(fact.value_decimal, prior.value_decimal)
        denominator = exact(prior.value_decimal)
        with localcontext() as ctx:
            ctx.prec = 64
            pct = delta / denominator if denominator > 0 else None
        candidate.append((fact, prior, delta, pct, decision))
    features = []
    for fact, prior, delta, pct, decision in candidate:
        # One prior revision per cluster, latest strictly BEFORE this publication. Current cluster
        # and simultaneous disclosures cannot contribute to the expanding normalizer.
        history = {}
        for other, earlier, change, _, _ in candidate:
            if (other.series_key() == fact.series_key() and other.available_at() < fact.available_at()
                    and other.event_cluster_id != fact.event_cluster_id):
                history[other.event_cluster_id] = (other.fact_id, change, canonical_hash(asdict(other)), canonical_hash(asdict(earlier)))
        values = [entry[1] for entry in history.values()]
        center = median(values) if values else None
        deviation = _subtract(str(delta), str(center)) if center is not None else None
        with localcontext() as ctx:
            ctx.prec = 64
            mad = median([abs(value - center) for value in values]) if values else None
            z = deviation / (Decimal("1.4826") * mad) if len(values) >= min_history and mad else None
        normalizer_reason = "insufficient_prior_clusters" if len(values) < min_history else ("zero_mad" if not mad else None)
        row = {"event_id": fact.fact_id, "event_cluster_id": fact.event_cluster_id,
               "issuer_cik": fact.issuer_cik, "ticker": fact.ticker, "security_id": fact.security_id,
               "metric_name": fact.metric_name, "fact_kind": fact.fact_kind, "unit": fact.unit,
               "currency": fact.currency, "scope": fact.scope, "target_period": fact.target_period,
               "definition_version": fact.definition_version, "expectation_type": "management_guidance",
               "expectation_id": prior.fact_id, "expectation_available_at": prior.available_at().isoformat(),
               "available_at_utc": fact.available_at().isoformat(), "decision_at_utc": decision.isoformat(),
               "publication_basis": fact.publication_basis,
               "revision_abs": decimal_text(delta), "revision_pct": decimal_text(pct),
               "revision_pct_null_reason": "nonpositive_prior" if pct is None else None,
               "revision_vs_past_median": decimal_text(deviation), "past_mad_z": decimal_text(z),
               "normalizer_null_reason": normalizer_reason, "n_prior_events": len(values),
               "exposure_status": fact.exposure_status, "exposure_evidence_id": fact.exposure_evidence_id,
               "feature_version": VERSION,
               "fact_sha256": canonical_hash(asdict(fact)), "expectation_sha256": canonical_hash(asdict(prior)),
               "document_sha256": fact.document_sha256, "prior_document_sha256": prior.document_sha256,
               "input_batch_sha256": fact.input_batch_sha256,
               "history_fact_ids": sorted(entry[0] for entry in history.values()),
               "history_lineage": sorted([entry[0], entry[2], entry[3]] for entry in history.values())}
        row["feature_row_sha256"] = canonical_hash(row)
        features.append(row)
    coverage = Counter((f.ticker, f.metric_name, f.available_at().year) for f in ordered)
    reason_counts = Counter(reason for row in excluded for reason in row["reasons"])
    return {"schema_version": 1, "feature_version": VERSION,
            "mode": "retrospective_source_reconstruction", "strategy_ready": False,
            "remaining_gates": ["archive_reconciliation", "reviewed_market_and_sector_panel",
                                "approved_hypothesis_and_costs", "independent_event_adequacy"],
            "config": {"min_history": min_history, "processing_seconds": processing_seconds,
                       "development_start": START.isoformat(), "development_end_exclusive": END.isoformat()},
            "features": features, "exclusions": excluded, "exclusion_reason_counts": dict(sorted(reason_counts.items())),
            "duplicate_rows_removed": duplicates, "fenced_rows": fenced,
            "unique_event_clusters": len({f["event_cluster_id"] for f in features}),
            "coverage": [{"ticker": t, "metric_name": m, "year": y, "facts": n} for (t, m, y), n in sorted(coverage.items())]}


def next_session_close(available_at: str, sessions: list[dict]) -> str | None:
    """Conservative daily lag: first exchange session dated AFTER availability in New York.

    Caller supplies a pinned exchange calendar with date/open/close timestamps; no weekday heuristic.
    Return a reference timestamp, never an asserted fill. Half days and holidays come from the calendar.
    """
    available = timestamp(available_at)
    previous = None
    for session in sessions:
        day = date.fromisoformat(session["date"])
        opening, closing = timestamp(session["open"]), timestamp(session["close"])
        if (previous is not None and day <= previous) or opening >= closing:
            raise ValueError("calendar must be ordered unique sessions with valid open/close")
        if opening.astimezone(ET).date() != day or closing.astimezone(ET).date() != day:
            raise ValueError("exchange session timezone/date mismatch")
        previous = day
    return next((s["close"] for s in sessions if date.fromisoformat(s["date"]) > available.astimezone(ET).date()), None)
