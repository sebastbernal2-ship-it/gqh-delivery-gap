"""Normalize pinned warehouse exports and French factors into quarantined daily panels."""
import argparse
import csv
import json
import math
from datetime import datetime, time, timezone
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo
from importlib.metadata import version
import exchange_calendars as xcals
from ..core import clock
from .french import FILES, digest, parse_daily

BATCHES = {
    'massive_bars': 'bec91f7c380937d3d647ade8214968c13abd4bde032c9a7cf7741f0ee58306cd',
    'massive_bars_unadjusted': '17c538dd38a3ff939e78ee074934637efca91518db02048410ed088be603ff6c',
    'massive_dividends': 'ac84b5535b5bb86ef32acbba49877aca87d3ccf204318d329c8fe64854322e76',
    'massive_splits': '07c65ecbfac427f5b32e79329c4a4557501950e9268444536571ce95b3d28480',
}
ASSETS = ('PWR', 'ETN', 'EME', 'DLR', 'SPY')
MAX_DEVELOPMENT_DATE = '2022-09-30'
NY = ZoneInfo('America/New_York')


def sessions(start, end):
    if not '2016-01-04' <= start < end <= MAX_DEVELOPMENT_DATE:
        raise ValueError('bounds must stay inside existing 2016-01-04..2022-09-30 development history')
    calendar = xcals.get_calendar('XNYS', start=start, end=end)
    return {s.date().isoformat(): calendar.session_close(s).to_pydatetime().isoformat()
            for s in calendar.sessions_in_range(start, end)}


def load_export(path):
    import hashlib
    records, loaded, identities = [], [], set()
    with Path(path).open(newline='') as stream:
        for r in csv.DictReader(stream):
            source, batch = r['SOURCE_ID'], r['BATCH_SHA256']
            if BATCHES.get(source) != batch:
                raise ValueError('unknown or unpinned source batch')
            key = (source, batch, r['ROW_INDEX'])
            if key in identities:
                raise ValueError('duplicate export row identity')
            identities.add(key)
            p = json.loads(r['PAYLOAD_JSON'])
            canonical = json.dumps(p, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
            if hashlib.sha256(canonical.encode()).hexdigest() != r['ROW_SHA256']:
                raise ValueError('payload row hash mismatch')
            loaded.append(clock(r['LOADED_AT']))
            records.append((source, p))
    if not records:
        raise ValueError('empty export')
    return records, max(loaded).isoformat()


def total_return(previous, current, distribution):
    p, c, d = map(lambda v: Decimal(str(v)), (previous, current, distribution))
    if not all(v.is_finite() for v in (p, c, d)) or p <= 0 or c <= 0 or d < 0:
        raise ValueError('invalid price/distribution')
    return float((c + d) / p - 1)


def normalize_prices(records, schedule, assets=ASSETS):
    """First version requires verified zero split receipts and matching raw/adjusted bars.

    Cash distributions accrue on ex-date. This is a research total-return convention,
    not actual cash reinvestment, pay-date cashflow or a taxes/borrow-aware P&L engine.
    """
    bars = {'massive_bars': {}, 'massive_bars_unadjusted': {}}
    dividends, split_coverage, dividend_ids = {}, set(), set()
    start, end = min(schedule), max(schedule)
    for source, p in records:
        asset = p.get('ticker')
        if asset not in assets:
            raise ValueError('unexpected asset in pinned export')
        if source in bars:
            stamp = clock(p['bar_time_utc']).astimezone(NY)
            day = stamp.date().isoformat()
            if stamp.timetz().replace(tzinfo=None) != time(0):
                raise ValueError('daily bar must carry the documented midnight ET bucket timestamp')
            if day not in schedule:
                raise ValueError('non-session or out-of-window bar')
            values = [float(p[k]) for k in ('open', 'high', 'low', 'close', 'volume')]
            o,h,l,c,v = values
            if not all(math.isfinite(x) for x in values) or min(o,h,l,c)<=0 or v<0 or h<max(o,c,l) or l>min(o,c,h):
                raise ValueError('invalid OHLCV')
            key = (asset, day)
            if key in bars[source]:
                raise ValueError('duplicate asset/session bar')
            bars[source][key] = p
        elif source == 'massive_splits':
            # A no-event receipt is evidence about the requested interval, not an actual split.
            if p.get('result_count') != 0 or p.get('requested_from','9999') > start or p.get('requested_to','0000') < end:
                raise ValueError('split history unsupported or receipt does not cover window')
            if asset in split_coverage:
                raise ValueError('duplicate split coverage receipt')
            split_coverage.add(asset)
        elif source == 'massive_dividends':
            day = p['ex_dividend_date']
            if day not in schedule:
                raise ValueError('non-session or out-of-window dividend')
            if p.get('currency') != 'USD' or not p.get('id'):
                raise ValueError('USD dividend with stable identity required')
            if p['id'] in dividend_ids:
                raise ValueError('duplicate dividend identity')
            dividend_ids.add(p['id'])
            amount = Decimal(str(p['cash_amount']))
            if not amount.is_finite() or amount < 0:
                raise ValueError('invalid dividend amount')
            key = (asset, day)
            dividends[key] = dividends.get(key, Decimal(0)) + amount
        else:
            raise ValueError('unknown source')
    expected = {(asset, day) for asset in assets for day in schedule}
    if split_coverage != set(assets):
        raise ValueError('missing no-split coverage receipt')
    for source in bars:
        if set(bars[source]) != expected:
            raise ValueError('missing sessions or incomplete export; never silently inner-join')
    for key in expected:
        for field in ('open','high','low','close'):
            a,b = (float(bars[source][key][field]) for source in bars)
            if not math.isclose(a,b,rel_tol=1e-8,abs_tol=1e-8):
                raise ValueError('adjusted/raw mismatch despite zero-split assumption')
    days = sorted(schedule)
    returns = {}
    for prev, day in zip(days, days[1:]):
        returns[day] = {asset: total_return(bars['massive_bars_unadjusted'][asset,prev]['close'],
                                         bars['massive_bars_unadjusted'][asset,day]['close'],
                                         dividends.get((asset,day),0)) for asset in assets}
    return returns, {'sessions':len(days),'return_rows':len(returns),'dividend_records':len(dividend_ids),
                     'assets':list(assets),'first_price_session':days[0],'first_return_session':days[1],
                     'last_return_session':days[-1],'return_convention':'cash-distribution-inclusive ex-date accrual; no splits in declared interval'}


def build(export, french_dir, output, start='2016-01-04', end=MAX_DEVELOPMENT_DATE):
    schedule = sessions(start,end)
    records, loaded = load_export(export)
    returns, qa = normalize_prices(records,schedule)
    directory = Path(french_dir)
    receipt = json.loads((directory/'receipt.json').read_text())
    factors = {}
    for kind, name in FILES.items():
        if digest(directory/name) != receipt['files'][kind]['sha256']:
            raise ValueError('French archive hash mismatch')
        factors[kind] = parse_daily((directory/name).read_bytes(),kind,start,end)
        if set(factors[kind]) != set(schedule):
            raise ValueError(f'{kind}: missing/extra exchange sessions')
    # RF and market must agree across separately downloaded constructions before comparisons.
    for day in schedule:
        for field in ('RF','Mkt-RF'):
            if factors['ff3'][day][field] != factors['ff5'][day][field]:
                raise ValueError('FF3/FF5 common market or RF vintage mismatch')
    available = max(clock(loaded),clock(receipt['retrieved_at'])).isoformat()
    manifest = {'window':{'price_start':start,'end':end},'study_role':'retrospective_only',
                'historical_availability_verified':False,'universe':'fixed five-name research basket; not survivorship-free',
                'export_sha256':digest(export),'french_receipt':receipt,'pinned_batches':BATCHES,
                'snapshot_available_at':available,'calendar':'XNYS',
                'runtime':{n:version(n) for n in ('exchange-calendars','numpy','pandas')},
                'qa':qa,'blocking_gates':['historical source/revision availability unverified',
                    'no promotion to strategy inputs or sealed evaluation',
                    'industry portfolios are research controls, not sector ETF execution instruments'],
                'code_sha256':{p.name:digest(p) for p in (Path(__file__),Path(__file__).with_name('french.py'))}}
    output=Path(output)
    output.mkdir(parents=True,exist_ok=False)
    for construction in ('ff3','ff5'):
        names=['MKT','SMB','HML']+(['RMW','CMA'] if construction=='ff5' else [])+['MOM']
        specs=[{'id':n,'canonical_id':n,'family':'market' if n=='MKT' else 'style',
                'economic_channel':n,'role':'return_factor','unit':'decimal_return',
                'source':f'French {construction} pinned snapshot; momentum separate'} for n in names]
        rows=[]
        for day, asset_returns in returns.items():
            f=factors[construction][day]; rf=f['RF']
            columns={('MKT' if k=='Mkt-RF' else k):v for k,v in f.items() if k!='RF'}
            columns['MOM']=factors['momentum'][day]['Mom']
            rows.append({'period_end':schedule[day],'available_at':available,
                         'excess_returns':{a:r-rf for a,r in asset_returns.items()},'factors':columns})
        panel={'study_role':'retrospective_only','currency':'USD','horizon':'daily_session_close_to_close',
               'source_version':digest(export)+':'+receipt['files'][construction]['sha256'],
               'assets':list(ASSETS),'factor_specs':specs,'rows':rows}
        (output/f'{construction}_panel.json').write_text(json.dumps(panel,allow_nan=False)+'\n')
    with (output/'industry12_controls.csv').open('w',newline='') as stream:
        names=list(factors['industry12'][next(iter(returns))])
        writer=csv.writer(stream);writer.writerow(['session','period_end','available_at',*names])
        for day in returns:
            rf=factors['ff3'][day]['RF']
            writer.writerow([day,schedule[day],available,*[factors['industry12'][day][n]-rf for n in names]])
    manifest['output_sha256']={p.name:digest(p) for p in sorted(output.iterdir())}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--export',required=True);p.add_argument('--french-dir',required=True)
    p.add_argument('--output',required=True);p.add_argument('--start',default='2016-01-04')
    p.add_argument('--end',default=MAX_DEVELOPMENT_DATE)
    a=p.parse_args();m=build(a.export,a.french_dir,a.output,a.start,a.end)
    print(json.dumps({'qa':m['qa'],'study_role':m['study_role'],'blocking_gates':m['blocking_gates']}))
