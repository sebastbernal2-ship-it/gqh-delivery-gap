"""Build a bounded BTC public-mirror development panel; availability is explicitly assumed."""
from __future__ import annotations

import argparse
from bisect import bisect_left, bisect_right
from collections import Counter
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path

from information_views import PARTITIONS, digest, load_panel

NS = 1_000_000_000
SOURCE = '3783f2f7c3ea5705a3c5f35c37d4d6ec54a6713b291b851b06e3d6aabb0bfff9'
RUN_ID = '27a69e4024235408eaff54876c781d0b9135713bb71780a386e16ce6db46fb2a'
TARGET = 'btc-mirror-mid-5s-after-assumed-decision-bins-1bp-v1'
FEATURES = ('spread_bps', 'top_imbalance', 'depth_imbalance', 'depth_ratio', 'move_5s_bps', 'rv_30s_bps')


def iso_ns(value):
    # Round UP to the next microsecond, never earlier than the source nanosecond clock.
    return (datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=(value + 999)//1000)).isoformat()


def normalize(rows):
    books, excluded = [], Counter()
    for r in rows:
        b = json.loads(r['BOOK'])
        if b.get('coin') != 'BTC' or r['SOURCE_SHA256'] != SOURCE:
            raise ValueError('unexpected coin/source; this adapter is pinned to the declared pilot')
        if type(b.get('timestamp')) is not int:
            raise ValueError('source timestamp must be exact integer nanoseconds')
        if json.loads(r.get('QUALITY_FLAGS') or '[]') and any(flag in json.loads(r['QUALITY_FLAGS']) for flag in
                ('invalid_best_prices', 'locked_or_crossed_book', 'nonfinite_fields_replaced_with_null')):
            excluded['quality_flag'] += 1
            continue
        try:
            prices = [[float(b[f'{side}_px_{i}']) for i in range(1,6)] for side in ('bid','ask')]
            sizes = [[float(b[f'{side}_sz_{i}']) for i in range(1,6)] for side in ('bid','ask')]
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError('expected five levels with bid/ask px/sz fields') from error
        if not all(math.isfinite(v) and v > 0 for side in prices+sizes for v in side):
            excluded['invalid_depth'] += 1
            continue
        bids, asks = prices
        if bids[0] >= asks[0] or bids != sorted(bids,reverse=True) or asks != sorted(asks):
            excluded['invalid_order'] += 1
            continue
        books.append(dict(t=b['timestamp'], mid=(bids[0]+asks[0])/2, bid=bids[0], ask=asks[0],
                          bid_sizes=sizes[0], ask_sizes=sizes[1], row_index=int(r['ROW_INDEX']),
                          row_sha256=r['ROW_SHA256']))
    books.sort(key=lambda b:b['t'])
    if len({b['t'] for b in books}) != len(books):
        raise ValueError('duplicate timestamps need an explicit upstream resolution policy')
    return books, excluded


def build(source_csv, output):
    with Path(source_csv).open() as f:
        raw = list(csv.DictReader(f))
    if len(raw) >= 5000:
        raise ValueError('export reached SQL limit; completeness is ambiguous')
    books, excluded = normalize(raw)
    if not books:
        raise ValueError('no valid book observations')
    # Do not accept a different date or a larger sample under this pilot protocol.
    lower = 1765065600 * NS  # 2025-12-07 00:00 UTC
    if any(not lower <= b['t'] < lower + 86400*NS for b in books):
        raise ValueError('book outside declared development day')
    times = [b['t'] for b in books]
    panel, label_audit = [], []
    next_decision_source = 0
    csv_hash = digest(source_csv)
    for i,b in enumerate(books):
        t = b['t']
        if t < next_decision_source:
            excluded['sampling_stride'] += 1
            continue
        old = bisect_right(times,t-30*NS)-1
        lag = bisect_right(times,t-5*NS)-1
        if old < 0 or lag < 0:
            excluded['warmup'] += 1
            continue
        decision = t+NS
        target = decision+5*NS
        end = bisect_left(times,target)
        if end >= len(books) or times[end] > target+2*NS:
            excluded['missing_or_late_label'] += 1
            continue
        if any(times[j+1]-times[j] > 2*NS for j in range(old,end)):
            excluded['source_gap'] += 1
            continue
        depth_bid, depth_ask = sum(b['bid_sizes']), sum(b['ask_sizes'])
        top_bid, top_ask = b['bid_sizes'][0], b['ask_sizes'][0]
        rv = math.sqrt(sum((1e4*math.log(books[j]['mid']/books[j-1]['mid']))**2 for j in range(old+1,i+1)))
        features = ((b['ask']-b['bid'])/b['mid']*1e4, (top_bid-top_ask)/(top_bid+top_ask),
                    (depth_bid-depth_ask)/(depth_bid+depth_ask),
                    math.log((depth_bid+depth_ask)/(top_bid+top_ask)),
                    (b['mid']/books[lag]['mid']-1)*1e4,rv)
        change = (books[end]['mid']/b['mid']-1)*1e4
        case = f'BTC:{t}'
        ref = f'{csv_hash}:source-row-{b["row_index"]}'
        history_ref = f'{csv_hash}:source-time-ns-{times[old]}-through-{t}'
        panel.append(dict(case_id=case, episode_id=f'BTC:minute:{decision//(60*NS)}', instrument='BTC',
                          decision_at=iso_ns(decision), label_end=iso_ns(times[end]),
                          label_available_at=iso_ns(times[end]+NS),
                          feature_available_at=[iso_ns(decision)]*6, features=features,
                          label=0 if change < -1 else 2 if change > 1 else 1,
                          target_id=TARGET, source_refs=[ref]*4+[history_ref]*2))
        label_audit.append(dict(case_id=case, source_time_ns=t, source_row=b['row_index'],
                                label_time_ns=times[end], label_row=books[end]['row_index'],
                                feature_mid=b['mid'], future_mid=books[end]['mid'], return_bps=change))
        next_decision_source = t+6*NS
    episodes=list(dict.fromkeys(r['episode_id'] for r in panel))
    if len(episodes)<10:
        raise ValueError('fewer than ten minute episodes; cannot populate five roles')
    n=len(episodes)
    edges=(0,n//2,n*65//100,n*80//100,n*90//100,n)
    mapping={ep:PARTITIONS[i] for i in range(5) for ep in episodes[edges[i]:edges[i+1]]}
    for r in panel: r['partition']=mapping[r['episode_id']]
    kept=[]
    for i,p in enumerate(PARTITIONS):
        block=[r for r in panel if r['partition']==p]
        following=[r['decision_at'] for r in panel if i<4 and r['partition']==PARTITIONS[i+1]]
        for r in block:
            if following and r['label_available_at'] >= min(following):
                excluded['partition_boundary']+=1
            else: kept.append(r)
    output=Path(output)
    output.mkdir(parents=True,exist_ok=False)
    panel_path=output/'panel.jsonl'
    panel_path.write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in kept))
    kept_ids={r['case_id'] for r in kept}
    (output/'label_audit.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in label_audit if r['case_id'] in kept_ids))
    manifest=dict(scope='development_only', target_id=TARGET, feature_order=FEATURES,
                  outcome_order=['down','flat','up'],groups={'A':[0,1],'B':[2,3],'C':[4,5]},
                  label_rule='midpoint return from feature snapshot to first snapshot >= decision+5s; +/-1bp, ties flat',
                  availability_basis='retrospective_assumption',
                  availability_note='source timestamps + assumed 1s; historical receive clocks and venue equivalence unverified',
                  development_start='2025-12-07T00:00:00+00:00',development_end='2025-12-08T00:00:00+00:00',
                  panel_sha256=digest(panel_path),export_sha256=csv_hash, source_sha256=SOURCE, run_id=RUN_ID,
                  raw_rows=len(raw), valid_book_rows=len(books), panel_rows=len(kept), exclusions=dict(excluded),
                  first_source_ns=times[0],last_source_ns=times[-1],
                  label_audit_sha256=digest(output/'label_audit.jsonl'),
                  limitations=['33-minute one-day pilot; not independent regimes',
                               'three views of one book stream; no synchronized fills, OI or liquidation labels',
                               'overlapping feature histories; six-second sampling does not imply independent cases',
                               'snapshot-clock latency assumption; forecast engineering only, not executable alpha'])
    manifest_path=output/'manifest.json'
    manifest_path.write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    load_panel(panel_path,manifest_path)
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(build(args.csv,args.output),indent=2))
