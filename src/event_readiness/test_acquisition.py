"""Offline acquisition gates. Synthetic inputs only; never opens a strategy holdout."""
from datetime import datetime
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from .acquisition import Retrieval, atomic_json, canonical, public_url, records_file, sha, strict_json, validate_bar
from .pull_candidates import record
from .queue_data import date_value, queue_records
from .warehouse_candidates import prepare, verify_rows


class JsonTests(unittest.TestCase):
    def test_invalid_json_values(self):
        for text in ('{"x":NaN}', '{"x":Infinity}', '{"x":1e999}', '{"x":1,"x":2}'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                strict_json(text)

    def test_public_url_removes_auth(self):
        self.assertEqual(public_url('https://api.massive.com/a?apiKey=SECRET&token=OTHER&limit=1'),
                         'https://api.massive.com/a?limit=1')
        for url in ('http://example.com/a', 'https://user:pass@example.com/a', 'https://example.com/#x'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                public_url(url)

    def test_bar_bounds_and_domain(self):
        bar = dict(o=1, h=2, l=0, c=1, v=0, t=10, n=0)
        validate_bar(bar, 10, 11)
        for bad in ({'v': -1}, {'c': float('nan')}, {'t': 11}, {'t': True}, {'h': .5}, {'n': 1.5}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_bar(bar | bad, 10, 11)


class RetrievalTests(unittest.TestCase):
    def test_cross_origin_credentials_refused_before_io(self):
        with tempfile.TemporaryDirectory() as tmp:
            client = Retrieval(Path(tmp), 'not-a-real-key', delay=0)
            for url in ('https://evil.test/page', 'https://api.massive.com.evil.test/page'):
                with self.assertRaises(ValueError):
                    client.fetch(url, massive=True)

    def test_cache_checks_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            client = Retrieval(Path(tmp), delay=0)
            url, body = 'https://example.com/source', b'{"results":[]}'
            obj = client.root / 'objects' / sha(body)
            obj.write_bytes(body)
            atomic_json(client.root / 'requests' / (sha(url.encode())+'.json'), {'url': url, 'sha256': sha(body)})
            self.assertEqual(client.fetch(url)[0], body)
            obj.write_bytes(b'corrupted')
            with self.assertRaises(ValueError):
                client.fetch(url)

    def test_pagination_cycle_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            client = Retrieval(Path(tmp), delay=0)
            url = 'https://api.massive.com/page'
            with patch.object(client, 'fetch', return_value=(canonical({'status':'OK','results':[], 'next_url':url}).encode(), {})):
                with self.assertRaises(ValueError):
                    list(client.pages(url))


class QueueTests(unittest.TestCase):
    def test_dates_do_not_guess_numeric_encoding(self):
        for raw in (2024, 17197, 45200, '2024', 'TBD', None):
            self.assertIsNone(date_value(raw, None))
        for raw in ('2024-01-02T00:00:00', '01/02/2024', datetime(2024,1,2)):
            self.assertEqual(date_value(raw, None), '2024-01-02')
        from openpyxl.utils.datetime import CALENDAR_WINDOWS_1900
        self.assertEqual(date_value(45200, CALENDAR_WINDOWS_1900, 2023), '2023-10-01')
        self.assertIsNone(date_value(45200, CALENDAR_WINDOWS_1900, 2024))

    def test_ercot_month_and_missing_date_marker(self):
        from .ercot_data import report_month, milestone
        self.assertEqual(report_month('GIS_Report_Jun2026'), '2026-06')
        self.assertEqual(report_month('GIS_Report_July_2020_Revised'), '2020-07')
        self.assertIsNone(milestone(datetime(1900,1,1),None))
        with self.assertRaises(ValueError): report_month('Unknown_2026')

    def test_ercot_preserves_negative_capacity_and_source_clock(self):
        from openpyxl import Workbook
        from .ercot_data import extract_sheet
        wb=Workbook(); s=wb.active;s.title='Project Details'
        s.append(['INR','Projected COD','Capacity (MW)','GIM Study Phase'])
        s.append(['20INR001',datetime(1900,1,1),-5,'Planned'])
        doc={'context':{'doc_id':'123'},'data':{'FriendlyName':'GIS_Report_Jan2022'},
             'reported_posted_at_utc':'2022-02-01T00:00:00+00:00'}
        receipt={'sha256':'a'*64,'url':'https://example.com/workbook','retrieved_at_utc':'2026-10-03T00:00:00+00:00'}
        rows=list(extract_sheet(s,doc,receipt,wb.epoch))
        self.assertEqual(rows[0]['normalized']['capacity_mw_raw'],-5)
        self.assertIsNone(rows[0]['normalized']['proposed_service_date'])
        self.assertIsNone(rows[0]['available_at_utc'])
        self.assertEqual(rows[0]['reported_posted_at_utc'],doc['reported_posted_at_utc'])

    def test_workbook_provenance_and_duplicates_retained(self):
        from openpyxl import Workbook
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'source.xlsx'
            wb = Workbook(); ws = wb.active; ws.title='data'
            ws.append(['q_id','entity','q_status','q_date','prop_date','state','type_clean'])
            ws.append(['A','ERCOT','active',datetime(2020,1,1),'2023','TX','Solar'])
            ws.append(['A','ERCOT','active',None,45200,'TX','Solar'])
            wb.save(path); wb.close()
            receipt = {'sha256':sha(path.read_bytes()),'url':'https://example.com/queue', 'retrieved_at_utc':'2026-10-03T00:00:00+00:00'}
            rows = list(queue_records(path, 2021, receipt))
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]['normalized']['submission_date'], '2020-01-01')
            self.assertIsNone(rows[0]['available_at_utc'])
            self.assertIsNone(rows[1]['normalized']['proposed_service_date'])
            self.assertEqual(rows[0]['context']['sheet_row'],2)
            path.write_bytes(b'broken')
            with self.assertRaises(ValueError):
                list(queue_records(path, 2021, receipt))


def fixture(root):
    (root/'objects').mkdir(); (root/'requests').mkdir()
    body = b'{"x":1}'
    receipt = {'sha256':sha(body),'url':'https://example.com/one','size_bytes':len(body),
               'http_status':200,'retrieved_at_utc':'2026-10-03T00:00:00+00:00'}
    (root/'objects'/receipt['sha256']).write_bytes(body)
    atomic_json(root/'requests'/'one.json',receipt)
    row = record('synthetic',{},receipt,{'x':1})
    manifest = records_file(root/'records.jsonl',[row])
    atomic_json(root/'complete.json',manifest)
    return row, receipt


class WarehouseTests(unittest.TestCase):
    def test_deterministic_bundle_contains_original_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); row, receipt = fixture(root)
            first, zip_path, transport = prepare(root)
            second, _, _ = prepare(root)
            self.assertEqual(first,second)
            with zipfile.ZipFile(zip_path) as archive:
                self.assertEqual(archive.read('objects/'+receipt['sha256']),b'{"x":1}')
            import gzip
            envelope = strict_json(gzip.decompress(transport.read_bytes()))
            self.assertEqual(envelope['row_sha256'],sha(canonical(row).encode()))

    def test_missing_provenance_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); row,_=fixture(root)
            row['source_sha256']='a'*64
            atomic_json(root/'complete.json',records_file(root/'records.jsonl',[row]))
            with self.assertRaises(ValueError): prepare(root)

    def test_corrupt_objects_or_rows_rejected(self):
        for kind in ('objects','records'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp); _,receipt=fixture(root)
                p=root/'objects'/receipt['sha256'] if kind=='objects' else root/'records.jsonl'
                p.write_bytes(b'changed')
                with self.assertRaises(ValueError): prepare(root)

    def test_warehouse_missing_duplicate_or_corrupt_rows_rejected(self):
        from unittest.mock import Mock
        payload=canonical({'a':1})
        good=(0,sha(payload.encode()),payload)
        expected={'rows':1,'records_sha256':sha((payload+'\n').encode())}
        cursor=Mock(); cursor.fetchmany.side_effect=[[good],[]]
        verify_rows(cursor,'ACQUISITION_COPY','unused',expected)
        for rows in ([],[good,good],[(1,good[1],payload)],[(0,'a'*64,payload)]):
            cursor=Mock();cursor.fetchmany.side_effect=[rows,[]]
            with self.subTest(rows=rows),self.assertRaises(ValueError):
                verify_rows(cursor,'ACQUISITION_COPY','unused',expected)


class MirrorTests(unittest.TestCase):
    def test_redirect_hosts_and_protocol(self):
        from .mirror_candidates import permitted_host
        self.assertTrue(permitted_host('https://huggingface.co/datasets/example/data'))
        self.assertTrue(permitted_host('https://cas-bridge.xethub.hf.co/file'))
        for url in ('http://huggingface.co/data','https://huggingface.co.evil.test/data',
                    'https://user:pass@huggingface.co/data','https://localhost/data'):
            self.assertFalse(permitted_host(url))

    def test_unpinned_or_traversal_plan_refused(self):
        from .mirror_candidates import download
        with tempfile.TemporaryDirectory() as tmp:
            client=Retrieval(Path(tmp))
            entry={'dataset':'example/data','revision':'a'*40,'path':'data/a.parquet','size':10,'sha256':'b'*64}
            for change in ({'revision':'main'},{'path':'../private'},{'size':600_000_000},{'sha256':'not-a-hash'}):
                with self.subTest(change=change),self.assertRaises(ValueError):
                    download(client,entry|change)

    def test_nanosecond_timestamps_preserved(self):
        import pyarrow as pa
        import pyarrow.parquet as pq
        from .mirror_data import batches
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'test.parquet'; value=1753808400042190641
            pq.write_table(pa.table({'time':pa.array([value],type=pa.timestamp('ns')),'coin':['BTC']}),p)
            self.assertEqual(list(batches(p))[0]['time'],value)


if __name__=='__main__':
    unittest.main()
