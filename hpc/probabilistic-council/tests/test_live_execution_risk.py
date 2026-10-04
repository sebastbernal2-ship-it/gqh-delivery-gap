import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from record_execution_tape import Journal
from export_execution_capture import export
from prepare_live_execution_risk import prepare, day, read_capture
from execution_risk_dataset import load_risk_cache
from multisession_panel import PARTITIONS
from synchronized_tape import NS, digest
from test_synchronized_tape import START


def capture(root, date_offset=0, lengths=(280,)):
    start = START + date_offset * 86400 * NS
    journal = Journal(root / 'capture', 10_000_000)
    offset = 0
    for length in lengths:
        journal.boundary('connection_open', start + offset * NS, (offset + 1) * NS)
        for i in range(offset, offset + length):
            event = start + i * NS
            book = {'channel': 'l2Book', 'data': {'coin': 'BTC', 'time': event // 1_000_000,
                    'levels': [[{'px': str(99 - j), 'sz': '2', 'n': 1} for j in range(5)],
                               [{'px': str(101 + j), 'sz': '2', 'n': 1} for j in range(5)]]}}
            trade = {'channel': 'trades', 'data': [{'coin': 'BTC', 'time': event // 1_000_000,
                     'tid': i, 'side': 'B', 'px': '100', 'sz': '1'}]}
            journal.append(json.dumps(book), event + 1, (i + 1) * NS + 1)
            journal.append(json.dumps(trade), event + 2, (i + 1) * NS + 2)
        offset += length
    journal.finish('test', offset, [])
    export(root / 'capture', root / 'objects')
    return {'capture': str(root / 'capture'), 'objects': str(root / 'objects'),
            'capture_receipt_sha256': digest(root / 'capture/capture.json'),
            'inventory_sha256': digest(root / 'objects/inventory.json')}


def plan(root, entries, roles):
    path = root / 'plan.json'
    path.write_text(json.dumps({'schema_version': 'execution-live-role-plan-v1',
                              'scope': 'development_only', 'captures': entries,
                              'session_roles': roles}))
    return path


class LiveRiskTests(unittest.TestCase):
    def test_reconnects_cannot_supply_each_others_history_or_future(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry = capture(root / 'source', lengths=(80, 80, 80))
            path = plan(root, [entry], {day(START): 'training'})
            report = prepare(path, root / 'out')
            self.assertEqual(report['cases'], 0)
            self.assertEqual(len(report['coverage']), 3)
            self.assertFalse(report['cache_created'])
            self.assertFalse((root / 'out/features.npy').exists())

    def test_five_dates_produce_hash_verified_development_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entries = [capture(root / str(i), i) for i in range(5)]
            roles = {day(START + i * 86400 * NS): role for i, role in enumerate(PARTITIONS)}
            report = prepare(plan(root, entries, roles), root / 'out')
            self.assertTrue(report['cache_created'])
            spec, arrays = load_risk_cache(root / 'out')
            self.assertEqual(spec['availability_basis'], 'local_receipt')
            self.assertEqual(set(arrays['roles']), set(range(5)))
            self.assertFalse(spec['eligible_for_performance_claim'])
            self.assertNotIn(str(root), (root / 'out/manifest.json').read_text())
            self.assertTrue((arrays['targets'][..., 1] == 0).all())

    def test_source_tampering_fails_before_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry = capture(root / 'source')
            inventory = json.loads((Path(entry['objects']) / 'inventory.json').read_text())
            (Path(entry['objects']) / inventory['sources'][0]['sha256']).write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError, 'hash/size'):
                prepare(plan(root, [entry], {day(START): 'training'}), root / 'out')
            self.assertFalse((root / 'out').exists())

    def test_export_projection_must_match_pinned_journal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry = capture(root / 'source')
            from synchronized_tape import parquet_rows
            def altered(path):
                for index, recorded, coin, payload in parquet_rows(path):
                    yield index, recorded + 100, coin, payload
            with patch('prepare_live_execution_risk.parquet_rows', side_effect=altered):
                with self.assertRaisesRegex(ValueError, 'reproduce receipt'):
                    read_capture(entry)

    def test_rehashed_clock_discontinuity_is_not_accepted_as_local_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry = capture(root / 'source')
            directory = Path(entry['capture'])
            journal = directory / 'messages.jsonl'
            rows = [json.loads(line) for line in journal.read_text().splitlines()]
            rows[1]['receipt_monotonic_ns'] += 200_000_000
            journal.write_text(''.join(json.dumps(row) + '\n' for row in rows))
            receipt = json.loads((directory / 'capture.json').read_text())
            receipt['messages_sha256'] = digest(journal)
            (directory / 'capture.json').write_text(json.dumps(receipt))
            entry['capture_receipt_sha256'] = digest(directory / 'capture.json')
            inventory_path = Path(entry['objects']) / 'inventory.json'
            inventory = json.loads(inventory_path.read_text())
            inventory['capture_receipt_sha256'] = entry['capture_receipt_sha256']
            inventory['journal_sha256'] = digest(journal)
            inventory_path.write_text(json.dumps(inventory))
            entry['inventory_sha256'] = digest(inventory_path)
            with self.assertRaisesRegex(ValueError, 'clock discontinuity'):
                read_capture(entry)

    def test_duplicate_capture_and_reversed_date_roles_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry = capture(root / 'source')
            with self.assertRaisesRegex(ValueError, 'duplicate capture'):
                prepare(plan(root, [entry, entry], {day(START): 'training'}), root / 'dup')
            roles = {day(START): 'evaluation', day(START + 86400 * NS): 'training'}
            with self.assertRaisesRegex(ValueError, 'chronological'):
                prepare(plan(root, [entry], roles), root / 'bad')


if __name__ == '__main__':
    unittest.main()
