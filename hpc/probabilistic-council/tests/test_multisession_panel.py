"""Cross-file identity, chronological roles, future labels and missing-source regressions."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from multisession_panel import merge_events,session_cases,build,validate_plan,PARTITIONS
from synchronized_tape import Trade,NS,digest,parse_messages
from test_synchronized_tape import book_message,trade_message,START,SHA


def session(start=START,changed=False):
    books,_=parse_messages([book_message(start+i*NS,price=101 if changed and i==35 else 100) for i in range(100)],'books',SHA)
    trades,_=parse_messages([trade_message(start+i*NS,tid=i) for i in range(100)],'trades',SHA)
    return books,trades


def source_fixture(root):
    entries,rows=[],{}
    for day in range(8,14):
        start=START+(day-8)*86400*NS
        for kind in ('books','trades'):
            for file_index in range(2):
                content=f'{day}:{kind}:{file_index}'.encode();p=root/'temp';p.write_bytes(content);sha=digest(p);p.rename(root/sha)
                entries.append(dict(session=f'2025-12-{day:02}',kind=kind,size=len(content),sha256=sha))
                rows[sha]=[book_message(start+i*NS) if kind=='books' else trade_message(start+i*NS,tid=i) for i in range(100)]
    plan=root/'plan.json';plan.write_text(json.dumps(dict(scope='development_only',selection_rule='synthetic fixture',files=entries)))
    return plan,rows


class MultisessionTests(unittest.TestCase):
    def test_cross_file_duplicates_keep_first_receipt_and_conflicts_fail(self):
        a=Trade(START,START+NS,5,'B',100,2,'first');b=Trade(START,START+2*NS,5,'B',100,2,'second')
        merged,n=merge_events([b,a],'trades');self.assertEqual(merged,[a]);self.assertEqual(n,1)
        c=Trade(START,START+2*NS,5,'A',100,2,'bad')
        with self.assertRaisesRegex(ValueError,'conflicting'):merge_events([a,c],'trades')
        # tid alone is not globally unique.
        c=Trade(START+NS,START+2*NS,5,'A',100,2,'new')
        self.assertEqual(len(merge_events([a,c],'trades')[0]),2)

    def test_future_mid_changes_label_not_features(self):
        books,trades=session();before,_,_,_=session_cases(books,trades,'test')
        books,trades=session(changed=True);after,_,_,_=session_cases(books,trades,'test')
        self.assertEqual(before[0]['features'],after[0]['features'])
        self.assertEqual(before[0]['label'],1);self.assertEqual(after[0]['label'],2)

    def test_no_training_row_crosses_a_recording_gap(self):
        books,trades=session();books=books[:45]+books[55:]
        rows,labels,excluded,_=session_cases(books,trades,'test')
        self.assertTrue(excluded)
        self.assertTrue(rows)
        for label in labels:
            decision=label['decision_ns']
            self.assertFalse(decision-30*NS < START+55*NS and decision+5*NS > START+44*NS)

    def test_complete_build_separates_sessions_and_validates_existing_contract(self):
        from information_views import load_panel
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);plan,rows=source_fixture(root)
            with patch('multisession_panel.parquet_rows',side_effect=lambda p:rows[p.name]):
                spec=build(plan,root,root/'panel')
            _,parts,_=load_panel(root/'panel/panel.jsonl',root/'panel/manifest.json')
            self.assertEqual(len({r.episode_id for r in parts['training']}),2)
            for role in PARTITIONS[1:]:self.assertEqual(len({r.episode_id for r in parts[role]}),1)
            self.assertEqual(spec['availability_basis'],'retrospective_assumption')
            self.assertTrue(all(c['cross_file_retransmissions']['books']==100 for c in spec['session_coverage'].values()))
            self.assertEqual(spec['panel_sha256'],digest(root/'panel/panel.jsonl'))

    def test_missing_file_and_cross_session_identity_fail_without_output(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);plan,rows=source_fixture(root);entries=json.loads(plan.read_text())['files']
            saved=(root/entries[0]['sha256']).read_bytes();(root/entries[0]['sha256']).unlink()
            with self.assertRaises(FileNotFoundError):build(plan,root,root/'missing')
            self.assertFalse((root/'missing').exists());(root/entries[0]['sha256']).write_bytes(saved)
            for e in entries[4:8]:rows[e['sha256']]=rows[entries[0 if e['kind']=='books' else 2]['sha256']]
            with patch('multisession_panel.parquet_rows',side_effect=lambda p:rows[p.name]):
                with self.assertRaisesRegex(ValueError,'overlaps'):build(plan,root,root/'overlap')
            self.assertFalse((root/'overlap').exists())

    def test_invalid_plan_roles_and_budget_fail(self):
        with tempfile.TemporaryDirectory() as t:
            plan,_=source_fixture(Path(t));spec=json.loads(plan.read_text());spec['files'][0]['size']=750_000_001
            with self.assertRaisesRegex(ValueError,'cap'):validate_plan(spec)
            spec=json.loads(plan.read_text());spec['files'].pop()
            with self.assertRaisesRegex(ValueError,'two book'):validate_plan(spec)


if __name__=='__main__':unittest.main()
