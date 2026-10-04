"""The public-book adapter must retain causal features and reject broken source contracts."""
import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from book_panel import build, normalize, SOURCE, NS, iso_ns
from information_views import load_panel, stamp


def fixture():
    start=1765083600*NS
    rows=[]
    for i in range(1200):
        b={'coin':'BTC','timestamp':start+i*NS}
        for j in range(1,6):
            b.update({f'bid_px_{j}':100-j*0.001,f'ask_px_{j}':100+j*0.001,
                      f'bid_sz_{j}':j+1, f'ask_sz_{j}':j+2})
        rows.append(dict(ROW_INDEX=i,ROW_SHA256='a'*64,SOURCE_SHA256=SOURCE,QUALITY_FLAGS='[]',BOOK=json.dumps(b)))
    return rows


def write(path, rows):
    with path.open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader();w.writerows(rows)


class BookPanelTests(unittest.TestCase):
    def test_clock_rounds_up_and_never_via_float(self):
        self.assertEqual(iso_ns(1765083600*NS+1),'2025-12-07T05:00:00.000001+00:00')

    def test_wrong_source_and_float_clock_fail(self):
        rows=fixture()[:1]
        rows[0]['SOURCE_SHA256']='wrong'
        with self.assertRaisesRegex(ValueError,'source'): normalize(rows)
        rows[0]['SOURCE_SHA256']=SOURCE
        b=json.loads(rows[0]['BOOK']);b['timestamp']=float(b['timestamp']);rows[0]['BOOK']=json.dumps(b)
        with self.assertRaisesRegex(ValueError,'integer'): normalize(rows)

    def test_invalid_book_excluded_and_duplicates_rejected(self):
        rows=fixture()[:3]
        b=json.loads(rows[0]['BOOK']);b['bid_px_1']=101;rows[0]['BOOK']=json.dumps(b)
        books,exclusions=normalize(rows)
        self.assertEqual(len(books),2);self.assertEqual(exclusions['invalid_order'],1)
        with self.assertRaisesRegex(ValueError,'duplicate'):normalize(rows[1:]+rows[1:])

    def test_future_mid_changes_label_not_current_features(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t); rows=fixture();write(root/'input.csv',rows)
            result=build(root/'input.csv',root/'panel')
            _,parts,_=load_panel(root/'panel/panel.jsonl',root/'panel/manifest.json')
            before=parts['training'][0]
            self.assertEqual(before.label,1)
            b=json.loads(rows[36]['BOOK'])
            for j in range(1,6):b[f'bid_px_{j}']+=1;b[f'ask_px_{j}']+=1
            rows[36]['BOOK']=json.dumps(b);write(root/'changed.csv',rows)
            build(root/'changed.csv',root/'changed')
            _,after,_=load_panel(root/'changed/panel.jsonl',root/'changed/manifest.json')
            self.assertEqual(before.features,after['training'][0].features)
            self.assertEqual(after['training'][0].label,2)
            self.assertGreater(result['exclusions']['partition_boundary'],0)

    def test_source_gap_is_not_forward_filled(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);rows=fixture();rows=rows[:300]+rows[310:];write(root/'input.csv',rows)
            result=build(root/'input.csv',root/'panel')
            self.assertGreater(result['exclusions']['source_gap'],0)
            self.assertEqual(result['availability_basis'],'retrospective_assumption')


if __name__=='__main__': unittest.main()
