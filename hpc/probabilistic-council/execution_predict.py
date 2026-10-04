"""Load once, infer all side/horizon/task distributions from one structured sequence."""
import argparse
import json
from pathlib import Path
import numpy as np
import torch
from council.calibration import TemperatureCalibrator
from execution_model import ExecutionJev
from execution_train import apply,probabilities
from synchronized_tape import digest


class ExecutionPredictor:
    def __init__(self,checkpoint,expected_sha256,device='cpu'):
        if digest(checkpoint)!=expected_sha256:raise ValueError('checkpoint hash mismatch')
        payload=torch.load(checkpoint,map_location='cpu',weights_only=True)
        schemas=('execution-jev-v1','execution-jev-view-ablation-v1')
        if payload['schema_version'] not in schemas or payload['config']!={'features':24,'steps':16,'width':32}:raise ValueError('checkpoint schema mismatch')
        self.model=ExecutionJev(**payload['config']).to(device)
        self.model.load_state_dict(payload['state']);self.model.eval();self.device=device
        self.mean=np.asarray(payload['mean']);self.scale=np.asarray(payload['scale'])
        if self.mean.shape!=(24,) or self.scale.shape!=(24,) or not np.isfinite(self.mean).all() or not np.isfinite(self.scale).all() or (self.scale<=0).any():raise ValueError('invalid normalizer')
        self.feature_mask=np.asarray(payload.get('feature_mask',np.ones(24,dtype=bool)),dtype=bool)
        if self.feature_mask.shape!=(24,) or not self.feature_mask.any():raise ValueError('invalid feature-view mask')
        self.cal=[TemperatureCalibrator(**c) for c in payload['calibration']]
        if len(self.cal)!=12:raise ValueError('twelve query calibrators required')
        self.view=payload.get('view','all_features')

    def predict(self,sequence):
        x=np.asarray(sequence,dtype=np.float32)
        if x.shape!=(16,24) or not np.isfinite(x).all():raise ValueError('finite 16x24 sequence required')
        standardized=(x-self.mean)/self.scale
        standardized[:,~self.feature_mask]=0.
        x=torch.tensor(standardized[None],dtype=torch.float32,device=self.device)
        p=apply(probabilities(self.model,x),self.cal)[0]
        return {'scope':'development_forecast','view':self.view,'horizons_s':[5,15,60],'sides':['buy','sell'],'tasks':['terminal','adverse'],
                'terminal_edges_bps':[-2,-.5,.5,2],'adverse_edges_bps':[.5,1,2,5],
                'probabilities':p.tolist(),'adverse_at_least_threshold':np.cumsum(p[:,:,1,::-1],axis=-1)[:,:,::-1][:,:,1:].tolist(),
                'limitations':'observed snapshot marginals; no fill, impact, joint-path or execution guarantee'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--sha256',required=True);p.add_argument('--sequence',type=Path,required=True)
    a=p.parse_args();print(json.dumps(ExecutionPredictor(a.checkpoint,a.sha256).predict(json.loads(a.sequence.read_text())),indent=2))
