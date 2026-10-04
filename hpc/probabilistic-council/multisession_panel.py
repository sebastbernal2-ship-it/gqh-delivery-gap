"""Merge pinned WebSocket files into a development panel; all receive-time claims are assumed."""
from __future__ import annotations

import argparse
from bisect import bisect_right
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
import re

from synchronized_tape import (CausalTape, NS, MAX_BOOK_AGE_NS, HISTORY_NS,
                               digest, parquet_rows, parse_messages, summarize, utc)

PARTITIONS = ('training','specialist_calibration','gate_fit','pool_calibration','evaluation')
FEATURES = ('spread_bps','depth_imbalance','reported_flow_30s','log_observed_volume_30s','move_5s_bps','rv_30s_bps')
TARGET = 'btc-recorded-proxy-mid-5s-bins-1bp-v1'


def merge_events(events, kind):
    """Cross-file retransmissions resolve at earliest recorded availability, never by outcomes."""
    unique, duplicates = {}, 0
    for x in sorted(events, key=lambda x:(x.recorded_ns,x.event_ns)):
        key = x.event_ns if kind=='books' else (x.event_ns,x.tid)
        contents = (x.bids,x.asks) if kind=='books' else (x.side,x.price,x.size)
        if key in unique:
            previous=unique[key]
            before=(previous.bids,previous.asks) if kind=='books' else (previous.side,previous.price,previous.size)
            if before!=contents:
                raise ValueError('conflicting cross-file identity')
            duplicates+=1
        else:
            unique[key]=x
    return list(unique.values()),duplicates


def session_cases(books, trades, session):
    """Pure transformation, with a fixed recorded-clock schedule and explicit future labels."""
    if not books or not trades:
        raise ValueError('empty book/trade session')
    tape=CausalTape(books,trades)
    lo=max(min(x.recorded_ns for x in books),min(x.recorded_ns for x in trades))
    hi=min(max(x.recorded_ns for x in books),max(x.recorded_ns for x in trades))
    if hi<=lo:
        raise ValueError('no recorded-clock overlap')
    rows, labels, exclusions=[],[],Counter()
    for decision in range(lo+HISTORY_NS,hi-5*NS,6*NS):
        try:
            state=tape.features_at(decision)
            current=tape.book_at(decision)
            future=tape.book_at(decision+5*NS)
            if future.recorded_ns<=decision:
                raise ValueError('no newly recorded future book')
            bridge=tape.book_states[bisect_right(tape.book_times,decision)-1:bisect_right(tape.book_times,decision+5*NS)]
            if any(b.event_ns-a.event_ns>MAX_BOOK_AGE_NS for a,b in zip(bridge,bridge[1:])):
                raise ValueError('label history gap')
        except ValueError as e:
            exclusions[str(e)]+=1
            continue
        change=(future.mid/current.mid-1)*1e4
        case=f'BTC:{session}:{decision}'
        ref=f'{session}:observed-trades:{decision-HISTORY_NS}:{decision}'
        hist=f'{state["history_start_ref"]}:through:{current.source_ref}'
        rows.append(dict(case_id=case,episode_id=f'BTC:session:{session}',instrument='BTC',
                         decision_at=utc(decision),label_end=utc(decision+5*NS),
                         label_available_at=utc(decision+5*NS),feature_available_at=[utc(decision)]*6,
                         features=state['features'],label=0 if change < -1 else 2 if change > 1 else 1,
                         target_id=TARGET,source_refs=[current.source_ref]*2+[ref]*2+[hist]*2))
        labels.append(dict(case_id=case,decision_ns=decision,feature_event_ns=current.event_ns,
                           label_event_ns=future.event_ns,label_recorded_ns=future.recorded_ns,
                           label_horizon_ns=decision+5*NS,feature_book_ref=current.source_ref,
                           label_book_ref=future.source_ref,observed_trade_refs=state['trade_refs'],
                           feature_mid=current.mid,future_mid=future.mid,return_bps=change))
    return rows,labels,dict(exclusions),{'start_ns':lo,'end_ns':hi,'duration_ns':hi-lo}


def validate_plan(plan):
    entries=plan['files']
    if plan.get('scope')!='development_only' or not plan.get('selection_rule'):
        raise ValueError('development scope and selection rule required')
    if not entries or len({e['sha256'] for e in entries})!=len(entries):
        raise ValueError('unique source objects required')
    if any(not re.fullmatch('[0-9a-f]{64}',e['sha256']) or type(e['size']) is not int or e['size']<=0 for e in entries):
        raise ValueError('source hash and positive integer size required')
    max_bytes=plan.get('max_bytes',750_000_000)
    if type(max_bytes) is not int or not 0<max_bytes<=2_000_000_000 or sum(e['size'] for e in entries)>max_bytes:
        raise ValueError('plan exceeds bounded acquisition cap')
    sessions=sorted(set(e['session'] for e in entries))
    for s in sessions:
        day=datetime.strptime(s,'%Y-%m-%d')
        if not 2025<=day.year<=2026:
            raise ValueError('sessions must be development dates in 2025-2026')
    if 'session_roles' in plan:
        roles=plan['session_roles']
        if set(roles)!=set(sessions) or set(roles.values())!=set(PARTITIONS):
            raise ValueError('every session needs exactly one of the five declared chronological roles')
        ranks=[PARTITIONS.index(roles[s]) for s in sessions]
        if ranks!=sorted(ranks):
            raise ValueError('session roles must form nonempty chronological blocks')
        minimum=plan.get('minimum_sessions_per_role',3)
        if type(minimum) is not int or minimum<3:
            raise ValueError('at least three sessions per role are required')
        if any(ranks.count(i)<minimum for i in range(len(PARTITIONS))):
            raise ValueError('too few metadata-selected sessions in a role')
        for s in sessions:
            current=[e for e in entries if e['session']==s]
            counts=Counter(e['kind'] for e in current)
            if counts['books']!=counts['trades'] or counts['books']<1:
                raise ValueError('each session needs matched book and trade file counts')
            if any('pair_id' not in e for e in current):
                raise ValueError('explicit-role plans require paired source ids')
            by_pair={}
            for e in current:by_pair.setdefault(e['pair_id'],[]).append(e['kind'])
            if any(Counter(kinds)!=Counter({'books':1,'trades':1}) for kinds in by_pair.values()):
                raise ValueError('each pair id must identify one book file and one trade file')
            entries_by_pair={}
            for e in current:entries_by_pair.setdefault(e['pair_id'],[]).append(e)
            for paired in entries_by_pair.values():
                stamps=[e.get('filename_timestamp_s') for e in paired]
                if any(type(t) is not int for t in stamps) or abs(stamps[0]-stamps[1])>2:
                    raise ValueError('book/trade filename clocks must match within two seconds')
    else:
        if len(sessions)!=6:
            raise ValueError('legacy plan requires six declared sessions')
        for s in sessions:
            if Counter(e['kind'] for e in entries if e['session']==s)!=Counter({'books':2,'trades':2}):
                raise ValueError('each legacy session requires two book and two trade files')
    return sessions


def build(plan_path, objects, output):
    plan=json.loads(Path(plan_path).read_text())
    sessions=validate_plan(plan)
    collected={s:{'books':[],'trades':[]} for s in sessions}
    source_counts={}
    # Hash-verify every file before any source is parsed, so a missing object never emits a panel.
    for e in plan['files']:
        path=Path(objects)/e['sha256']
        if path.stat().st_size!=e['size'] or digest(path)!=e['sha256']:
            raise ValueError('source bytes disagree with pinned publisher identity')
    for e in plan['files']:
        events,counts=parse_messages(parquet_rows(Path(objects)/e['sha256']),e['kind'],e['sha256'])
        collected[e['session']][e['kind']].extend(events)
        source_counts[e['sha256']]=counts
    panel,labels,coverage=[],[],{}
    seen_books,seen_trades=set(),set()
    for index,s in enumerate(sessions):
        books,bd=merge_events(collected[s]['books'],'books')
        trades,td=merge_events(collected[s]['trades'],'trades')
        # Filename dates label acquisition blocks, not an assertion about actual event dates.
        # A file ending just after midnight can legitimately contain the prior calendar day.
        book_ids={x.event_ns for x in books};trade_ids={(x.event_ns,x.tid) for x in trades}
        if book_ids & seen_books or trade_ids & seen_trades:
            raise ValueError('identity overlaps declared sessions')
        seen_books.update(book_ids);seen_trades.update(trade_ids)
        rows,audit,excluded,overlap=session_cases(books,trades,s)
        if not rows:
            raise ValueError('no causal cases in a declared session')
        role=plan.get('session_roles',{}).get(s,PARTITIONS[max(0,index-1)])
        for r in rows:r['partition']=role
        panel.extend(rows);labels.extend(audit)
        coverage[s]=dict(books=summarize(books),trades=summarize(trades),overlap=overlap,
                         cross_file_retransmissions={'books':bd,'trades':td},exclusions=excluded,
                         cases_before_boundary_purge=len(rows),partition=role)
    panel.sort(key=lambda r:r['decision_at'])
    purged=Counter();kept=[]
    for i,role in enumerate(PARTITIONS):
        following=[r['decision_at'] for r in panel if i<4 and r['partition']==PARTITIONS[i+1]]
        for r in panel:
            if r['partition']==role:
                if following and r['label_available_at']>=min(following):purged[role]+=1
                else:kept.append(r)
    if any(not any(r['partition']==p for r in kept) for p in PARTITIONS):
        raise ValueError('empty chronological role after purge')
    out=Path(output);out.mkdir(parents=True,exist_ok=False)
    panel_path=out/'panel.jsonl'
    panel_path.write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in kept))
    ids={r['case_id'] for r in kept}
    (out/'label_audit.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in labels if r['case_id'] in ids))
    manifest=dict(scope='development_only',target_id=TARGET,feature_order=FEATURES,
                  outcome_order=['down','flat','up'],groups={'A':[0,1],'B':[2,3],'C':[4,5]},
                  label_rule='latest valid recorded-proxy book at decision versus latest at decision+5s; +/-1bp, ties flat; new future observation required',
                  availability_basis='retrospective_assumption',availability_note='Parquet recorded clock is an unverified availability proxy; venue-clock-only joins forbidden',
                  development_start=utc(min(x.recorded_ns for c in collected.values() for x in c['books'])-NS),
                  development_end=utc(max(x.recorded_ns for c in collected.values() for x in c['books'])+NS),
                  panel_sha256=digest(panel_path),plan_sha256=digest(plan_path),adapter_sha256=digest(__file__),
                  causal_adapter_sha256=digest(Path(__file__).with_name('synchronized_tape.py')),
                  session_roles=plan.get('session_roles',{s:coverage[s]['partition'] for s in sessions}),
                  source_counts=source_counts,source_files=plan['files'],session_coverage=coverage,
                  partition_boundary_purges=dict(purged),panel_rows=len(kept),
                  label_audit_sha256=digest(out/'label_audit.jsonl'),
                  partition_class_counts={p:dict(Counter(str(r['label']) for r in kept if r['partition']==p)) for p in PARTITIONS},
                  limitations=['six small development sessions selected by filename order, not representative regimes',
                               'unverified mirror provenance equivalence, recorded-clock meaning and trade-feed completeness',
                               'reported trade-side semantics unverified; no liquidation labels or order-level queue data',
                               'overlapping trailing histories; no independent-case or executable-alpha claim',
                               'first five-minute candidate previously inspected for engineering, not a pristine holdout'])
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    return manifest


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan',type=Path,required=True);p.add_argument('--objects',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(json.dumps(build(a.plan,a.objects,a.output),indent=2,sort_keys=True))
