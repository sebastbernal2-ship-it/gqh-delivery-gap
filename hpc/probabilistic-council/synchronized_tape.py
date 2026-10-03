"""Audit pinned WebSocket mirrors and join only information recorded by a decision clock.

Recorded timestamps are an UNVERIFIED availability proxy, not evidence of executable latency.
No account identifiers, raw payloads, signed URLs or price outcomes enter the public audit.
"""
from __future__ import annotations

import argparse
from bisect import bisect_right
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import re

NS = 1_000_000_000
MAX_BOOK_AGE_NS = 2 * NS
HISTORY_NS = 30 * NS
MIN_OVERLAP_NS = 600 * NS
LOWER_NS = 1735689600 * NS  # 2025-01-01; excludes the closed project holdouts
UPPER_NS = 1798761600 * NS  # 2027-01-01; unit guard, not an approved research interval


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def utc(ns):
    return (datetime(1970, 1, 1, tzinfo=timezone.utc) +
            timedelta(microseconds=(ns + 999) // 1000)).isoformat()


def clock(value, multiplier):
    if type(value) is not int or not LOWER_NS <= value * multiplier < UPPER_NS:
        raise ValueError('exact integer clock with declared ns/ms unit required in 2025-2026')
    return value * multiplier


def positive(value):
    if isinstance(value, bool):
        raise ValueError('positive finite price/size required')
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise ValueError('positive finite price/size required')
    return result


@dataclass(frozen=True)
class Book:
    event_ns: int
    recorded_ns: int
    bids: tuple[tuple[float, float], ...]
    asks: tuple[tuple[float, float], ...]
    source_ref: str

    @property
    def mid(self):
        return (self.bids[0][0] + self.asks[0][0]) / 2


@dataclass(frozen=True)
class Trade:
    event_ns: int
    recorded_ns: int
    tid: int
    side: str
    price: float
    size: float
    source_ref: str


def parse_messages(rows, kind, source_sha, coin='BTC'):
    """Project before retaining records; never retain the users/hash payload fields."""
    if kind not in ('books', 'trades') or not re.fullmatch('[0-9a-f]{64}', source_sha):
        raise ValueError('declared kind and SHA-256 required')
    observations, counts = [], Counter()
    channel = 'l2Book' if kind == 'books' else 'trades'
    for index, recorded, outer_coin, payload in rows:
        counts['source_rows'] += 1
        if outer_coin != coin:
            counts['other_coin_rows'] += 1
            continue
        recorded = clock(recorded, 1)
        raw = json.loads(payload)
        if raw.get('channel') != channel:
            raise ValueError('unexpected WebSocket channel')
        data = raw['data']
        events = [data] if kind == 'books' else data
        if not isinstance(events, list) or not events:
            raise ValueError('nonempty message events required')
        for j, item in enumerate(events):
            if item.get('coin') != coin:
                raise ValueError('outer/inner coin mismatch')
            event = clock(item['time'], 1_000_000)
            if event > recorded:
                raise ValueError('event clock is later than recorded clock')
            ref = f'{source_sha}:row-{index}:event-{j}'
            if kind == 'books':
                levels = item['levels']
                if not isinstance(levels, list) or len(levels) != 2 or any(len(s) < 5 for s in levels):
                    raise ValueError('five bid and ask levels required')
                sides = tuple(tuple((positive(v['px']), positive(v['sz'])) for v in side) for side in levels)
                bids, asks = sides
                bp, ap = [v[0] for v in bids], [v[0] for v in asks]
                if (bp != sorted(bp, reverse=True) or ap != sorted(ap) or
                        len(set(bp)) != len(bp) or len(set(ap)) != len(ap) or bp[0] >= ap[0]):
                    raise ValueError('unsorted, duplicate-price, locked or crossed book')
                observations.append(Book(event, recorded, bids, asks, ref))
            else:
                if item.get('side') not in ('A', 'B') or type(item.get('tid')) is not int or item['tid'] < 0:
                    raise ValueError('trade side A/B and nonnegative integer tid required')
                observations.append(Trade(event, recorded, item['tid'], item['side'],
                                          positive(item['px']), positive(item['sz']), ref))
            counts['selected_events'] += 1
    # Stable first-recorded observation wins on an exact retransmission. A conflicting identity
    # fails rather than averaging it or choosing whichever payload would improve a prediction.
    observations.sort(key=lambda x: (x.recorded_ns, x.event_ns))
    unique = {}
    for x in observations:
        key = x.event_ns if kind == 'books' else (x.event_ns, x.tid)
        content = (x.bids, x.asks) if kind == 'books' else (x.side, x.price, x.size)
        if key in unique:
            before = unique[key]
            previous = (before.bids, before.asks) if kind == 'books' else (before.side, before.price, before.size)
            if content != previous:
                raise ValueError('conflicting duplicate identity')
            counts['exact_retransmissions'] += 1
        else:
            unique[key] = x
    result = sorted(unique.values(), key=lambda x: (x.recorded_ns, x.event_ns))
    counts['unique_events'] = len(result)
    return result, dict(counts)


def parquet_rows(path):
    """PyArrow is optional except at the acquisition boundary. Never float-convert timestamps."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    p = pq.ParquetFile(path)
    if p.schema_arrow.names != ['timestamp', 'coin', 'payload'] or p.schema_arrow.field('timestamp').type != pa.timestamp('ns'):
        raise ValueError('expected exact timestamp[ns], coin, payload mirror schema')
    index = 0
    for batch in p.iter_batches(batch_size=2048):
        times = batch.column('timestamp').cast(pa.int64()).to_pylist()
        for t, c, payload in zip(times, batch.column('coin').to_pylist(), batch.column('payload').to_pylist()):
            yield index, t, c, payload
            index += 1


class CausalTape:
    def __init__(self, books, trades):
        self.books = sorted(books, key=lambda x: (x.recorded_ns, x.event_ns))
        self.trades = sorted(trades, key=lambda x: (x.recorded_ns, x.event_ns))
        self.book_states = []
        latest_event = -1
        for book in self.books:
            if book.event_ns > latest_event:
                self.book_states.append(book)
                latest_event = book.event_ns
        self.book_times = [x.recorded_ns for x in self.book_states]
        self.trade_times = [x.recorded_ns for x in self.trades]

    def book_at(self, decision_ns):
        # An out-of-order old event must never replace a newer already-known book state.
        index = bisect_right(self.book_times, decision_ns) - 1
        if index < 0:
            raise ValueError('missing past book')
        b = self.book_states[index]
        if decision_ns - b.event_ns > MAX_BOOK_AGE_NS:
            raise ValueError('stale book')
        return b

    def features_at(self, decision_ns):
        clock(decision_ns, 1)
        b = self.book_at(decision_ns)
        start = decision_ns - HISTORY_NS
        old = self.book_at(start)
        lag = self.book_at(decision_ns - 5 * NS)
        # Rolling volatility uses only states known at this decision; out-of-order retransmissions
        # cannot rewind the book. Fail on a history gap instead of silently forward-filling it.
        history_start = bisect_right(self.book_times, start) - 1
        states = self.book_states[history_start:bisect_right(self.book_times, decision_ns)]
        if any(right.event_ns - left.event_ns > MAX_BOOK_AGE_NS for left, right in zip(states, states[1:])):
            raise ValueError('book history gap')
        window = [t for t in self.trades[bisect_right(self.trade_times, start):bisect_right(self.trade_times, decision_ns)]
                  if start < t.event_ns <= decision_ns]
        total = sum(t.size for t in window)
        reported_flow = sum((1 if t.side == 'B' else -1) * t.size for t in window)
        bid, ask = sum(v[1] for v in b.bids[:5]), sum(v[1] for v in b.asks[:5])
        rv = math.sqrt(sum((1e4 * math.log(right.mid / left.mid))**2 for left, right in zip(states, states[1:])))
        values = ((b.asks[0][0] - b.bids[0][0]) / b.mid * 1e4, (bid - ask) / (bid + ask),
                  reported_flow / total if total else 0.0, math.log1p(total),
                  (b.mid / lag.mid - 1) * 1e4, rv)
        if not all(math.isfinite(v) for v in values):
            raise ValueError('nonfinite aggregated feature')
        return {'decision_ns': decision_ns, 'features': values,
                'feature_available_ns': [decision_ns] * 6,
                'book_ref': b.source_ref, 'history_start_ref': old.source_ref,
                'trade_refs': [t.source_ref for t in window], 'observed_trade_count': len(window),
                'trade_zero_note': 'zero observed volume is not proof of complete trade coverage'}


def summarize(observations):
    if not observations:
        return {'events': 0}
    lags = sorted(x.recorded_ns - x.event_ns for x in observations)
    times = sorted(set(x.event_ns for x in observations))
    gaps = [b - a for a, b in zip(times, times[1:])]
    return dict(events=len(observations), first_event_ns=min(times), last_event_ns=max(times),
                first_recorded_ns=min(x.recorded_ns for x in observations),
                last_recorded_ns=max(x.recorded_ns for x in observations),
                recorded_minus_event_ns={'min': lags[0], 'median': lags[len(lags)//2], 'max': lags[-1]},
                event_gaps_over_2s=sum(g > MAX_BOOK_AGE_NS for g in gaps),
                max_event_gap_ns=max(gaps, default=0))


def audit(plan_path, objects, output):
    plan = json.loads(Path(plan_path).read_text())
    files = plan['files']
    if len(files) != 2 or {x['kind'] for x in files} != {'books', 'trades'}:
        raise ValueError('one book and one trade file required')
    streams, sources, counts = {}, [], {}
    for e in files:
        sha = e['sha256']
        if not re.fullmatch('[0-9a-f]{64}', sha) or type(e['size']) is not int or not 0 < e['size'] <= 500_000_000:
            raise ValueError('bounded publisher identity required')
        path = Path(objects) / sha
        if path.stat().st_size != e['size'] or digest(path) != sha:
            raise ValueError('source bytes disagree with pinned publisher identity')
        streams[e['kind']], counts[e['kind']] = parse_messages(parquet_rows(path), e['kind'], sha)
        sources.append(e)
    summaries = {k: summarize(v) for k, v in streams.items()}
    reasons = []
    overlap = None
    if any(not s for s in streams.values()):
        reasons.append('empty selected stream')
    else:
        lo = max(s['first_recorded_ns'] for s in summaries.values())
        hi = min(s['last_recorded_ns'] for s in summaries.values())
        overlap = {'start_ns': lo, 'end_ns': hi, 'duration_ns': max(0, hi-lo)}
        if hi - lo < MIN_OVERLAP_NS:
            reasons.append('less than ten minutes of recorded-clock overlap; five-role training blocked')
    tape = CausalTape(streams['books'], streams['trades'])
    states, excluded = [], Counter()
    if overlap:
        # Fixed 6s schedule, anchored to first common recorded clock, independent of outcomes.
        for decision in range(overlap['start_ns'] + HISTORY_NS, overlap['end_ns'], 6*NS):
            try:
                states.append(tape.features_at(decision))
            except ValueError as e:
                excluded[str(e)] += 1
    receipt = dict(scope='development_only', coin='BTC', sources=sources,
                   plan_sha256=digest(plan_path), adapter_sha256=digest(__file__),
                   availability_basis='retrospective_assumption',
                   availability_note='Parquet recorded timestamp is an unverified receipt-time proxy; never join solely on venue event time',
                   summaries=summaries, counts=counts, overlap=overlap,
                   feature_order=['spread_bps','depth_imbalance','reported_flow_30s','log_observed_volume_30s','move_5s_bps','rv_30s_bps'],
                   groups={'A':[0,1], 'B':[2,3], 'C':[4,5]}, causal_states=len(states), exclusions=dict(excluded),
                   panel_candidate_ready=not reasons and bool(states), training_run_performed=False,
                   panel_blockers=reasons or ([] if states else ['no valid causal states']),
                   limitations=['third-party mirror byte equivalence to venue unverified',
                                'recorded-clock meaning and feed completeness unverified',
                                'aggregated L2 snapshots, not order-level L4 or queue replay',
                                'trade prints, not account fills; liquidation labels unavailable',
                                'trade side retained as reported, aggressor semantics not verified',
                                'single short session, no independent regime or execution evidence'])
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    (output / 'states.jsonl').write_text(''.join(json.dumps(x, sort_keys=True)+'\n' for x in states))
    receipt['states_sha256'] = digest(output / 'states.jsonl')
    (output / 'audit.json').write_text(json.dumps(receipt, indent=2, sort_keys=True)+'\n')
    return receipt


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan', type=Path, required=True)
    p.add_argument('--objects', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(audit(a.plan, a.objects, a.output), indent=2, sort_keys=True))
