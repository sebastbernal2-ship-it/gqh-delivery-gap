"""OFF-CLUSTER: fixed regularized latest-state baseline; never score evaluation here."""
from dataclasses import asdict
import argparse
import json
from pathlib import Path

import numpy as np
from council.calibration import fit_temperature
from execution_dataset import load_cache
from execution_train import apply
from synchronized_tape import digest


def softmax(logits):
    e=np.exp(logits-logits.max(axis=-1,keepdims=True))
    return e/e.sum(axis=-1,keepdims=True)


def fit_reference(features,targets,roles):
    # One fixed baseline, all 24 latest-state inputs, L2=1, 1000 full-batch steps.
    # Each of the 12 marginals is fitted separately; intercept is not penalized.
    train=roles==0
    x=np.asarray(features[:,-1,:],dtype=np.float64)
    mean=x[train].mean(axis=0)
    scale=np.maximum(x[train].std(axis=0),1e-6)
    x=(x-mean)/scale
    y=np.asarray(targets[train]).reshape(-1,12)
    onehot=np.eye(5)[y]
    weights=np.zeros((12,24,5),dtype=np.float64)
    counts=np.stack([np.bincount(y[:,q],minlength=5)+1 for q in range(12)])
    intercept=np.log(counts/counts.sum(axis=1,keepdims=True))
    for _ in range(1000):
        p=softmax(np.einsum('nf,qfc->nqc',x[train],weights)+intercept)
        delta=(p-onehot)/len(y)
        gradient=np.einsum('nf,nqc->qfc',x[train],delta)+weights
        weights-=.05*gradient
        intercept-=.05*delta.sum(axis=0)
        if not np.isfinite(weights).all():
            raise ValueError('nonfinite linear baseline fit')
    raw=softmax(np.einsum('nf,qfc->nqc',x,weights)+intercept).reshape(-1,3,2,2,5)
    calibration=[]
    mask=roles==1
    labels=np.asarray(targets[mask]).reshape(-1,12)
    p=raw[mask].reshape(-1,12,5)
    for q in range(12):
        calibration.append(fit_temperature(p[:,q].tolist(),labels[:,q].tolist()))
    probability=apply(raw,calibration)
    return probability,{'mean':mean.tolist(),'scale':scale.tolist(),
        'weights':weights.tolist(),'intercept':intercept.tolist(),
        'calibration':[asdict(c) for c in calibration],
        'l2':1.,'steps':1000,'learning_rate':.05,'input':'latest sequence step, all 24 features'}


def prepare(dataset,output):
    spec,arrays=load_cache(dataset)
    probability,parameters=fit_reference(arrays['features'],arrays['targets'],arrays['roles'])
    root=Path(output)
    root.mkdir(parents=True,exist_ok=False)
    np.save(root/'probabilities.npy',probability,allow_pickle=False)
    (root/'parameters.json').write_text(json.dumps(parameters,sort_keys=True)+'\n')
    report={'schema_version':'execution-linear-reference-v1','scope':'development_only',
        'dataset_manifest_sha256':digest(Path(dataset)/'manifest.json'),
        'code_sha256':digest(__file__),'probabilities_sha256':digest(root/'probabilities.npy'),
        'parameters_sha256':digest(root/'parameters.json'),
        'parent_cases':spec['panel_rows'],'evaluation_scored':False,
        'fit_roles':['training','specialist_calibration'],
        'protocol':'fixed latest-state multinomial L2 reference, not an architecture-matched sequence model'}
    (root/'manifest.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    print(json.dumps(prepare(a.dataset,a.output),indent=2))
