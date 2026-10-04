"""OFF-CLUSTER: prepare live movement-risk cases without crossing receipt segments.

The frozen local plan pins capture receipts and exported inventories. Paths remain local.
An insufficient plan produces a coverage receipt only, never a partial training cache.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import re
from pathlib import Path

import numpy as np

from execution_dataset import cases, FEATURES, HORIZONS
from execution_risk_dataset import SCHEMA, FILES, validate
from multisession_panel import PARTITIONS, merge_events
from synchronized_tape import digest, parquet_rows, parse_messages


def day(ns):
    return datetime.fromtimestamp(ns // 1_000_000_000, timezone.utc).date().isoformat()


def read_capture(entry):
    capture, objects = Path(entry['capture']), Path(entry['objects'])
    if digest(capture / 'capture.json') != entry['capture_receipt_sha256']:
        raise ValueError('capture receipt hash mismatch')
    if digest(objects / 'inventory.json') != entry['inventory_sha256']:
        raise ValueError('inventory hash mismatch')
    receipt = json.loads((capture / 'capture.json').read_text())
    inventory = json.loads((objects / 'inventory.json').read_text())
    journal = capture / 'messages.jsonl'
    if (receipt.get('schema_version') != 'execution-live-capture-v1'
            or inventory.get('schema_version') != 'execution-live-source-inventory-v1'
            or inventory.get('scope') != 'development_only'
            or receipt.get('clock_basis') != 'time.time_ns immediately after recv; paired with time.monotonic_ns'
            or inventory.get('clock_basis') != receipt.get('clock_basis')
            or digest(journal) != receipt['messages_sha256']
            or inventory['journal_sha256'] != receipt['messages_sha256']
            or inventory['capture_receipt_sha256'] != entry['capture_receipt_sha256']):
        raise ValueError('capture lineage mismatch')
    expected = {}
    previous = None
    for index, line in enumerate(journal.read_text().splitlines()):
        row = json.loads(line)
        if (type(row['sequence']) is not int or row['sequence'] != index
                or type(row['segment']) is not int or row['segment'] < 1
                or type(row['receipt_wall_ns']) is not int
                or type(row['receipt_monotonic_ns']) is not int):
            raise ValueError('invalid journal sequence/segment')
        if previous:
            if row['segment'] < previous['segment']:
                raise ValueError('segment reversal')
            if row['segment'] == previous['segment'] and (
                    row['receipt_wall_ns'] <= previous['receipt_wall_ns']
                    or row['receipt_monotonic_ns'] <= previous['receipt_monotonic_ns']
                    or abs((row['receipt_wall_ns'] - previous['receipt_wall_ns'])
                           - (row['receipt_monotonic_ns'] - previous['receipt_monotonic_ns'])) > 100_000_000):
                raise ValueError('unsegmented clock discontinuity')
        if row['coin'] != 'BTC':
            raise ValueError('instrument mismatch')
        kind = {'l2Book': 'books', 'trades': 'trades'}[row['payload']['channel']]
        expected.setdefault((row['segment'], kind), []).append((row['receipt_wall_ns'], row['payload']))
        previous = row
    streams = {}
    seen = set()
    for source in inventory['sources']:
        if (not isinstance(source.get('sha256'), str)
                or not re.fullmatch(r'[0-9a-f]{64}', source['sha256'])
                or type(source.get('size')) is not int or source['size'] < 0):
            raise ValueError('source identity contract mismatch')
        key = source['segment'], source['kind']
        path = objects / source['sha256']
        if key in seen or key not in expected:
            raise ValueError('duplicate or unrecorded source segment')
        seen.add(key)
        if path.stat().st_size != source['size'] or digest(path) != source['sha256']:
            raise ValueError('source hash/size mismatch')
        rows = list(parquet_rows(path))
        actual = [(r[1], json.loads(r[3])) for r in rows if r[2] == 'BTC']
        if len(actual) != len(rows) or actual != expected[key]:
            raise ValueError('export does not reproduce receipt journal')
        events, _ = parse_messages(iter(rows), source['kind'], source['sha256'])
        events, _ = merge_events(events, source['kind'])
        streams.setdefault(source['segment'], {})[source['kind']] = events
    if seen != set(expected):
        raise ValueError('missing exported channel/segment')
    return streams, inventory


def prepare(plan_path, output):
    plan_path, output = Path(plan_path), Path(output)
    plan = json.loads(plan_path.read_text())
    if plan.get('schema_version') != 'execution-live-role-plan-v1' or plan.get('scope') != 'development_only':
        raise ValueError('live role plan contract mismatch')
    roles = plan['session_roles']
    dates = sorted(roles)
    ranks = [PARTITIONS.index(roles[d]) for d in dates]
    if ranks != sorted(ranks) or any(datetime.strptime(d, '%Y-%m-%d').date().isoformat() != d for d in dates):
        raise ValueError('roles must follow whole chronological UTC dates')
    if not plan['captures']:
        raise ValueError('empty capture plan')
    # All lineage is verified before opening labels, including later captures.
    identities = []
    for entry in plan['captures']:
        _, inventory = read_capture(entry)
        identities.append(inventory['journal_sha256'])
    if len(set(identities)) != len(identities):
        raise ValueError('duplicate capture journal')
    rows, coverage, sources = [], [], []
    for entry in plan['captures']:
        streams, inventory = read_capture(entry)
        sources.extend(inventory['sources'])
        for segment, channels in sorted(streams.items()):
            segment_id = f"{inventory['journal_sha256']}:{segment}"
            all_events = [e for events in channels.values() for e in events]
            segment_dates = sorted({day(e.recorded_ns) for e in all_events})
            if any(d not in roles for d in segment_dates):
                raise ValueError('captured date missing frozen role')
            for date in segment_dates:
                # UTC boundary is a fresh warm-up even within an uninterrupted connection.
                books = [e for e in channels.get('books', []) if day(e.recorded_ns) == date]
                trades = [e for e in channels.get('trades', []) if day(e.recorded_ns) == date]
                candidates, excluded = cases(books, trades) if books and trades else ([], {'missing_stream': 1})
                coverage.append({'segment_id': segment_id, 'session': date, 'role': roles[date],
                                 'books': len(books), 'trades': len(trades),
                                 'cases': len(candidates), 'exclusions': excluded})
                for row in candidates:
                    row.update(session=date, segment_id=segment_id, role=PARTITIONS.index(roles[date]))
                rows.extend(candidates)
    rows.sort(key=lambda row: row['decision_ns'])
    if len({r['decision_ns'] for r in rows}) != len(rows):
        raise ValueError('overlapping decision clocks across captures')
    counts = Counter(r['role'] for r in rows)
    blockers = [f'{name}: no eligible cases' for i, name in enumerate(PARTITIONS) if not counts[i]]
    report = {'schema_version': 'execution-live-risk-coverage-v1', 'scope': 'development_only',
              'plan_sha256': digest(plan_path), 'adapter_sha256': digest(__file__),
              'coverage': coverage, 'cases': len(rows), 'blockers': blockers,
              'cache_created': not blockers, 'eligible_for_performance_claim': False}
    # Write only after validation; existing directories must never be overwritten.
    if not blockers:
        arrays = {'features': np.asarray([r['sequence'] for r in rows], dtype=np.float32),
                  'targets': np.asarray([[[[-a['terminal_bps'], a['buy_adverse_bps']],
                                          [a['terminal_bps'], a['sell_adverse_bps']]]
                                         for a in r['audit']] for r in rows], dtype=np.float32),
                  'roles': np.asarray([r['role'] for r in rows], dtype=np.int64),
                  'clocks': np.asarray([[r['decision_ns'], r['label_available_ns']] for r in rows], dtype=np.int64)}
        manifest = {'schema_version': SCHEMA, 'scope': 'development_only',
                    'target_id': 'signed-terminal-and-observed-adverse-movement-bps-v1',
                    'availability_basis': 'local_receipt', 'horizons': list(HORIZONS),
                    'sides': ['buy', 'sell'], 'tasks': ['terminal_loss', 'observed_adverse'],
                    'feature_order': list(FEATURES), 'partitions': list(PARTITIONS),
                    'sessions': [r['session'] for r in rows],
                    'segments': [r['segment_id'] for r in rows],
                    'source_manifest_sha256': digest(plan_path), 'sources': sources,
                    'capture_journal_sha256': identities,
                    'adapter_sha256': digest(__file__), 'eligible_for_performance_claim': False,
                    'limitations': ['local receive clocks do not prove venue or exchange latency',
                                    'trade completeness and clock synchronization unverified',
                                    'observed snapshots only; no fills, intervention or realized profit',
                                    'development data; session counts are not proof of statistical sufficiency']}
        validate(manifest, arrays)
    output.mkdir(parents=True, exist_ok=False)
    (output / 'coverage.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    if not blockers:
        for name in FILES:
            np.save(output / (name + '.npy'), arrays[name], allow_pickle=False)
        manifest['array_sha256'] = {name + '.npy': digest(output / (name + '.npy')) for name in FILES}
        (output / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.plan, args.output), indent=2))
