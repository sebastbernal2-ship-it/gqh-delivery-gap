"""OFF-CLUSTER: fetch a pinned public Hugging Face Parquet plan into a private object cache."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import re
import time
from urllib.parse import quote

import certifi
import requests


def sha256(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def load_plan(path):
    p=Path(path);spec=json.loads(p.read_text())
    if spec.get('scope')!='development_only' or not spec.get('files'):
        raise ValueError('a nonempty development-only file plan is required')
    limit=spec.get('max_bytes',750_000_000)
    if type(limit) is not int or not 0<limit<=2_000_000_000:
        raise ValueError('public plan cap must be between one byte and two GB')
    seen=set();total=0
    for e in spec['files']:
        if (not re.fullmatch(r'[0-9a-f]{64}',e.get('sha256','')) or type(e.get('size')) is not int
                or e['size']<=0 or not e.get('dataset') or not e.get('revision')
                or not e.get('path') or e['path'].startswith('/') or '..' in Path(e['path']).parts):
            raise ValueError('each source needs a pinned revision, safe path, byte size and SHA-256')
        if e['sha256'] in seen:raise ValueError('duplicate object hash in plan')
        seen.add(e['sha256']);total+=e['size']
    if total>limit:raise ValueError('plan exceeds its declared byte cap')
    return spec,total


def fetch_one(entry,root):
    target=root/entry['sha256'];partial=root/(entry['sha256']+'.partial')
    if target.exists():
        if target.stat().st_size==entry['size'] and sha256(target)==entry['sha256']:
            return 'cached',entry['size']
        raise ValueError(f'cache object exists with wrong bytes: {entry["path"]}')
    url=('https://huggingface.co/datasets/'+quote(entry['dataset'],safe='/')+'/resolve/'+
         quote(entry['revision'],safe='')+'/'+quote(entry['path'],safe='/')+'?download=true')
    session=requests.Session();session.headers['User-Agent']='GQH-bounded-development-sample/1.0'
    for attempt in range(4):
        h=hashlib.sha256();count=0
        try:
            with session.get(url,stream=True,verify=certifi.where(),timeout=(20,180)) as response:
                response.raise_for_status()
                with partial.open('wb') as out:
                    for block in response.iter_content(1024*1024):
                        if not block:continue
                        count+=len(block)
                        if count>entry['size']:raise ValueError('download exceeds pinned byte size')
                        h.update(block);out.write(block)
            if count!=entry['size'] or h.hexdigest()!=entry['sha256']:
                raise ValueError(f'download hash/size mismatch for {entry["path"]}')
            os.replace(partial,target)
            return 'downloaded',count
        except Exception:
            partial.unlink(missing_ok=True)
            if attempt==3:raise
            time.sleep(attempt+1)
    raise RuntimeError('unreachable')


def fetch(plan_path,objects,workers=4):
    if not 1<=workers<=8:raise ValueError('worker count must be 1 through 8')
    spec,total=load_plan(plan_path);root=Path(objects);root.mkdir(parents=True,exist_ok=True)
    done=0;verified=0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        jobs=[pool.submit(fetch_one,e,root) for e in spec['files']]
        for job in as_completed(jobs):
            state,size=job.result();done+=1;verified+=size
            if done%10==0 or done==len(jobs):
                print(f'verified {done}/{len(jobs)} objects; {verified}/{total} bytes',flush=True)
    return {'objects':done,'bytes':verified,'plan_sha256':sha256(plan_path)}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--objects',type=Path,required=True)
    parser.add_argument('--workers',type=int,default=4)
    args=parser.parse_args()
    print(json.dumps(fetch(args.plan,args.objects,args.workers),indent=2))
