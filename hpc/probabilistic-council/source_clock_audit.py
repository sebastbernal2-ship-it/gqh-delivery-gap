"""OFF-CLUSTER: inspect training-source clocks without computing features or labels.

The receipt contains counts and clocks only, never prices or participant identifiers.
Negative lags are reported, not shifted, filtered away, or interpreted as latency.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from fetch_public_plan import load_plan
from synchronized_tape import NS, clock, digest, parquet_rows


def inspect_rows(rows, kind, coin='BTC'):
    channel = {'books': 'l2Book', 'trades': 'trades'}[kind]
    counts = Counter()
    coins = Counter()
    recorded_times, event_times, lags = [], [], []
    previous_recorded = previous_event = None
    for _, recorded, outer_coin, payload in rows:
        counts['source_rows'] += 1
        coins[outer_coin] += 1
        if outer_coin != coin:
            continue
        counts['selected_rows'] += 1
        recorded = clock(recorded, 1)
        raw = json.loads(payload)
        if raw.get('channel') != channel:
            raise ValueError('unexpected channel')
        events = [raw['data']] if kind == 'books' else raw['data']
        if not isinstance(events, list) or not events:
            raise ValueError('nonempty events required')
        recorded_times.append(recorded)
        if previous_recorded is not None and recorded < previous_recorded:
            counts['recorded_row_reversals'] += 1
        previous_recorded = recorded
        for item in events:
            if item.get('coin') != coin:
                raise ValueError('outer/inner coin mismatch')
            event = clock(item['time'], 1_000_000)
            event_times.append(event)
            lags.append(recorded-event)
            counts['selected_events'] += 1
            if event > recorded:
                counts['event_later_than_recorded'] += 1
            if recorded-event > 2*NS:
                counts['lag_over_2s'] += 1
            if previous_event is not None and event < previous_event:
                counts['event_order_reversals'] += 1
            previous_event = event
    summary = {'counts': dict(counts), 'instrument_row_counts': dict(sorted(coins.items()))}
    if not lags:
        return summary
    ordered_lags = sorted(lags)
    unique_events = sorted(set(event_times))
    gaps = [b-a for a, b in zip(unique_events, unique_events[1:])]
    summary.update(
        first_recorded_ns=min(recorded_times), last_recorded_ns=max(recorded_times),
        first_event_ns=min(event_times), last_event_ns=max(event_times),
        recorded_minus_event_ns={
            name: ordered_lags[min(len(lags)-1, int(q*(len(lags)-1)))]
            for name, q in [('min',0), ('p01',.01), ('median',.5), ('p99',.99), ('max',1)]},
        unique_event_timestamps=len(unique_events),
        event_gaps_over_2s=sum(g > 2*NS for g in gaps),
        max_event_gap_ns=max(gaps, default=0))
    return summary


def audit(source_plan, sample_plan, objects):
    """Only exact training-role objects from the frozen parent plan may be opened."""
    parent, _ = load_plan(source_plan)
    sample, _ = load_plan(sample_plan)
    expected = {e['sha256']: e for e in parent['files']}
    if len(sample['files']) != 2 or {e['kind'] for e in sample['files']} != {'books','trades'}:
        raise ValueError('one paired book/trade interval required')
    if len({e['pair_id'] for e in sample['files']}) != 1:
        raise ValueError('matched pair required')
    # Validate the whole subset before touching any object, including on a bad second entry.
    for entry in sample['files']:
        if expected.get(entry['sha256']) != entry:
            raise ValueError('audit subset must match frozen source entries exactly')
        if parent['session_roles'][entry['session']] != 'training':
            raise ValueError('source QA may only open training-role data')
    summaries = {}
    for entry in sample['files']:
        path = Path(objects)/entry['sha256']
        if path.stat().st_size != entry['size'] or digest(path) != entry['sha256']:
            raise ValueError('publisher bytes/hash mismatch')
        summaries[entry['kind']] = inspect_rows(parquet_rows(path), entry['kind'])
    blockers = []
    for kind, stats in summaries.items():
        if not stats['counts'].get('selected_events'):
            blockers.append(f'{kind}: empty selected stream')
        if stats['counts'].get('event_later_than_recorded'):
            blockers.append(f'{kind}: venue event later than recorded timestamp')
    return {
        'schema_version':'execution-source-clock-audit-v1', 'scope':'development_only',
        'coin':'BTC', 'parent_plan_sha256':digest(source_plan),
        'sample_plan_sha256':digest(sample_plan), 'audit_code_sha256':digest(__file__),
        'sources':sample['files'], 'summaries':summaries,
        'clock_contract_blockers':blockers,
        'numeric_clock_contract_passed':not blockers,
        'availability_verified':False, 'labels_computed':False, 'training_run_performed':False,
        'limitations':[
            'sample QA does not prove archive completeness or collector lineage',
            'timezone, clock synchronization and receipt semantics require separate evidence',
            'no price features, targets, prediction ranking or latency claim computed']}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-plan', type=Path, required=True)
    p.add_argument('--sample-plan', type=Path, required=True)
    p.add_argument('--objects', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    receipt = audit(a.source_plan, a.sample_plan, a.objects)
    with a.output.open('x') as f:
        f.write(json.dumps(receipt, indent=2, sort_keys=True)+'\n')
    print(json.dumps({'numeric_clock_contract_passed':receipt['numeric_clock_contract_passed'],
                      'clock_contract_blockers':receipt['clock_contract_blockers']}, indent=2))
