"""Jev-only model fitting on an externally prepared, validated numerical cache."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import platform
import subprocess

import numpy as np
import torch
from torch import nn
from council.calibration import fit_temperature
from execution_dataset import load_cache
from execution_model import ExecutionJev
from synchronized_tape import digest


def metrics(p,y):
    flat=p.reshape(-1,5);labels=y.reshape(-1)
    one=np.eye(5)[labels]
    return {'mean_query_log_loss':float(-np.log(np.clip(flat[np.arange(len(labels)),labels],1e-12,1)).mean()),
            'mean_query_brier':float(((flat-one)**2).sum(-1).mean())}


def fit(x,y,pretraining_x,pretraining,epochs,seed,device):
    torch.manual_seed(seed)
    model=ExecutionJev().to(device);opt=torch.optim.AdamW(model.parameters(),lr=1e-3)
    losses=[]
    if pretraining:
        for _ in range(pretraining):
            order=torch.randperm(len(pretraining_x))
            for indexes in order.split(32):
                batch=pretraining_x[indexes]
                batch=batch.to(device);mask=torch.rand(batch.shape[:2],device=device)<.2
                if not mask.any():mask[0,0]=True
                opt.zero_grad();loss=model.masked_loss(batch,mask)
                if not torch.isfinite(loss):raise ValueError('nonfinite pretraining loss')
                loss.backward();opt.step();losses.append(float(loss.detach()))
    # Reset optimizer for equal supervised schedules; pretraining gets additional disclosed compute.
    opt=torch.optim.AdamW(model.parameters(),lr=1e-3)
    torch.manual_seed(seed+1)
    supervised=[]
    for _ in range(epochs):
        for indexes in torch.randperm(len(x)).split(32):
            opt.zero_grad();loss=nn.functional.cross_entropy(model(x[indexes].to(device)).reshape(-1,5),y[indexes].to(device).reshape(-1))
            if not torch.isfinite(loss):raise ValueError('nonfinite supervised loss')
            loss.backward();opt.step();supervised.append(float(loss.detach()))
    model.eval()
    return model,{'pretraining_losses':losses,'supervised_losses':supervised}


def probabilities(model,x):
    with torch.no_grad():
        p=torch.cat([model(b.to(next(model.parameters()).device)).softmax(-1).double().cpu() for b in x.split(128)]).numpy()
    if not np.isfinite(p).all() or (p<0).any() or not np.allclose(p.sum(-1),1.,atol=1e-6):raise ValueError('invalid model probability distribution')
    return p


def calibrate(p,y):
    flat=p.reshape(len(p),12,5);labels=y.reshape(len(y),12)
    return [fit_temperature(flat[:,i].tolist(),labels[:,i].tolist()) for i in range(12)]


def apply(p,cal):
    flat=p.reshape(len(p),12,5)
    return np.asarray([[cal[q].apply(row[q].tolist()) for q in range(12)] for row in flat]).reshape(p.shape)


def run(dataset,output,epochs=3,pretraining=3,seed=20261003,device='cpu'):
    if epochs<1 or pretraining<1:raise ValueError('positive epoch budgets required')
    spec,a=load_cache(dataset);roles=a['roles'];raw=np.asarray(a['features']);labels=np.asarray(a['targets'])
    pretraining_raw=np.asarray(a['pretraining_features'])
    train=pretraining_raw.astype(np.float64)
    mean=train.mean(axis=(0,1));scale=train.std(axis=(0,1));scale=np.where(scale<1e-6,1.,scale)
    x=torch.tensor((raw-mean)/scale,dtype=torch.float32)
    pretraining_x=torch.tensor((pretraining_raw-mean)/scale,dtype=torch.float32)
    y=torch.tensor(labels,dtype=torch.long)
    if not torch.isfinite(x).all():raise ValueError('nonfinite standardized model input')
    out=Path(output);out.mkdir(parents=True,exist_ok=False)
    scores={};models={};gate={};predictions={};calibrators={}
    for name,budget in [('scratch',0),('masked_pretrained',pretraining)]:
        model,losses=fit(x[roles==0],y[roles==0],pretraining_x,budget,epochs,seed,device)
        cal=calibrate(probabilities(model,x[roles==1]),labels[roles==1]);calibrators[name]=[asdict(c) for c in cal]
        gate[name]=metrics(apply(probabilities(model,x[roles==2]),cal),labels[roles==2])
        # Both variants are reported; evaluation never determines the selected checkpoint.
        predictions[name]=apply(probabilities(model,x[roles==4]),cal)
        scores[name]=metrics(predictions[name],labels[roles==4])
        payload={'schema_version':'execution-jev-v1','config':model.config,'state':{k:v.detach().cpu().clone() for k,v in model.state_dict().items()},
                 'mean':mean.tolist(),'scale':scale.tolist(),'calibration':calibrators[name],
                 'dataset_manifest_sha256':digest(Path(dataset)/'manifest.json')}
        torch.save(payload,out/(name+'.pt'));models[name]=losses
    selected=min(gate,key=lambda k:gate[k]['mean_query_log_loss'])
    prior=np.asarray([np.bincount(labels[roles==0].reshape(-1,12)[:,i],minlength=5)+1 for i in range(12)],dtype=float)
    prior/=prior.sum(-1,keepdims=True)
    prior=np.broadcast_to(prior.reshape(3,2,2,5),(sum(roles==4),3,2,2,5))
    scores['training_prevalence']=metrics(prior,labels[roles==4]);scores['gate_selected']=scores[selected]
    for name,p in predictions.items():np.save(out/(name+'_evaluation.npy'),p,allow_pickle=False)
    report={'status':'development_engineering_only','dataset_manifest':spec,'dataset_manifest_sha256':digest(Path(dataset)/'manifest.json'),
            'epochs':epochs,'pretraining_epochs':pretraining,'seed':seed,'device':device,
            'environment':{'python':platform.python_version(),'numpy':np.__version__,'torch':torch.__version__},
            'git_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=Path(__file__).parent,text=True).strip(),
            'code_sha256':{p.name:digest(p) for p in [Path(__file__),Path(__file__).with_name('execution_model.py'),Path(__file__).with_name('execution_dataset.py')]},
            'normalizer':{'mean':mean.tolist(),'scale':scale.tolist()},'losses':models,'calibration':calibrators,
            'pretraining_corpus':{'windows':len(pretraining_x),'sessions':spec['pretraining_sessions'],
                                  'stride_seconds':spec['pretraining_stride_seconds'],
                                  'training_only':True},
            'gate_metrics':gate,'gate_selected':selected,'evaluation_metrics':scores,
            'role_cases':{str(i):int(sum(roles==i)) for i in range(5)},'unused_role':'pool_calibration',
            'artifacts':{p.name:digest(p) for p in out.iterdir()},
            'limitations':['small reused development sample; query labels are correlated within parent cases',
                           'marginal probabilities, no joint path or enforced cross-horizon consistency',
                           'scratch versus masked reconstruction; unequal total compute disclosed',
                           'no live HiPerGator, latency, execution costs, fill, impact or quantum claim']}
    (out/'report.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dataset',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--epochs',type=int,default=3);p.add_argument('--pretraining-epochs',type=int,default=3);p.add_argument('--device',default='cpu')
    a=p.parse_args();print(json.dumps(run(a.dataset,a.output,a.epochs,a.pretraining_epochs,device=a.device)['evaluation_metrics'],indent=2))
