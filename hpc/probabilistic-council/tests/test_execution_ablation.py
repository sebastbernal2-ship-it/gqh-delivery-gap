import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
import torch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from execution_model import ExecutionJev
from execution_predict import ExecutionPredictor
from multisession_panel import PARTITIONS,validate_plan
from synchronized_tape import digest


class ExecutionAblationTests(unittest.TestCase):
    def test_pinned_sample_has_balanced_ordered_roles_and_matched_clocks(self):
        plan=json.loads((ROOT/'synchronized_ablation_plan.json').read_text())
        sessions=validate_plan(plan)
        self.assertEqual(len(sessions),30)
        self.assertEqual({r:list(plan['session_roles'].values()).count(r) for r in PARTITIONS},{r:6 for r in PARTITIONS})
        bad=json.loads(json.dumps(plan))
        first=bad['files'][1]
        first['filename_timestamp_s']+=3
        with self.assertRaisesRegex(ValueError,'match within two seconds'):
            validate_plan(bad)
        bad=json.loads(json.dumps(plan));bad['session_roles'][sessions[0]]='evaluation'
        with self.assertRaisesRegex(ValueError,'chronological blocks'):
            validate_plan(bad)

    def test_view_checkpoint_ignores_excluded_input_features(self):
        torch.manual_seed(17)
        model=ExecutionJev();payload={
            'schema_version':'execution-jev-view-ablation-v1',
            'config':model.config,
            'state':model.state_dict(),
            'mean':[0.]*24,
            'scale':[1.]*24,
            'feature_mask':[i==21 for i in range(24)],
            'view':'B_trades',
            'calibration':[{'temperature':1.,'sample_count':1,'log_loss_before':1.,'log_loss_after':1.} for _ in range(12)],
        }
        with tempfile.TemporaryDirectory() as temp:
            checkpoint=Path(temp)/'view.pt';torch.save(payload,checkpoint)
            predictor=ExecutionPredictor(checkpoint,digest(checkpoint))
            base=np.zeros((16,24),dtype=np.float32);hidden=base.copy();hidden[:,0]=1e6
            first=predictor.predict(base);second=predictor.predict(hidden)
        self.assertEqual(first['view'],'B_trades')
        self.assertTrue(np.allclose(first['probabilities'],second['probabilities'],atol=0,rtol=0))
        probabilities=np.asarray(first['probabilities'])
        self.assertEqual(probabilities.shape,(3,2,2,5))
        self.assertTrue(np.allclose(probabilities.sum(axis=-1),1.,atol=1e-6))


if __name__=='__main__':unittest.main()
