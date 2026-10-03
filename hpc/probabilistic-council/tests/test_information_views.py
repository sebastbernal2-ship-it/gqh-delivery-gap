"""Leakage boundaries, feature combinations and complete training artifact regression."""
from dataclasses import asdict
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from information_views import load_panel, seven_views, select_views, run
from specialist_lab import FEATURES, synthetic_rows, split_rows


def fixture(root):
    root = Path(root)
    rows = []
    for partition, block in split_rows(synthetic_rows(100, 7)).items():
        for r in block:
            rows.append(dict(case_id=r.case_id, episode_id=r.episode_id, instrument=r.instrument,
                             decision_at=r.decision_at.isoformat(), label_end=r.label_end.isoformat(),
                             label_available_at=r.label_available_at.isoformat(),
                             feature_available_at=[r.available_at.isoformat()] * 6, features=r.features,
                             label=r.label, partition=partition, target_id=r.target_id, source_refs=['fixture'] * 6))
    spec = dict(scope='development_only', feature_order=FEATURES, outcome_order=['down','flat','up'],
                groups={'A':[0,1], 'B':[2,3], 'C':[4,5]}, target_id=rows[0]['target_id'],
                label_rule='synthetic return bins +/-5bp at 75 seconds', availability_basis='synthetic',
                availability_note='generated test data', development_start='2020-01-01T00:00:00+00:00',
                development_end='2020-02-01T00:00:00+00:00')
    return write(root, rows, spec), rows, spec


def write(root, rows, spec):
    panel, manifest = root / 'panel.jsonl', root / 'manifest.json'
    panel.write_text(''.join(json.dumps(r) + '\n' for r in rows))
    spec['panel_sha256'] = hashlib.sha256(panel.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(spec))
    return panel, manifest


class InformationViewTests(unittest.TestCase):
    def test_views_cover_all_combinations_without_duplicate_features(self):
        views = seven_views({'A':[0,1], 'B':[2,3], 'C':[4,5]})
        self.assertEqual(set(views), {'A','B','C','AB','AC','BC','ABC'})
        self.assertEqual(views['AC'], (0,1,4,5))

    def test_valid_panel_and_hash_tamper(self):
        with tempfile.TemporaryDirectory() as t:
            (panel, manifest), _, _ = fixture(t)
            spec, parts, views = load_panel(panel, manifest)
            self.assertEqual(len(parts['training']), 50)
            panel.write_text(panel.read_text() + '\n')
            with self.assertRaisesRegex(ValueError,'hash'):
                load_panel(panel, manifest)

    def test_rejects_future_feature_mature_label_episode_and_target(self):
        mutations = [lambda r: r[0].update(feature_available_at=[r[0]['label_end']]*6),
                     lambda r: r[49].update(label_available_at=r[50]['decision_at']),
                     lambda r: r[50].update(episode_id=r[49]['episode_id']),
                     lambda r: r[0].update(target_id='OTHER'),
                     lambda r: r[0].update(label=True),
                     lambda r: r[0].update(source_refs=[])]
        for mutate in mutations:
            with self.subTest(mutate=mutate), tempfile.TemporaryDirectory() as t:
                _, rows, spec = fixture(t)
                mutate(rows)
                with self.assertRaises(ValueError):
                    load_panel(*write(Path(t),rows,spec))

    def test_rejects_closed_holdout_even_with_new_target_name(self):
        with tempfile.TemporaryDirectory() as t:
            _, rows, spec = fixture(t)
            spec.update(development_start='2022-01-01T00:00:00+00:00',development_end='2025-01-01T00:00:00+00:00')
            rows[0].update(decision_at='2023-01-01T00:00:00+00:00', label_end='2023-01-02T00:00:00+00:00',
                           label_available_at='2023-01-02T00:00:01+00:00')
            with self.assertRaisesRegex(ValueError, 'holdout'):
                load_panel(*write(Path(t),rows,spec))

    def test_rejects_duplicate_feature_groups(self):
        with tempfile.TemporaryDirectory() as t:
            _, rows, spec = fixture(t)
            spec['groups']['C']=[0,5]
            with self.assertRaisesRegex(ValueError,'exactly once'):
                load_panel(*write(Path(t),rows,spec))

    def test_selection_requires_increment_beyond_best_proper_subset(self):
        values={v:{'log_loss':1.0} for v in ('A','B','C','AB','AC','BC','ABC')}
        values['AB']['log_loss']=0.9
        values['ABC']['log_loss']=0.899
        result=select_views(values)
        self.assertEqual(result['retained'],['A','B','C','AB'])
        self.assertEqual(result['checks']['ABC']['best_subset'],'AB')

    def test_full_run_saves_all_views_and_freezes_selection_before_evaluation(self):
        with tempfile.TemporaryDirectory() as t:
            (panel,manifest), rows, spec=fixture(t)
            report=run(panel,manifest,Path(t)/'run',epochs=1,seed=7)
            self.assertEqual(len(report['models']),14)
            self.assertEqual(len(report['evaluation_metrics']),18)
            self.assertEqual(len(list((Path(t)/'run').glob('*.pt'))),14)
            # Perturb only evaluation labels; fitted models/calibrators and selection cannot change.
            for r in rows:
                if r['partition']=='evaluation': r['label']=(r['label']+1)%3
            panel,manifest=write(Path(t),rows,spec)
            second=run(panel,manifest,Path(t)/'changed',epochs=1,seed=7)
            for key in ('standardizer','calibration','pool_calibration','gate_scores','view_selection','gate_selected_model'):
                self.assertEqual(report[key],second[key])
            for name in report['models']:
                self.assertEqual((Path(t)/'run'/(name+'.pt')).read_bytes(), (Path(t)/'changed'/(name+'.pt')).read_bytes())
            with self.assertRaises(FileExistsError): run(panel,manifest,Path(t)/'run')


if __name__=='__main__': unittest.main()
