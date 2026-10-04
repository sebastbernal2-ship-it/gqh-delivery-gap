import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from execution_dataset import cases,prepare,load_cache
from execution_model import ExecutionJev
from execution_train import run
from execution_predict import ExecutionPredictor
from synchronized_tape import NS,parse_messages,digest
from test_synchronized_tape import book_message,trade_message,START,SHA


def fixture(start=START,change=False):
    books,_=parse_messages([book_message(start+i*NS,price=101 if change and i==40 else 100) for i in range(280)],'books',SHA)
    trades,_=parse_messages([trade_message(start+i*NS,tid=i) for i in range(280)],'trades',SHA)
    return books,trades


def cache(root):
    entries=[];sources={}
    for day in range(6):
        for kind in ('books','trades'):
            for file in range(2):
                p=root/'tmp';p.write_text(f'{day}-{kind}-{file}');sha=digest(p);p.rename(root/sha)
                entries.append(dict(session=f'2025-12-{8+day:02}',kind=kind,size=(root/sha).stat().st_size,sha256=sha))
                t=START+day*86400*NS
                sources[sha]=[book_message(t+i*NS) if kind=='books' else trade_message(t+i*NS,tid=i) for i in range(280)]
    plan=root/'plan';plan.write_text(json.dumps(dict(scope='development_only',selection_rule='synthetic',files=entries)))
    with patch('execution_dataset.parquet_rows',side_effect=lambda p:sources[p.name]):prepare(plan,root,root/'cache')
    return root/'cache'


class ExecutionTests(unittest.TestCase):
    def test_future_path_changes_excursion_not_inputs_and_sides_share_case(self):
        before,_=cases(*fixture());after,_=cases(*fixture(change=True))
        self.assertEqual(before[0]['sequence'],after[0]['sequence'])
        self.assertEqual(before[0]['targets'][0][1][1],0)
        self.assertEqual(after[0]['targets'][0][1][1],4)
        self.assertEqual(after[0]['targets'][0][0][1],0)
        self.assertEqual(np.asarray(after[0]['targets']).shape,(3,2,2))

    def test_gap_prevents_labeling_unobserved_path(self):
        b,t=fixture();b=b[:50]+b[55:];rows,excluded=cases(b,t)
        self.assertTrue(excluded)
        self.assertTrue(all(not (r['decision_ns']<START+55*NS and r['label_available_ns']>START+49*NS) for r in rows))

    def test_cache_hash_schema_roles_and_numeric_mmap(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);p=cache(root);s,a=load_cache(p)
            self.assertIsInstance(a['features'],np.memmap)
            self.assertEqual(a['features'].shape[1:],(16,24))
            with (p/'features.npy').open('ab') as f:f.write(b'tampered')
            with self.assertRaisesRegex(ValueError,'hash'):load_cache(p)

    def test_shared_queries_and_masked_pretraining_gradients(self):
        torch.manual_seed(3);model=ExecutionJev();x=torch.randn(2,16,24)
        p=model(x).softmax(-1);self.assertEqual(tuple(p.shape),(2,3,2,2,5));self.assertTrue(torch.allclose(p.sum(-1),torch.ones(2,3,2,2)))
        mask=torch.zeros(2,16,dtype=torch.bool);mask[:,0]=True
        model.masked_loss(x,mask).backward();self.assertGreater(float(model.project.weight.grad.abs().sum()),0)
        self.assertGreater(float(model.mask_token.grad.abs().sum()),0)
        with self.assertRaises(ValueError):model(torch.randn(2,15,24))

    def test_eval_labels_do_not_change_training_calibration_or_selection(self):
        torch.set_num_threads(1)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);p=cache(root);before=run(p,root/'run',epochs=1,pretraining=1)
            _,arrays=load_cache(p)
            first=np.flatnonzero(arrays['roles']==4)[0]
            checkpoint=root/'run/scratch.pt'
            predictor=ExecutionPredictor(checkpoint,digest(checkpoint))
            prediction=predictor.predict(arrays['features'][first])
            expected=np.load(root/'run/scratch_evaluation.npy')[0]
            self.assertTrue(np.allclose(prediction['probabilities'],expected,atol=1e-6))
            tails=np.asarray(prediction['adverse_at_least_threshold'])
            self.assertTrue((np.diff(tails,axis=-1)<=0).all())
            with self.assertRaisesRegex(ValueError,'hash'):ExecutionPredictor(checkpoint,'wrong')
            with self.assertRaises(ValueError):predictor.predict(np.full((16,24),np.nan))
            y=np.load(p/'targets.npy');r=np.load(p/'roles.npy');y[r==4]=(y[r==4]+1)%5;np.save(p/'targets.npy',y,allow_pickle=False)
            s=json.loads((p/'manifest.json').read_text());s['array_sha256']['targets.npy']=digest(p/'targets.npy');(p/'manifest.json').write_text(json.dumps(s))
            after=run(p,root/'changed',epochs=1,pretraining=1)
            for key in ('normalizer','losses','calibration','gate_metrics','gate_selected'):self.assertEqual(before[key],after[key])
            for name in ('scratch','masked_pretrained'):
                a=torch.load(root/'run'/f'{name}.pt',weights_only=False);b=torch.load(root/'changed'/f'{name}.pt',weights_only=False)
                self.assertTrue(all(torch.equal(v,b['state'][k]) for k,v in a['state'].items()))
                m=ExecutionJev(**a['config']);m.load_state_dict(a['state']);m.eval()
                x=torch.randn(2,16,24)
                self.assertTrue(torch.isfinite(m(x)).all())
            self.assertNotEqual(before['evaluation_metrics'],after['evaluation_metrics'])

    def test_cluster_spool_runs_only_cache_validation_and_jev_training(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);dataset=root/'cache';dataset.mkdir();(dataset/'manifest.json').write_text('{}')
            fake=root/'python';fake.write_text('#!/bin/bash\nprintf "%s\\n" "$*" >> "$GQH_TEST_LOG"\n');fake.chmod(0o755)
            component=Path(__file__).resolve().parents[1];spool=root/'spool';spool.write_bytes((component/'run-execution.slurm').read_bytes())
            env={**os.environ,'GQH_REPO_ROOT':str(component.parents[1]),'GQH_JEV_DATASET':str(dataset),'GQH_TAPE_RUN_DIR':str(root/'new'), 'GQH_PYTHON':str(fake),'GQH_TEST_LOG':str(root/'log')}
            result=subprocess.run(['bash',str(spool)],cwd=root,env=env,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr);log=(root/'log').read_text()
            self.assertIn('execution_train.py',log);self.assertNotIn('multisession_panel.py',log);self.assertNotIn('information_views.py',log)
            env['GQH_JEV_DATASET']='relative';(root/'log').unlink()
            self.assertNotEqual(subprocess.run(['bash',str(spool)],env=env,capture_output=True).returncode,0)
            self.assertFalse((root/'log').exists())

if __name__=='__main__':unittest.main()
