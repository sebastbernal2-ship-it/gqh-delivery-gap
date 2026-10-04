"""OFF-CLUSTER: prepare hash-pinned numerical Jev sequences and side/horizon labels."""
from bisect import bisect_right
from collections import Counter
import argparse
import json
from pathlib import Path

import numpy as np
from multisession_panel import PARTITIONS, merge_events, validate_plan
from synchronized_tape import CausalTape, NS, digest, parquet_rows, parse_messages

HORIZONS=(5,15,60)
TERMINAL_EDGES=(-2.,-.5,.5,2.)
ADVERSE_EDGES=(.5,1.,2.,5.)
PRETRAIN_STRIDE_NS=10*NS
FEATURES=tuple(f'{side}_{kind}_{i}' for i in range(1,6) for side in ('bid','ask') for kind in ('offset_bps','depth_fraction'))+('spread_bps','flow_5s','log_volume_5s','book_age_s')


def step(tape,t):
    b=tape.book_at(t);total=sum(s for _,s in b.bids[:5]+b.asks[:5])
    v=[]
    for i in range(5):
        for side in (b.bids,b.asks):
            px,sz=side[i];v.extend(((px/b.mid-1)*1e4,sz/total))
    trades=[x for x in tape.trades[bisect_right(tape.trade_times,t-5*NS):bisect_right(tape.trade_times,t)] if t-5*NS<x.event_ns<=t]
    volume=sum(x.size for x in trades)
    v.extend(((b.asks[0][0]-b.bids[0][0])/b.mid*1e4,
              sum((1 if x.side=='B' else -1)*x.size for x in trades)/volume if volume else 0.,
              np.log1p(volume),(t-b.event_ns)/NS))
    if not np.isfinite(v).all():raise ValueError('nonfinite numerical features')
    return v


def cases(books,trades):
    tape=CausalTape(books,trades)
    lo=max(min(x.recorded_ns for x in books),min(x.recorded_ns for x in trades))
    hi=min(max(x.recorded_ns for x in books),max(x.recorded_ns for x in trades))
    output=[];excluded=Counter()
    for t in range(lo+35*NS,hi-60*NS,65*NS):
        try:
            old=tape.book_at(t-30*NS);current=tape.book_at(t)
            end=tape.book_at(t+60*NS)
            path=tape.book_states[bisect_right(tape.book_times,t-30*NS)-1:bisect_right(tape.book_times,t+60*NS)]
            if any(b.event_ns-a.event_ns>2*NS for a,b in zip(path,path[1:])):raise ValueError('history/label gap')
            sequence=[step(tape,t+offset*NS) for offset in range(-30,1,2)]
            targets=[];audit=[]
            for h in HORIZONS:
                last=tape.book_at(t+h*NS)
                if last.recorded_ns<=t:raise ValueError('missing future observation')
                future=tape.book_states[bisect_right(tape.book_times,t):bisect_right(tape.book_times,t+h*NS)]
                moves=[0.]+[(b.mid/current.mid-1)*1e4 for b in future]
                terminal=(last.mid/current.mid-1)*1e4
                by_side=[]
                for sign in (1,-1):
                    adverse=max(-sign*r for r in moves)
                    by_side.append([bisect_right(TERMINAL_EDGES,sign*terminal),bisect_right(ADVERSE_EDGES,adverse)])
                targets.append(by_side)
                audit.append({'horizon':h,'terminal_bps':terminal,'buy_adverse_bps':-min(moves),'sell_adverse_bps':max(moves),'last_book_ref':last.source_ref})
            output.append({'decision_ns':t,'label_available_ns':t+60*NS,'sequence':sequence,'targets':targets,
                           'history_ref':old.source_ref,'current_ref':current.source_ref,'audit':audit})
        except ValueError as error:excluded[str(error)]+=1
    return output,dict(excluded)


def pretraining_windows(books,trades):
    """Unlabeled, past-only windows; called only for whole training-role sessions."""
    tape=CausalTape(books,trades)
    if not tape.books or not tape.trades:return [],[]
    lo=max(tape.books[0].recorded_ns,tape.trades[0].recorded_ns)
    hi=min(tape.books[-1].recorded_ns,tape.trades[-1].recorded_ns)
    output=[];clocks=[];excluded=Counter()
    for t in range(lo+30*NS,hi,PRETRAIN_STRIDE_NS):
        try:
            start=bisect_right(tape.book_times,t-30*NS)-1
            stop=bisect_right(tape.book_times,t)
            path=tape.book_states[start:stop]
            if not path or any(b.event_ns-a.event_ns>2*NS for a,b in zip(path,path[1:])):
                raise ValueError('pretraining history gap')
            sequence=[step(tape,t+offset*NS) for offset in range(-30,1,2)]
            output.append(sequence);clocks.append(t)
        except ValueError as error:excluded[str(error)]+=1
    return output,clocks


def prepare(plan_path,objects,output):
    plan=json.loads(Path(plan_path).read_text());sessions=validate_plan(plan)
    for e in plan['files']:
        p=Path(objects)/e['sha256']
        if p.stat().st_size!=e['size'] or digest(p)!=e['sha256']:raise ValueError('source hash/size mismatch')
    groups={s:{'books':[],'trades':[]} for s in sessions}
    for e in plan['files']:
        events,_=parse_messages(parquet_rows(Path(objects)/e['sha256']),e['kind'],e['sha256'])
        groups[e['session']][e['kind']].extend(events)
    all_rows=[];coverage={};seen={'books':set(),'trades':set()};pretrain_rows=[];pretrain_clocks=[];pretrain_sessions=[]
    for i,s in enumerate(sessions):
        streams={}
        for kind in ('books','trades'):
            streams[kind],_=merge_events(groups[s][kind],kind)
            keys={x.event_ns if kind=='books' else (x.event_ns,x.tid) for x in streams[kind]}
            if keys&seen[kind]:raise ValueError('cross-session source overlap')
            seen[kind]|=keys
        rows,excluded=cases(streams['books'],streams['trades'])
        if not rows:raise ValueError('empty session')
        role_name=plan['session_roles'][s] if 'session_roles' in plan else PARTITIONS[max(0,i-1)]
        role=PARTITIONS.index(role_name)
        for row in rows:row.update(role=role,session=s)
        all_rows+=rows;coverage[s]={'cases':len(rows),'exclusions':excluded,'role':role_name}
        if role==0:
            windows,clocks=pretraining_windows(streams['books'],streams['trades'])
            pretrain_rows.extend(windows);pretrain_clocks.extend(clocks);pretrain_sessions.extend([s]*len(windows))
            coverage[s]['unlabeled_pretraining_windows']=len(windows)
    all_rows.sort(key=lambda r:r['decision_ns'])
    kept=[]
    for role in range(5):
        later=[r['decision_ns'] for r in all_rows if r['role']==role+1]
        kept.extend(r for r in all_rows if r['role']==role and (not later or r['label_available_ns']<min(later)))
    if any(not any(r['role']==i for r in kept) for i in range(5)):raise ValueError('empty role')
    out=Path(output);out.mkdir(parents=True,exist_ok=False)
    arrays={'features':np.asarray([r['sequence'] for r in kept],dtype=np.float32),
            'targets':np.asarray([r['targets'] for r in kept],dtype=np.int64),
            'clocks':np.asarray([[r['decision_ns'],r['label_available_ns']] for r in kept],dtype=np.int64),
            'roles':np.asarray([r['role'] for r in kept],dtype=np.int64),
            'pretraining_features':np.asarray(pretrain_rows,dtype=np.float32),
            'pretraining_clocks':np.asarray(pretrain_clocks,dtype=np.int64)}
    if not len(arrays['pretraining_features']):raise ValueError('empty training-only pretraining corpus')
    for name,values in arrays.items():np.save(out/(name+'.npy'),values,allow_pickle=False)
    (out/'label_audit.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in kept))
    spec={'scope':'development_only','availability_basis':'retrospective_assumption','target_id':'btc-observed-proxy-terminal-excursion-v1',
          'feature_order':FEATURES,'horizons':HORIZONS,'sides':['buy','sell'],'tasks':['terminal','adverse'],
          'terminal_edges_bps':TERMINAL_EDGES,'adverse_edges_bps':ADVERSE_EDGES,'partitions':PARTITIONS,
          'sequence_steps':16,'panel_rows':len(kept),'pretraining_rows':len(pretrain_rows),
          'pretraining_stride_seconds':PRETRAIN_STRIDE_NS//NS,
          'pretraining_sessions':sorted(set(pretrain_sessions)),
          'pretraining_window_sessions':pretrain_sessions,
          'pretraining_clock_range_ns':[min(pretrain_clocks),max(pretrain_clocks)],
          'session_roles':plan['session_roles'] if 'session_roles' in plan else {s:PARTITIONS[max(0,i-1)] for i,s in enumerate(sessions)},
          'session_coverage':coverage,'sources':plan['files'],
          'plan_sha256':digest(plan_path),'adapter_sha256':digest(__file__),
          'causal_adapter_sha256':digest(Path(__file__).with_name('synchronized_tape.py')),
          'merge_adapter_sha256':digest(Path(__file__).with_name('multisession_panel.py')),
          'sessions':[r['session'] for r in kept],
          'array_sha256':{name+'.npy':digest(out/(name+'.npy')) for name in arrays},
          'label_audit_sha256':digest(out/'label_audit.jsonl'),
          'limitations':['development acquisition, not competition holdout',
                         'recorded availability proxy and trade completeness unverified',
                         'observed snapshot excursions only; no own impact, fills, costs or joint path claim']}
    (out/'manifest.json').write_text(json.dumps(spec,indent=2,sort_keys=True)+'\n')
    return spec


def load_cache(root):
    root=Path(root);s=json.loads((root/'manifest.json').read_text())
    if s['scope']!='development_only' or s['availability_basis']!='retrospective_assumption' or s['target_id']!='btc-observed-proxy-terminal-excursion-v1':raise ValueError('wrong cache scope/target')
    if (s['horizons']!=list(HORIZONS) or s['feature_order']!=list(FEATURES) or s['partitions']!=list(PARTITIONS) or
        s['sides']!=['buy','sell'] or s['tasks']!=['terminal','adverse'] or s['terminal_edges_bps']!=list(TERMINAL_EDGES) or s['adverse_edges_bps']!=list(ADVERSE_EDGES)):
        raise ValueError('cache schema mismatch')
    arrays={}
    for name in ('features','targets','clocks','roles','pretraining_features','pretraining_clocks'):
        p=root/(name+'.npy')
        if digest(p)!=s['array_sha256'][p.name]:raise ValueError('cache hash mismatch')
        arrays[name]=np.load(p,mmap_mode='r',allow_pickle=False)
    x,y,c,r,px,pc=(arrays[k] for k in ('features','targets','clocks','roles','pretraining_features','pretraining_clocks'));n=len(x)
    if x.shape!=(n,16,len(FEATURES)) or y.shape!=(n,3,2,2) or c.shape!=(n,2) or r.shape!=(n,) or len(s['sessions'])!=n:raise ValueError('cache shape mismatch')
    if not np.isfinite(x).all() or y.dtype.kind not in 'iu' or ((y<0)|(y>4)).any():raise ValueError('invalid cache values')
    if (px.ndim!=3 or px.shape[1:]!=(16,len(FEATURES)) or pc.shape!=(len(px),) or
        len(px)!=s['pretraining_rows'] or len(s['pretraining_window_sessions'])!=len(px) or
        not np.isfinite(px).all() or pc.dtype!=np.int64 or (np.diff(pc)<0).any()):
        raise ValueError('invalid training-only pretraining corpus')
    if s['pretraining_clock_range_ns']!=[int(pc.min()),int(pc.max())]:
        raise ValueError('pretraining clock manifest mismatch')
    if c.dtype!=np.int64 or r.dtype.kind not in 'iu' or ((r<0)|(r>4)).any() or (c[:,0]>=c[:,1]).any() or (np.diff(c[:,0])<=0).any():raise ValueError('invalid chronology')
    if (c[:,0]<1735689600*NS).any() or (c[:,1]>=1798761600*NS).any():raise ValueError('outside development fence')
    seen=set()
    for role in range(5):
        mask=r==role
        if not mask.any():raise ValueError('empty role')
        episodes={s['sessions'][i] for i in np.flatnonzero(mask)}
        if episodes&seen:raise ValueError('session crosses roles')
        seen|=episodes
        if role<4 and c[mask,1].max()>=c[r==role+1,0].min():raise ValueError('unmatured role labels')
    train_sessions={s['sessions'][i] for i in np.flatnonzero(r==0)}
    if (not set(s['pretraining_sessions'])<=train_sessions or
        set(s['pretraining_sessions'])!=set(s['pretraining_window_sessions'])):
        raise ValueError('pretraining includes a non-training session')
    return s,arrays


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);p.add_argument('--objects',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(json.dumps(prepare(a.plan,a.objects,a.output),indent=2,sort_keys=True))
