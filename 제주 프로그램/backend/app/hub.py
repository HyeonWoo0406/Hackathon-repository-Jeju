"""Approved public endpoints only. Never log credential-bearing request URLs."""
import asyncio
from datetime import date,datetime,timedelta
from collections import defaultdict
from contextlib import asynccontextmanager
from contextvars import ContextVar
import os
from urllib.parse import unquote
import httpx
from .db import connect,public_connect,SETTINGS
from .compute import boarding_total,wifi_totals

KEYS={'stop_bus':'1b1ta1a1ba6t6a1ttt3bD6b1tb1t1D3t','wifi':'7tttaDaD5ataaba75a57ttDtaDb6tb7t','island_bus':'617bt7b7ttb1Datab7a7ttD6tbt7611t'}
NAMES={'stop_bus':'제주데이터허브 일일 정류소별 버스 이용자','wifi':'제주데이터허브 읍면동별 와이파이 사용량','island_bus':'제주데이터허브 버스 일일 승객수','weather':'기상청 ASOS 일자료','holiday':'한국천문연구원 특일 정보'}
class Unavailable(Exception):pass
class DailyQuota(Unavailable):pass
QUOTA_DAY={}
CLIENT=ContextVar('hub_client',default=None)
FETCH_LOCK=asyncio.Lock()
REQUEST_POLICY=ContextVar('request_policy',default=None)

@asynccontextmanager
async def client_scope():
    if CLIENT.get() is not None:yield CLIENT.get()
    else:
        async with httpx.AsyncClient(timeout=20,trust_env=False) as client:yield client

async def request_json(client,url,params):
    for attempt in range(4):
        try:
            policy=REQUEST_POLICY.get()
            if policy is None:raise Unavailable('공개 자료 조회는 호출 상한이 적용된 정기 수집기에서만 실행합니다.')
            if policy:
                cached=policy.cached(url,params)
                if cached is not None:return cached
                policy.reserve()
            r=await client.get(url,params=params)
            if r.status_code in (403,429) and ('quota' in r.text.casefold() or '일일' in r.text):
                if policy:policy.block('제공처의 일일 조회 한도 초과')
                raise DailyQuota('공개 API의 일일 조회 한도를 모두 사용했습니다. 권한 부족이 아닙니다. 저장되지 않은 자료는 제공처의 한도가 복구된 뒤 조회할 수 있습니다.')
            if r.status_code==429:raise Unavailable('공개 API 요청이 몰려 일시적으로 제한되었습니다. 잠시 후 다시 시도해 주세요.')
            if r.status_code in (401,403):raise Unavailable('자료 사용 권한 확인 필요')
            r.raise_for_status();j=r.json()
            if not isinstance(j,dict):raise ValueError()
            if policy:policy.remember(url,params,j)
            return j
        except (httpx.HTTPError,ValueError):
            if attempt==3:raise Unavailable('자료를 받지 못했습니다.') from None
            await asyncio.sleep(attempt+1)

async def hub_rows(source,params):
    if QUOTA_DAY.get(source)==date.today():
        raise DailyQuota('공개 API의 일일 조회 한도를 모두 사용했습니다. 저장된 자료만 사용할 수 있습니다.')
    key=os.getenv('JEJU_HUB_KEY','')
    if not key:raise Unavailable('허브 키 없음')
    rows=[]
    async with client_scope() as client:
        for page in range(1,1001):
            try:j=await request_json(client,f'https://open.jejudatahub.net/api/proxy/{KEYS[source]}/{key}',{**params,'limit':100,'number':page})
            except DailyQuota:
                QUOTA_DAY[source]=date.today()
                raise
            if not isinstance(j.get('data'),list):raise Unavailable('자료 응답 형식 확인 필요')
            rows.extend(j['data'])
            if not j.get('hasMore',False):
                if 'totCnt' in j and int(j['totCnt'])!=len(rows):raise Unavailable('전체 행 수와 받은 행 수가 다릅니다.')
                return rows
            if not j['data']:raise Unavailable('페이지 자료가 비어 있습니다.')
    raise Unavailable('자료 페이지 범위를 넘었습니다.')

def iso(value):
    s=str(value).split('T')[0].replace('-','')[:8]
    return datetime.strptime(s,'%Y%m%d').date().isoformat()

def count(value):
    v=int(str(value).replace(',',''))
    if v<0:raise Unavailable('자료 숫자 형식 확인 필요')
    return v

def recorded(source,key,d):
    with public_connect() as c:return bool(c.execute('SELECT 1 FROM fetch_log WHERE source=? AND key=? AND date=?',(source,key,d)).fetchone())

def stamp(c,source,key,d,n):
    c.execute('INSERT OR REPLACE INTO fetch_log VALUES (?,?,?,?,?)',(source,key,d,n,datetime.now().isoformat(timespec='seconds')))

async def fetch_island(d):
    if recorded('island_bus','all',d):return True
    rows=await hub_rows('island_bus',{'startDate':d.replace('-',''),'endDate':d.replace('-','')})
    rows=[r for r in rows if iso(r['baseDate'])==d]
    if not rows:return False
    n=boarding_total(rows)
    with public_connect() as c:
        c.execute('INSERT OR REPLACE INTO island_bus VALUES (?,?)',(d,n));stamp(c,'island_bus','all',d,len(rows))
    return True

async def fetch_stop(d,stop):
    if recorded('stop_bus',stop['id'],d):return
    rows=await hub_rows('stop_bus',{'startDate':d.replace('-',''),'endDate':d.replace('-',''),'stationName':stop['name']})
    rows=[r for r in rows if iso(r['baseDate'])==d and str(r['stationId'])==stop['id']]
    if not rows and not recorded('island_bus','all',d):return
    total=boarding_total(rows)
    with public_connect() as c:
        c.execute('INSERT OR REPLACE INTO stop_bus VALUES (?,?,?)',(d,stop['id'],total));stamp(c,'stop_bus',stop['id'],d,len(rows))

async def fetch_wifi(d,emd):
    if recorded('wifi',emd,d):return
    rows=await hub_rows('wifi',{'searchDate':d.replace('-',''),'emd':emd})
    rows=[r for r in rows if iso(r['baseDate'])==d and r['emd']==emd]
    if not rows:return
    groups=wifi_totals(rows)
    with public_connect() as c:
        c.execute('DELETE FROM wifi WHERE date=? AND emd=?',(d,emd))
        c.executemany('INSERT INTO wifi VALUES (?,?,?,?)',[(d,emd,k,v) for k,v in groups.items()]);stamp(c,'wifi',emd,d,len(rows))

async def fetch_weather(start,end,stn):
    key=os.getenv('DATA_GO_KR_KEY','')
    with public_connect() as c:
        n=c.execute('SELECT count(*) FROM weather WHERE stn=? AND date BETWEEN ? AND ?',(stn,start,end)).fetchone()[0]
    if n==(date.fromisoformat(end)-date.fromisoformat(start)).days+1:return
    if not key:raise Unavailable('날씨 API 키가 설정되지 않았습니다.')
    async with client_scope() as client:
        j=await request_json(client,'https://apis.data.go.kr/1360000/AsosDalyInfoService/getWthrDataList',dict(serviceKey=unquote(key),numOfRows=60,pageNo=1,dataType='JSON',dataCd='ASOS',dateCd='DAY',startDt=start.replace('-',''),endDt=end.replace('-',''),stnIds=stn))
    try:items=j['response']['body']['items']['item']
    except (KeyError,TypeError):raise Unavailable('날씨 응답 확인 필요') from None
    if isinstance(items,dict):items=[items]
    with public_connect() as c:
        for r in items:
            d=iso(r['tm']);rain=float(r.get('sumRn') or 0);wind=float(r['maxWs']) if r.get('maxWs') not in ('',None) else None
            c.execute('INSERT OR REPLACE INTO weather VALUES (?,?,?,?)',(d,stn,rain,wind));stamp(c,'weather',str(stn),d,1)

async def fetch_holidays(year,month):
    key=os.getenv('DATA_GO_KR_KEY','');period=f'{year}-{month:02}'
    if year in SETTINGS.get('holiday_years',[]) or recorded('holiday',period,period+'-01'):return
    if not key:raise Unavailable('공휴일 API 키가 설정되지 않았습니다.')
    async with client_scope() as client:
        j=await request_json(client,'https://apis.data.go.kr/B090041/openapi/service/SpcdeInfoService/getRestDeInfo',dict(serviceKey=unquote(key),solYear=year,solMonth=f'{month:02}',_type='json',numOfRows=100))
    try:body=j['response']['body'];items=body.get('items') or {};rows=items.get('item',[]) if isinstance(items,dict) else []
    except (KeyError,TypeError):raise Unavailable('공휴일 응답 확인 필요') from None
    if isinstance(rows,dict):rows=[rows]
    with public_connect() as c:
        for r in rows:
            if r.get('isHoliday')=='Y':c.execute('INSERT OR REPLACE INTO holiday VALUES (?,?)',(iso(r['locdate']),r['dateName']))
        stamp(c,'holiday',period,period+'-01',len(rows))

async def ensure(dates,store):
    errors=set()
    slots=asyncio.Semaphore(4)
    async def attempt(label,fn,*args):
        try:await fn(*args)
        except Unavailable as e:errors.add(label+': '+str(e))
        except (ValueError,KeyError,TypeError):errors.add(label+': 제공 자료의 형식을 확인할 수 없습니다.')
    async def day(d):
        async with slots:
            await attempt('제주 전체 버스',fetch_island,d)
            for stop in store['stops']:
                await attempt('정류소 '+stop['name']+' ('+stop['id']+')',fetch_stop,d,stop)
            await attempt(store['emd']+' 와이파이',fetch_wifi,d,store['emd'])
    stn=SETTINGS['asos_station'].get(store['emd'],184)
    async def collect():
        await asyncio.gather(*(day(d) for d in dates))
        await attempt('날씨',fetch_weather,dates[0],dates[-1],stn)
        for month in sorted({d[:7] for d in dates}):
            await attempt('공휴일',fetch_holidays,int(month[:4]),int(month[5:]))
    async with FETCH_LOCK:
        async with httpx.AsyncClient(timeout=20,trust_env=False) as client:
            token=CLIENT.set(client)
            try:await collect()
            finally:CLIENT.reset(token)
    return sorted(errors)

def missing_details(dates,store):
    """Name the actual missing source and selection, never assume publication delay."""
    missing=[]
    with public_connect() as c:
        for label,table,where,args in [
            ('제주 전체 버스','island_bus','',()),
            (store['emd']+' 와이파이','fetch_log'," AND source='wifi' AND key=?",(store['emd'],)),
            *[(s['name']+' ('+s['id']+') 버스','stop_bus',' AND station_id=?',(s['id'],)) for s in store['stops']]
        ]:
            found={r[0] for r in c.execute('SELECT date FROM '+table+' WHERE date BETWEEN ? AND ?'+where,(dates[0],dates[-1],*args))}
            absent=[d for d in dates if d not in found]
            if absent:missing.append({'source':label,'dates':absent})
    return missing

def report_input(week_start,dates,store):
    with connect() as c:
        sales={r['date']:dict(r) for r in c.execute('SELECT * FROM sales WHERE date BETWEEN ? AND ?',(dates[0],dates[-1]))}
        example=c.execute("SELECT value FROM meta WHERE key='example'").fetchone()
    with public_connect() as c:
        island={r['date']:r['boardings'] for r in c.execute('SELECT * FROM island_bus WHERE date BETWEEN ? AND ?',(dates[0],dates[-1]))}
        bus={};wifi={}
        for d in dates:
            ids=[s['id'] for s in store['stops']]
            rows=list(c.execute('SELECT * FROM stop_bus WHERE date=? AND station_id IN ('+','.join('?' for _ in ids)+')',[d,*ids]))
            if len(rows)==len(ids):bus[d]=sum(r['boardings'] for r in rows)
            if c.execute('SELECT 1 FROM fetch_log WHERE source=? AND key=? AND date=?',('wifi',store['emd'],d)).fetchone():
                wifi[d]=sum(r['users'] for r in c.execute('SELECT * FROM wifi WHERE date=? AND emd=?',(d,store['emd'])) if r['category'] in SETTINGS['visit_categories'])
        stn=SETTINGS['asos_station'].get(store['emd'],184)
        weather={r['date']:dict(r) for r in c.execute('SELECT * FROM weather WHERE stn=? AND date BETWEEN ? AND ?',(stn,dates[0],dates[-1]))}
        holidays={r['date']:r['name'] for r in c.execute('SELECT * FROM holiday WHERE date BETWEEN ? AND ?',(dates[0],dates[-1]))}
        known=[d for d in dates if int(d[:4]) in SETTINGS.get('holiday_years',[]) or c.execute("SELECT 1 FROM fetch_log WHERE source='holiday' AND key=?",(d[:7],)).fetchone()]
        for d in dates:
            if d not in known and d not in holidays:holidays[d]='자료 확인 필요'
        sources=[{'name':NAMES[r['source']],'range':f'{dates[0]}~{dates[-1]}','fetched_at':r['fetched_at']} for r in c.execute('SELECT source,max(fetched_at) fetched_at FROM fetch_log WHERE date BETWEEN ? AND ? GROUP BY source',(dates[0],dates[-1]))]
    if any(int(d[:4]) in SETTINGS.get('holiday_years',[]) for d in dates):sources.append({'name':'공휴일 확인 목록 (천문연구원·정부 발표)','range':f'{dates[0]}~{dates[-1]}','fetched_at':'2026-11-12'})
    return dict(week_start=week_start,store=store,sales=sales,series={'island_bus':island,'stop_bus':bus,'wifi_visit':wifi},weather=weather,holidays=holidays,holiday_known=known,sources=sources,example=bool(example and example[0]=='true'))
