"""OFF-CLUSTER: bounded public BTC book/trade capture, never orders or account feeds.

Receipt clock is sampled immediately after recv returns. It includes local/network buffering,
not matching-engine latency. Payload projection removes participant identifiers before disk.
"""
from __future__ import annotations

import argparse
import asyncio
from collections import Counter
import json
import os
from pathlib import Path
import ssl
import time

from synchronized_tape import digest

ENDPOINT = 'wss://api.hyperliquid.xyz/ws'


def project(text):
    raw = json.loads(text)
    channel = raw.get('channel')
    if channel not in ('l2Book', 'trades'):
        return None
    data = raw['data']
    if channel == 'l2Book':
        if data.get('coin') != 'BTC':
            raise ValueError('unexpected instrument')
        data = {'coin':'BTC', 'time':data['time'], 'levels':[
            [{k:level[k] for k in ('px','sz','n') if k in level} for level in side]
            for side in data['levels']]}
    else:
        if not isinstance(data,list) or not data:
            raise ValueError('nonempty trade array required')
        if any(item.get('coin') != 'BTC' for item in data):
            raise ValueError('unexpected instrument')
        data = [{k:item[k] for k in ('coin','time','tid','side','px','sz')} for item in data]
    return {'channel':channel, 'data':data}


class Journal:
    def __init__(self, output, max_bytes):
        self.root = Path(output)
        self.root.mkdir(parents=True, exist_ok=False)
        self.path = self.root/'messages.jsonl'
        self.file = self.path.open('wb')
        self.max_bytes = max_bytes
        self.size = self.sequence = self.segment = 0
        self.counts = Counter()
        self.events = []
        self.last_clock = None
        self.last_sync = time.monotonic()

    def boundary(self, reason, wall_ns, monotonic_ns):
        self.segment += 1
        self.last_clock = None
        self.events.append({'segment':self.segment, 'reason':reason,
                            'wall_ns':wall_ns, 'monotonic_ns':monotonic_ns})

    def append(self, text, wall_ns, monotonic_ns):
        payload = project(text)
        if payload is None:
            return True
        if self.last_clock is not None:
            wall_delta = wall_ns-self.last_clock[0]
            mono_delta = monotonic_ns-self.last_clock[1]
            # Do not join through local clock discontinuities. A new segment forces a warmup.
            if wall_delta <= 0 or mono_delta <= 0 or abs(wall_delta-mono_delta)>100_000_000:
                self.boundary('clock_discontinuity',wall_ns,monotonic_ns)
            elif wall_ns//86_400_000_000_000 != self.last_clock[0]//86_400_000_000_000:
                self.boundary('utc_day_change',wall_ns,monotonic_ns)
        row = {'sequence':self.sequence, 'segment':self.segment,
               'receipt_wall_ns':wall_ns, 'receipt_monotonic_ns':monotonic_ns,
               'coin':'BTC', 'payload':payload}
        block = (json.dumps(row, separators=(',',':'))+'\n').encode()
        if self.size+len(block)>self.max_bytes:
            return False
        self.file.write(block)
        self.file.flush()
        self.size += len(block)
        self.sequence += 1
        self.counts[payload['channel']] += 1
        self.last_clock = (wall_ns,monotonic_ns)
        if time.monotonic()-self.last_sync>=1:
            os.fsync(self.file.fileno())
            self.last_sync = time.monotonic()
        return True

    def finish(self, reason, elapsed, errors):
        self.file.flush()
        os.fsync(self.file.fileno())
        self.file.close()
        receipt = {
            'schema_version':'execution-live-capture-v1','scope':'development_only',
            'endpoint':ENDPOINT,'coin':'BTC','duration_seconds':elapsed,'stop_reason':reason,
            'counts':dict(self.counts),'bytes':self.size,'max_bytes':self.max_bytes,
            'messages_sha256':digest(self.path),'recorder_sha256':digest(__file__),
            'boundaries':self.events,'errors':errors,'labels_computed':False,
            'clock_basis':'time.time_ns immediately after recv; paired with time.monotonic_ns',
            'payload_basis':'projected public messages; users/hash removed; not byte-exact raw feed',
            'limitations':['receipt includes network and local queue/buffering time',
                           'wall clock UTC synchronization is not independently attested',
                           'no exchange message sequence or completeness guarantee',
                           'never bridge segments in features or labels; warm up each segment',
                           'trade initial backlog remains event-timestamp filtered',
                           'no venue fills, account data, orders, model fit or trading result']}
        (self.root/'capture.json').write_text(json.dumps(receipt,indent=2)+'\n')
        return receipt


async def capture(output, seconds=60, max_bytes=64_000_000):
    if type(seconds) is not int or not 1<=seconds<=86400:
        raise ValueError('duration must be one second through one day')
    if type(max_bytes) is not int or not 1<=max_bytes<=1_000_000_000:
        raise ValueError('byte cap must be one byte through one GB')
    import certifi
    import websockets

    context=ssl.create_default_context(cafile=certifi.where())
    journal=Journal(output,max_bytes)
    start=time.monotonic()
    deadline=start+seconds
    errors=[]
    reason='duration_limit'
    try:
        while time.monotonic()<deadline:
            try:
                # Bound connect time as well as message receives by the requested duration.
                ws=await asyncio.wait_for(websockets.connect(
                    ENDPOINT,ssl=context,ping_interval=20,ping_timeout=20,
                    max_size=1_000_000,max_queue=32),deadline-time.monotonic())
                try:
                    journal.boundary('connection_open',time.time_ns(),time.monotonic_ns())
                    for channel in ('l2Book','trades'):
                        subscription={'type':channel,'coin':'BTC'}
                        if channel=='l2Book':
                            subscription['fast']=True  # Five levels, matching the model contract.
                        await asyncio.wait_for(ws.send(json.dumps({'method':'subscribe',
                            'subscription':subscription})),
                            max(.001,deadline-time.monotonic()))
                    while time.monotonic()<deadline:
                        text=await asyncio.wait_for(ws.recv(),deadline-time.monotonic())
                        wall=time.time_ns()
                        mono=time.monotonic_ns()
                        if not journal.append(text,wall,mono):
                            reason='byte_limit'
                            return journal.finish(reason,time.monotonic()-start,errors)
                finally:
                    await ws.close()
            except asyncio.TimeoutError:
                break
            except (OSError,websockets.exceptions.ConnectionClosed) as error:
                # Record class only. Error strings may contain URLs or remote text.
                errors.append({'type':type(error).__name__,'wall_ns':time.time_ns()})
                journal.boundary('connection_error',time.time_ns(),time.monotonic_ns())
                await asyncio.sleep(min(2,max(0,deadline-time.monotonic())))
    except BaseException:
        journal.finish('interrupted_or_failed',time.monotonic()-start,errors)
        raise
    return journal.finish(reason,time.monotonic()-start,errors)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--seconds',type=int,default=60)
    p.add_argument('--max-bytes',type=int,default=64_000_000)
    a=p.parse_args()
    receipt=asyncio.run(capture(a.output,a.seconds,a.max_bytes))
    print(json.dumps({k:receipt[k] for k in ['counts','bytes','duration_seconds','stop_reason']},indent=2))
