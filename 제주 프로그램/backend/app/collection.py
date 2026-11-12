"""Scheduled public-data collection; no user sales and no request-triggered network."""
import hashlib,json,time,uuid
from datetime import date,datetime
from urllib.parse import urlsplit
from .db import public_connect
from .hub import KEYS,Unavailable,DailyQuota,missing_details

class BudgetStop(Unavailable):pass

def init_collection():
    with public_connect() as c:c.executescript('''
CREATE TABLE IF NOT EXISTS collection_usage(day TEXT PRIMARY KEY,calls INTEGER NOT NULL,cap INTEGER NOT NULL,blocked INTEGER NOT NULL DEFAULT 0,message TEXT);
CREATE TABLE IF NOT EXISTS collection_pages(key TEXT PRIMARY KEY,body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS collection_jobs(key TEXT PRIMARY KEY,body TEXT NOT NULL,state TEXT NOT NULL,attempt_day TEXT,created_at TEXT NOT NULL,updated_at TEXT,last_error TEXT);
CREATE TABLE IF NOT EXISTS collection_lock(id INTEGER PRIMARY KEY CHECK(id=1),owner TEXT,expires REAL);
''')

def availability(dates,store):
    missing=missing_details(dates,store)
    blocked=False
    with public_connect() as c:
        if c.execute("SELECT 1 FROM sqlite_master WHERE name='collection_usage'").fetchone():
            row=c.execute('SELECT blocked FROM collection_usage WHERE day=?',(date.today().isoformat(),)).fetchone()
            blocked=bool(row and row[0])
    detail='공개 자료가 준비되어 있습니다.' if not missing else '선택한 범위의 공개 자료가 아직 준비되지 않았습니다. 자료 준비를 요청하면 정기 수집 때 확인합니다.'
    if missing and blocked:detail+=' 오늘은 제공처의 일일 한도로 추가 수집이 중지되어 있습니다.'
    return {'ready':not missing,'missing_sources':missing,'from':dates[0],'to':dates[-1],'detail':detail,'collection_blocked_today':blocked}

def enqueue(dates,store):
    init_collection()
    # Public selection only: never retain store name, industry, sales, or visitor ID.
    body={'dates':dates,'store':{'emd':store['emd'],'stops':sorted(store['stops'],key=lambda x:x['id'])}}
    encoded=json.dumps(body,ensure_ascii=False,sort_keys=True)
    key=hashlib.sha256(encoded.encode()).hexdigest()
    now=datetime.now().isoformat(timespec='seconds')
    with public_connect() as c:
        c.execute('BEGIN IMMEDIATE')
        existing=c.execute('SELECT state FROM collection_jobs WHERE key=?',(key,)).fetchone()
        if existing:return {'request_id':key,'state':existing['state']}
        if c.execute("SELECT count(*) FROM collection_jobs WHERE state!='complete'").fetchone()[0]>=100:
            raise Unavailable('자료 준비 요청이 많습니다. 나중에 다시 요청해 주세요.')
        c.execute('INSERT INTO collection_jobs VALUES (?,?,?,NULL,?,NULL,NULL)',(key,encoded,'pending',now))
    return {'request_id':key,'state':'pending'}

class Policy:
    def __init__(self,cap=100,day=None):
        if not 1<=cap<=1000:raise ValueError('호출 상한은 1~1000입니다.')
        self.cap=cap;self.day=day or date.today().isoformat();self.owner=uuid.uuid4().hex
        init_collection()

    def acquire(self):
        with public_connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute('SELECT * FROM collection_lock WHERE id=1').fetchone()
            if row and row['expires']>time.time():raise BudgetStop('다른 수집기가 실행 중입니다.')
            c.execute('INSERT OR REPLACE INTO collection_lock VALUES (1,?,?)',(self.owner,time.time()+120))

    def release(self):
        with public_connect() as c:c.execute('DELETE FROM collection_lock WHERE owner=?',(self.owner,))

    def key(self,url,params):
        resource=next((name for name,identifier in KEYS.items() if identifier in url),urlsplit(url).path)
        # Project keys occur in Hub URLs; only the resource name and non-secret parameters are hashed.
        safe={k:v for k,v in params.items() if k.casefold() not in ('servicekey','key','apikey')}
        return hashlib.sha256(json.dumps([resource,safe],sort_keys=True).encode()).hexdigest()

    def cached(self,url,params):
        with public_connect() as c:row=c.execute('SELECT body FROM collection_pages WHERE key=?',(self.key(url,params),)).fetchone()
        return json.loads(row[0]) if row else None

    def reserve(self):
        with public_connect() as c:
            c.execute('BEGIN IMMEDIATE')
            c.execute('INSERT OR IGNORE INTO collection_usage(day,calls,cap) VALUES (?,0,?)',(self.day,self.cap))
            row=c.execute('SELECT * FROM collection_usage WHERE day=?',(self.day,)).fetchone()
            if row['blocked']:raise DailyQuota('제공처 일일 조회 한도 초과로 오늘 수집을 중지했습니다.')
            cap=min(row['cap'],self.cap)
            if row['calls']>=cap:raise BudgetStop('오늘 설정한 수집 호출 상한에 도달했습니다.')
            c.execute('UPDATE collection_usage SET calls=calls+1,cap=? WHERE day=?',(cap,self.day))
            c.execute('UPDATE collection_lock SET expires=? WHERE owner=?',(time.time()+120,self.owner))

    def block(self,message):
        with public_connect() as c:
            c.execute('INSERT OR IGNORE INTO collection_usage(day,calls,cap) VALUES (?,0,?)',(self.day,self.cap))
            c.execute('UPDATE collection_usage SET blocked=1,message=? WHERE day=?',(message,self.day))

    def remember(self,url,params,payload):
        # Keep successful nonempty pages so a partial download can resume on a later run.
        response=payload.get('response') or {}
        body=response.get('body') if isinstance(response,dict) else None
        good=bool(payload.get('data')) if 'data' in payload else bool(isinstance(body,dict) and body.get('items'))
        if good:
            with public_connect() as c:c.execute('INSERT OR REPLACE INTO collection_pages VALUES (?,?)',(self.key(url,params),json.dumps(payload,ensure_ascii=False)))

    def status(self):
        with public_connect() as c:row=c.execute('SELECT day,calls,cap,blocked,message FROM collection_usage WHERE day=?',(self.day,)).fetchone()
        return dict(row) if row else {'day':self.day,'calls':0,'cap':self.cap,'blocked':0}
