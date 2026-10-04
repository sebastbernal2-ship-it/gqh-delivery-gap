"""OFF-CLUSTER: export projected live journals to segment-separated hash-pinned Parquet.

This produces source candidates, not an assigned split, labeled panel or training acceptance.
Never merge files from different segments merely because their UTC dates agree.
"""
from __future__ import annotations

import argparse
from datetime import datetime,timezone
import json
from pathlib import Path

from source_clock_audit import inspect_rows
from synchronized_tape import digest,parquet_rows


def export(capture,output):
    import pyarrow as pa
    import pyarrow.parquet as pq

    capture=Path(capture)
    receipt=json.loads((capture/'capture.json').read_text())
    source=capture/'messages.jsonl'
    if receipt.get('schema_version')!='execution-live-capture-v1' or digest(source)!=receipt['messages_sha256']:
        raise ValueError('capture receipt/source identity mismatch')
    root=Path(output)
    root.mkdir(parents=True,exist_ok=False)
    schema=pa.schema([('timestamp',pa.timestamp('ns')),('coin',pa.string()),('payload',pa.string())])
    inventory=[]
    segment=None
    writers={}
    buffers={}
    first_wall=None
    last_sequence=-1

    def flush(kind):
        if buffers[kind]:
            writers[kind].write_table(pa.Table.from_arrays([
                pa.array([r[0] for r in buffers[kind]],type=pa.int64()).cast(pa.timestamp('ns')),
                pa.array(['BTC']*len(buffers[kind])),pa.array([r[1] for r in buffers[kind]])],schema=schema))
            buffers[kind].clear()

    def close_segment():
        if segment is None:
            return
        for kind,writer in writers.items():
            flush(kind)
            writer.close()
            path=root/f'{segment}-{kind}.parquet'
            sha=digest(path)
            stats=inspect_rows(parquet_rows(path),kind)
            path.rename(root/sha)
            inventory.append({'kind':kind,'segment':segment,'sha256':sha,
                'size':(root/sha).stat().st_size,
                'session':datetime.fromtimestamp(first_wall//1_000_000_000,timezone.utc).date().isoformat(),
                'pair_id':f'live:{receipt["messages_sha256"]}:{segment}',
                'clock_audit':stats})

    with source.open() as f:
        for line in f:
            row=json.loads(line)
            if type(row['sequence']) is not int or row['sequence']!=last_sequence+1:
                raise ValueError('non-contiguous local journal sequence')
            last_sequence=row['sequence']
            if type(row['segment']) is not int or row['segment']<1:
                raise ValueError('positive segment required')
            if segment!=row['segment']:
                if segment is not None and row['segment']<=segment:
                    raise ValueError('segments must increase')
                close_segment()
                segment=row['segment']
                first_wall=row['receipt_wall_ns']
                writers={};buffers={}
            if row['coin']!='BTC':
                raise ValueError('unexpected instrument')
            kind={'l2Book':'books','trades':'trades'}[row['payload']['channel']]
            if kind not in writers:
                writers[kind]=pq.ParquetWriter(root/f'{segment}-{kind}.parquet',schema,compression='snappy')
                buffers[kind]=[]
            buffers[kind].append((row['receipt_wall_ns'],json.dumps(row['payload'],separators=(',',':'))))
            if len(buffers[kind])>=1024:
                flush(kind)
    close_segment()
    report={'schema_version':'execution-live-source-inventory-v1','scope':'development_only',
        'capture_receipt_sha256':digest(capture/'capture.json'),'journal_sha256':digest(source),
        'exporter_sha256':digest(__file__),'sources':inventory,'labels_computed':False,
        'ready_for_training':False,
        'blockers':['source inventory only: chronological session roles and coverage not approved',
                    'split and warm up by capture segment; current date-only merger must not be used'],
        'clock_basis':receipt['clock_basis']}
    (root/'inventory.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--capture',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    result=export(a.capture,a.output)
    print(json.dumps({'objects':len(result['sources']),'ready_for_training':False},indent=2))
