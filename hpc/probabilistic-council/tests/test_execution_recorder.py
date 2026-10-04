import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from record_execution_tape import Journal,project
from export_execution_capture import export


def message(coin='BTC'):
    return json.dumps({'channel':'trades','data':[{'coin':coin,'time':123,'tid':1,
        'side':'B','px':'100','sz':'2','users':['PRIVATE_USER'],'hash':'PRIVATE_HASH'}]})


class RecorderTests(unittest.TestCase):
    def test_projection_removes_participants_and_refuses_wrong_instrument(self):
        self.assertNotIn('PRIVATE',json.dumps(project(message())))
        self.assertIsNone(project('{"channel":"subscriptionResponse"}'))
        with self.assertRaisesRegex(ValueError,'instrument'):project(message('ETH'))

    def test_discontinuities_and_reconnects_split_sequences(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal=Journal(Path(tmp)/'capture',10000)
            journal.boundary('connection_open',100,100)
            journal.append(message(),200,200)
            journal.append(message(),150,300)
            journal.boundary('connection_open',400,400)
            journal.append(message(),500,500)
            receipt=journal.finish('test',1,[])
            rows=[json.loads(line) for line in journal.path.read_text().splitlines()]
            self.assertEqual([r['segment'] for r in rows],[1,2,3])
            self.assertEqual([r['sequence'] for r in rows],[0,1,2])
            self.assertEqual(receipt['bytes'],journal.path.stat().st_size)
            self.assertNotIn('PRIVATE',journal.path.read_text())
            self.assertEqual(receipt['boundaries'][1]['reason'],'clock_discontinuity')

    def test_byte_limit_preserves_complete_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal=Journal(Path(tmp)/'capture',1)
            self.assertFalse(journal.append(message(),200,200))
            receipt=journal.finish('byte_limit',0,[])
            self.assertEqual(receipt['bytes'],0)
            self.assertEqual(journal.path.read_bytes(),b'')

    def test_export_keeps_reconnect_segments_separate_and_checks_hash(self):
        import pyarrow.parquet as pq
        start=1765370000*1_000_000_000
        book=json.dumps({'channel':'l2Book','data':{'coin':'BTC','time':start//1_000_000,
            'levels':[[{'px':str(99-i),'sz':'2','n':1} for i in range(5)],
                      [{'px':str(101+i),'sz':'2','n':1} for i in range(5)]]}})
        trade=json.loads(message());trade['data'][0]['time']=start//1_000_000
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            journal=Journal(root/'capture',10000)
            for i in range(2):
                journal.boundary('connection_open',start+i*1000,100+i*1000)
                journal.append(book,start+i*1000+1,101+i*1000)
                journal.append(json.dumps(trade),start+i*1000+2,102+i*1000)
            journal.finish('test',1,[])
            report=export(root/'capture',root/'objects')
            self.assertEqual(len(report['sources']),4)
            self.assertEqual({e['segment'] for e in report['sources']},{1,2})
            self.assertFalse(report['ready_for_training'])
            for entry in report['sources']:
                table=pq.read_table(root/'objects'/entry['sha256'])
                self.assertEqual(table.num_rows,1)
                self.assertEqual(table.column_names,['timestamp','coin','payload'])
            journal.path.write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError,'identity mismatch'):
                export(root/'capture',root/'bad')
            self.assertFalse((root/'bad').exists())


if __name__=='__main__':unittest.main()
