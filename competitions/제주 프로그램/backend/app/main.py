import asyncio
import io
import json
import os
import sys
import zipfile
import secrets
import re
import shutil
import sqlite3
from urllib.parse import urlparse
from pathlib import Path
from datetime import date,datetime,timedelta
from contextlib import asynccontextmanager
import httpx
import pandas as pd
from fastapi import FastAPI,HTTPException,Request,UploadFile,File,Query
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,ConfigDict,Field,field_validator,model_validator
from .db import ROOT,ASSETS,RESOURCE,SETTINGS,connect,init,get_store,SESSION_DB,PUBLIC_DB,public_connect
from .compute import calendar,build_report
from .hub import report_input,Unavailable
from .collection import availability,enqueue
from .note import explain,classify,clean,INTENTS,percent,answer_question,unsupported_answer,question_facts

LOCKS={}
JOBS={}
def owner():return SESSION_DB.get() or os.getenv('WEEKLY_DB',str(ROOT/'data'/'app.db'))
def session_lock():return LOCKS.setdefault(owner(),asyncio.Lock())
def clear_finished_jobs():
    for key,job in list(JOBS.items()):
        if job['owner']==owner() and job['task'].done():del JOBS[key]
@asynccontextmanager
async def lifespan(app):
    if not os.getenv('DEMO_PUBLIC_ORIGIN'):init()
    try:yield
    finally:
        tasks=[j['task'] for j in JOBS.values() if not j['task'].done()]
        for task in tasks:task.cancel()
        if tasks:await asyncio.gather(*tasks,return_exceptions=True)
        JOBS.clear()
app=FastAPI(lifespan=lifespan,docs_url=None,redoc_url=None,openapi_url=None)
PORT=int(os.getenv('APP_PORT') or 8765)

@app.middleware('http')
async def local_only(request:Request,call_next):
    public=os.getenv('DEMO_PUBLIC_ORIGIN','').rstrip('/')
    hosts=(f'127.0.0.1:{PORT}',f'localhost:{PORT}','testserver')+((urlparse(public).netloc,) if public else ())
    if request.headers.get('host') not in hosts:return JSONResponse({'detail':'허용하지 않는 주소입니다.'},403)
    if request.method not in ('GET','HEAD') or request.url.path=='/api/report':
        if request.headers.get('origin') not in (None,f'http://127.0.0.1:{PORT}',f'http://localhost:{PORT}',public) or request.headers.get('x-weekly-client')!='1':return JSONResponse({'detail':'허용하지 않는 요청입니다.'},403)
    if request.method not in ('GET','HEAD'):
        parts=[];size=0
        async for chunk in request.stream():
            size+=len(chunk)
            if size>5_500_000:return JSONResponse({'detail':'파일은 5MB 이하입니다.'},413)
            parts.append(chunk)
        request._body=b''.join(parts)
    token=None;public_token=None;session=None
    if public:
        public_path=ROOT/'runtime'/'public-data.db'
        if not public_path.exists():
            shutil.copyfile(ROOT/'runtime'/'demo-seed.db',public_path)
            with connect(public_path) as c:
                for table in ('store','sales','report','meta'):c.execute('DELETE FROM '+table)
        public_token=PUBLIC_DB.set(str(public_path))
        directory=ROOT/'runtime'/'web-sessions';directory.mkdir(parents=True,exist_ok=True)
        session=request.cookies.get('weekly_session','')
        if not re.fullmatch(r'[a-f0-9]{64}',session) or not (directory/(session+'.db')).is_file():
            if sum(1 for _ in directory.glob('*.db'))>=100:
                PUBLIC_DB.reset(public_token)
                return JSONResponse({'detail':'데모 접속 공간이 가득 찼습니다.'},503)
            session=secrets.token_hex(32)
            session_path=directory/(session+'.db')
            shutil.copyfile(ROOT/'runtime'/'demo-seed.db',session_path)
            # Never initialize a visitor with another user's records or sample sales.
            fresh=sqlite3.connect(session_path)
            try:
                with fresh:
                    for table in ('store','sales','report','meta'):fresh.execute('DELETE FROM '+table)
            finally:fresh.close()
        token=SESSION_DB.set(str(directory/(session+'.db')))
    try:result=await call_next(request)
    finally:
        if token is not None:SESSION_DB.reset(token)
        if public_token is not None:PUBLIC_DB.reset(public_token)
    if session:result.set_cookie('weekly_session',session,httponly=True,secure=urlparse(public).scheme=='https' and request.headers.get('host')==urlparse(public).netloc,samesite='lax',max_age=86400)
    result.headers.update({'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'"})
    return result

def asset(name):return json.loads((RESOURCE/'data'/name).read_text(encoding='utf-8'))
def parse_date(value):
    try:
        d=date.fromisoformat(value)
        if d.isoformat()!=value:raise ValueError()
        return value
    except ValueError:raise HTTPException(422,'날짜는 YYYY-MM-DD 형식입니다.')

class Strict(BaseModel):model_config=ConfigDict(extra='forbid')
class Stop(Strict):
    id:str=Field(min_length=1,max_length=30)
    name:str=Field(min_length=1,max_length=100)
class Store(Strict):
    name:str=Field(default='',max_length=60)
    emd:str
    industry:str
    stops:list[Stop]=Field(min_length=1,max_length=3)
    @model_validator(mode='after')
    def check(self):
        known={r['id']:r['name'] for r in asset('stops.json')}
        if self.emd not in asset('emds.json') or self.industry not in ['음식점','카페','소매','기타']:raise ValueError('목록에서 동네·업종을 선택하세요.')
        if len({s.id for s in self.stops})!=len(self.stops) or any(known.get(s.id)!=s.name for s in self.stops):raise ValueError('목록의 정류소를 선택하세요.')
        if not clean(self.name):raise ValueError('가게 이름을 확인하세요.')
        return self
class Sale(Strict):
    date:str
    amount:int|None=Field(default=None,ge=0,le=100_000_000,strict=True)
    closed:bool=False
    @field_validator('date')
    @classmethod
    def check_date(cls,v):
        d=date.fromisoformat(v)
        if d.isoformat()!=v:raise ValueError('날짜 형식 오류')
        return v
class Sales(Strict):
    rows:list[Sale]=Field(min_length=1,max_length=3660)
    example:bool=False
    @model_validator(mode='after')
    def unique(self):
        if len({r.date for r in self.rows})!=len(self.rows):raise ValueError('날짜가 중복됩니다.')
        return self

@app.get('/api/status')
async def status():
    online=False
    with public_connect() as c:latest=c.execute('SELECT max(date) FROM island_bus').fetchone()[0]
    llm=False
    try:
        async with httpx.AsyncClient(timeout=1,trust_env=False) as c:
            r=await c.get('http://127.0.0.1:8766/health');llm=r.status_code==200
    except httpx.HTTPError:pass
    return dict(online=online,hub_key=bool(os.getenv('JEJU_HUB_KEY')),data_key=bool(os.getenv('DATA_GO_KR_KEY')),llm=llm,latest_hub_date=latest,demo=bool(os.getenv('DEMO_PUBLIC_ORIGIN')))

@app.get('/api/emds')
def emds():return asset('emds.json')
@app.get('/api/stops')
def stops(q:str=Query(default='',max_length=100)):
    term=q.strip().casefold()
    return [s for s in asset('stops.json') if term in s['name'].casefold() or term in s['id']][:30] if term else []
@app.get('/api/store',response_model=Store|None)
def store():return get_store()
@app.put('/api/store')
async def put_store(s:Store):
    async with session_lock():
        clear_finished_jobs()
        with connect() as c:
            c.execute('INSERT OR REPLACE INTO store VALUES (1,?,?,?,?)',(s.name,s.emd,s.industry,json.dumps([t.model_dump() for t in s.stops],ensure_ascii=False)))
            c.execute('DELETE FROM report')
    return s.model_dump()
@app.get('/api/sales')
def get_sales(start:str=Query(alias='from'),end:str=Query(alias='to')):
    parse_date(start);parse_date(end)
    with connect() as c:return [dict(r) for r in c.execute('SELECT * FROM sales WHERE date BETWEEN ? AND ? ORDER BY date',(start,end))]
@app.put('/api/sales')
async def put_sales(s:Sales):
    async with session_lock():
        clear_finished_jobs()
        with connect() as c:
            c.executemany('INSERT OR REPLACE INTO sales VALUES (?,?,?)',[(r.date,r.amount,int(r.closed)) for r in s.rows])
            c.execute('DELETE FROM report')
            c.execute("INSERT OR REPLACE INTO meta VALUES ('example',?)",('true' if s.example or os.getenv('DEMO_PUBLIC_ORIGIN') else 'false',))
    return {'saved':len(s.rows)}
@app.post('/api/sales/upload')
async def upload(file:UploadFile=File(...)):
    raw=await file.read(5_000_001)
    if len(raw)>5_000_000:raise HTTPException(413,'파일은 5MB 이하입니다.')
    try:
        suffix=Path(file.filename or '').suffix.lower()
        if suffix=='.csv':frame=pd.read_csv(io.BytesIO(raw),encoding='utf-8-sig',dtype=str,nrows=3661)
        elif suffix=='.xlsx':
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                if sum(i.file_size for i in z.infolist())>30_000_000:raise ValueError()
            frame=pd.read_excel(io.BytesIO(raw),dtype=str,nrows=3661)
        else:raise ValueError()
        frame=frame.rename(columns={'날짜':'date','매출':'amount','휴무':'closed'})
        if not {'date','amount'}.issubset(frame.columns):raise ValueError()
        rows=[]
        for r in frame.to_dict('records'):
            d=str(r['date'])[:10];v=r['amount']
            amount=None if pd.isna(v) or str(v).strip()=='' else float(str(v).replace(',',''))
            if amount is not None and (not amount.is_integer() or not 0<=amount<=100_000_000):raise ValueError()
            closed=str(r.get('closed','')).lower() in ('1','true','휴무','y')
            rows.append({'date':d,'amount':int(amount) if amount is not None else None,'closed':closed})
        validated=Sales(rows=rows)
        example_name=Path(file.filename or '').name
        return {'rows':[r.model_dump() for r in validated.rows],'saved':False,'example':example_name=='example-sales.csv' or (example_name.startswith('example-sales-') and example_name.endswith('.csv'))}
    except Exception:raise HTTPException(422,'날짜·매출 열과 중복 날짜, 금액을 확인하세요.') from None

@app.get('/api/report')
async def report(week_start:str):
    try:dates=calendar(week_start)
    except ValueError:raise HTTPException(422,'대상 주의 월요일을 선택하세요.')
    if date.fromisoformat(dates[-1])>=date.today():raise HTTPException(422,'지난 주까지 선택할 수 있습니다.')
    async with session_lock():
        s=get_store()
        if not s:raise HTTPException(409,'가게를 먼저 등록하세요.')
        require_sales(dates)
        state=availability(dates,s)
        if not state['ready']:return JSONResponse({'detail':state['detail'],'missing_sources':state['missing_sources']},409)
        errors=[]
        data=report_input(week_start,dates,s)
        result=build_report(data,SETTINGS);result['note']=await explain(result);result['sources_status']=errors
        with connect() as c:c.execute('INSERT OR REPLACE INTO report VALUES (?,?,?)',(week_start,json.dumps(result,ensure_ascii=False),datetime.now().isoformat()))
        return result

class ReportJobRequest(Strict):
    week_start:str

@app.get('/api/data-availability')
def data_availability(week_start:str):
    try:dates=calendar(week_start)
    except ValueError:raise HTTPException(422,'대상 주의 월요일을 선택하세요.')
    s=get_store()
    if not s:raise HTTPException(409,'가게를 먼저 등록하세요.')
    return availability(dates,s)

@app.post('/api/data-requests')
def request_data(q:ReportJobRequest):
    try:dates=calendar(q.week_start)
    except ValueError:raise HTTPException(422,'대상 주의 월요일을 선택하세요.')
    if date.fromisoformat(dates[-1])>=date.today():raise HTTPException(422,'지난 주까지 선택할 수 있습니다.')
    if date.fromisoformat(dates[0])<date.today()-timedelta(days=366):raise HTTPException(422,'자료 준비 요청은 최근 1년 범위에서 가능합니다.')
    s=get_store()
    if not s:raise HTTPException(409,'가게를 먼저 등록하세요.')
    state=availability(dates,s)
    if state['ready']:return {'state':'complete','detail':'공개 자료가 준비되어 있습니다.'}
    try:result=enqueue(dates,s)
    except Unavailable as error:raise HTTPException(429,str(error))
    return {**result,'detail':'자료 준비를 요청했습니다. 정기 수집 후 다시 확인해 주세요. 제공처 한도와 자료 유무에 따라 완료 시점은 달라질 수 있습니다.'}

def require_sales(dates):
    with connect() as c:
        for start,end in ((dates[0],dates[27]),(dates[28],dates[-1])):
            if not c.execute('SELECT 1 FROM sales WHERE date BETWEEN ? AND ? AND amount IS NOT NULL AND closed=0 LIMIT 1',(start,end)).fetchone():
                raise HTTPException(422,'결산 대상 주와 기준 4주에 매출을 입력해 주세요. 0원도 입력한 매출로 인정합니다.')

@app.post('/api/report-jobs',status_code=202)
async def start_report_job(q:ReportJobRequest):
    try:dates=calendar(q.week_start)
    except ValueError:raise HTTPException(422,'대상 주의 월요일을 선택하세요.')
    if date.fromisoformat(dates[-1])>=date.today():raise HTTPException(422,'지난 주까지 선택할 수 있습니다.')
    if not get_store():raise HTTPException(409,'가게를 먼저 등록하세요.')
    require_sales(dates)
    state=availability(dates,get_store())
    if not state['ready']:raise HTTPException(409,state['detail'])
    current=owner()
    for key,job in list(JOBS.items()):
        if job['owner']!=current:continue
        if not job['task'].done():
            if job['week_start']!=q.week_start:raise HTTPException(409,'진행 중인 결산이 끝난 뒤 다른 주를 선택해 주세요.')
            return {'job_id':key,'state':job['state']}
        del JOBS[key]
    if sum(not j['task'].done() for j in JOBS.values())>=16:raise HTTPException(429,'결산 요청이 많습니다. 잠시 후 다시 눌러 주세요.')
    if len(JOBS)>=128:
        for key,job in list(JOBS.items()):
            if job['task'].done():del JOBS[key]
    key=secrets.token_hex(24)
    job={'owner':current,'week_start':q.week_start,'state':'processing'}
    async def run():
        try:
            result=await report(q.week_start)
            if isinstance(result,JSONResponse):
                job.update(state='failed',detail=json.loads(result.body).get('detail','자료를 확인하지 못했습니다.'))
            else:job.update(state='complete',result=result)
        except HTTPException as error:job.update(state='failed',detail=error.detail)
        except asyncio.CancelledError:
            if job['state']!='cancelled':job.update(state='failed',detail='서버가 재시작되었습니다. 받은 자료는 남아 있으니 다시 결산해 주세요.')
            raise
        except Exception:job.update(state='failed',detail='결산 중 오류가 발생했습니다. 받은 자료는 남아 있으니 다시 결산해 주세요.')
    job['task']=asyncio.create_task(run());JOBS[key]=job
    return {'job_id':key,'state':'processing'}

@app.get('/api/report-jobs/{job_id}')
def report_job(job_id:str):
    job=JOBS.get(job_id)
    if not job or job['owner']!=owner():raise HTTPException(404,'결산 작업을 찾을 수 없습니다. 다시 결산해 주세요.')
    return {k:v for k,v in job.items() if k not in ('owner','task')}

@app.delete('/api/report-jobs/{job_id}')
async def cancel_report_job(job_id:str):
    job=JOBS.get(job_id)
    if not job or job['owner']!=owner():raise HTTPException(404,'결산 작업을 찾을 수 없습니다.')
    if not job['task'].done():
        job['state']='cancelled';job['task'].cancel()
        await asyncio.gather(job['task'],return_exceptions=True)
    return {'state':job['state']}

@app.get('/api/history')
def history():
    with connect() as c:rows=[json.loads(r['body']) for r in c.execute('SELECT body FROM report ORDER BY week_start DESC LIMIT 8')]
    return [{'week_start':r['week_start'],'verdict':r['verdict_text'],'store':r['indicators'][0]['change'],'neighborhood':r['neighborhood']} for r in rows]

class Ask(Strict):
    week_start:str
    question:str|None=Field(default=None,max_length=500)
    intent:str|None=None
    dow:str|None=None
@app.post('/api/ask')
async def ask(q:Ask):
    with connect() as c:row=c.execute('SELECT body FROM report WHERE week_start=?',(q.week_start,)).fetchone()
    if not row:raise HTTPException(409,'결산을 먼저 만들어 주세요.')
    r=json.loads(row['body']);intent=q.intent;dow=q.dow;by='template';selected_days=[]
    if q.question:
        parsed=await classify(q.question)
        if not parsed.get('intent'):return unsupported_answer()
        generated=await answer_question(r,q.question)
        if generated:return generated
        intent=parsed.get('intent');dow=parsed.get('dow');selected_days=parsed.get('days',[]);by=parsed.get('by','template')
        if intent=='summary':
            facts=question_facts(r)
            return {'intent':intent,'answer':facts['summary']+'\n'+facts['limit'],'by':'template','notice':'AI 답변을 확인하지 못해 계산된 결과를 표시했습니다.'}
    if intent not in INTENTS or (dow is not None and dow not in list('월화수목금토일')):return unsupported_answer()
    if intent in ('day_detail','rain'):
        days=[d for d in r['days'] if (intent=='rain' and d['rain_mm'] is not None and d['rain_mm']>=1) or (intent=='day_detail' and (not dow or d['dow']==dow) and (not selected_days or d['dow'] in selected_days))]
        answer='\n'.join(f"{d['date']}({d['dow']}요일): 기준 4주의 같은 요일과 비교해 가게 매출 {percent(d['store'])}, 동네 지표 {percent(d['area'])}입니다. 강수량 {str(d['rain_mm'])+'mm' if d['rain_mm'] is not None else '자료 없음'}, 공휴일 {d['holiday'] or '등록 없음'}. {'비교에서 제외한 날입니다.' if d.get('excluded') else '확인할 날로 표시됐습니다.' if d['flag'] else ''}" for d in days) or ('비 자료를 확인하지 못했습니다.' if intent=='rain' and all(d['rain_mm'] is None for d in r['days']) else '해당하는 날이 없습니다.')
    elif intent=='island':answer='제주 전체 버스 승차는 '+percent(r['indicators'][3]['change'])+' 변했습니다. 가게 매출과 서로 다른 지표입니다.'
    elif intent=='excluded':answer='\n'.join(d['date']+' '+d['reason'] for d in r['excluded']) or '뺀 날이 없습니다.'
    elif intent=='sources':answer='\n'.join(s['name']+' '+s['range']+' / '+s['fetched_at'] for s in r['sources'])
    else:answer='\n'.join(h['week_start']+' '+h['verdict'] for h in history()) or '저장된 결산이 없습니다.'
    return {'intent':intent,'answer':answer,'by':by}

@app.delete('/api/my-data')
async def delete_data():
    async with session_lock():
        clear_finished_jobs()
        with connect() as c:
            for table in ('store','sales','report'):c.execute('DELETE FROM '+table)
            c.execute("DELETE FROM meta WHERE key='example'")
    return {'deleted':True}

dist=ASSETS/'frontend'/'dist'
if dist.exists():app.mount('/',StaticFiles(directory=dist,html=True),name='frontend')
