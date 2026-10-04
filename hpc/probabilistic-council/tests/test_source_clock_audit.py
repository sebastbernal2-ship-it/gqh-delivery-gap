import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from source_clock_audit import audit, inspect_rows
from synchronized_tape import NS

START = 1765370000*NS


def row(event, recorded, coin='BTC'):
    return (0, recorded, coin, json.dumps({'channel':'trades', 'data':[
        {'coin':coin, 'time':event//1_000_000, 'px':'PRIVATE_PRICE',
         'users':['PRIVATE_USER'], 'hash':'PRIVATE_HASH'}]}))


class SourceClockAuditTests(unittest.TestCase):
    def test_negative_lags_and_order_reversals_are_preserved(self):
        receipt = inspect_rows([
            row(START+NS,START), row(START,START-NS),
            row(START,START+4*NS), row(START,START,'ETH')], 'trades')
        self.assertEqual(receipt['counts']['event_later_than_recorded'],2)
        self.assertEqual(receipt['counts']['recorded_row_reversals'],1)
        self.assertEqual(receipt['counts']['event_order_reversals'],1)
        self.assertEqual(receipt['counts']['lag_over_2s'],1)
        self.assertEqual(receipt['recorded_minus_event_ns']['min'],-NS)
        self.assertEqual(receipt['instrument_row_counts'],{'BTC':3,'ETH':1})
        self.assertNotIn('PRIVATE',json.dumps(receipt))

    def test_evaluation_role_rejected_before_any_source_is_opened(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            entries=[{'sha256':c*64,'size':1,'dataset':'a/b','revision':'pinned',
                      'path':kind+'.parquet','session':'day','pair_id':'pair','kind':kind}
                     for c,kind in [('a','books'),('b','trades')]]
            parent={'scope':'development_only','files':entries,'session_roles':{'day':'evaluation'}}
            sample={'scope':'development_only','files':entries}
            (root/'parent.json').write_text(json.dumps(parent))
            (root/'sample.json').write_text(json.dumps(sample))
            with patch('source_clock_audit.parquet_rows') as read:
                with self.assertRaisesRegex(ValueError,'training-role'):
                    audit(root/'parent.json',root/'sample.json',root/'missing')
                read.assert_not_called()

    def test_empty_stream_does_not_invent_clock_ranges(self):
        receipt=inspect_rows([row(START,START,'ETH')],'trades')
        self.assertNotIn('first_event_ns',receipt)
        self.assertEqual(receipt['counts']['source_rows'],1)


if __name__=='__main__':unittest.main()
