import asyncio,json
from fastapi.testclient import TestClient
from backend.app import main,hub
from backend.app.db import SESSION_DB,PUBLIC_DB,init,connect,public_connect,RESOURCE

def test_background_jobs_are_nonblocking_owned_and_shared_cache_has_no_sales(tmp_path,monkeypatch):
    runtime=tmp_path/'runtime';runtime.mkdir()
    token=SESSION_DB.set(str(runtime/'demo-seed.db'))
    try:init()
    finally:SESSION_DB.reset(token)
    monkeypatch.setattr(main,'ROOT',tmp_path)
    monkeypatch.setenv('DEMO_PUBLIC_ORIGIN','https://demo.example')
    gate=asyncio.Event();started=asyncio.Event();owners=[]
    async def slow_report(week):
        owners.append(SESSION_DB.get());started.set();await gate.wait()
        with connect() as c:
            name=c.execute('SELECT name FROM store').fetchone()[0]
            c.execute('INSERT OR REPLACE INTO sales VALUES (?,123,0)',('2026-11-02',))
        with public_connect() as c:c.execute('INSERT OR REPLACE INTO island_bus VALUES (?,456)',('2026-11-02',))
        return {'name':name,'week_start':week}
    monkeypatch.setattr(main,'report',slow_report)
    monkeypatch.setattr(main,'availability',lambda *args:{'ready':True})
    stops=json.loads((RESOURCE/'data/stops.json').read_text(encoding='utf-8'))
    store={'name':'첫 가게','emd':'애월읍','industry':'카페','stops':[s for s in stops if s['id']=='0003291']}
    headers={'X-Weekly-Client':'1','Origin':'https://demo.example'}
    with TestClient(main.app,base_url='https://demo.example') as client:
        client.put('/api/store',headers=headers,json=store)
        assert client.post('/api/report-jobs',headers=headers,json={'week_start':'2026-11-02'}).status_code==422
        client.put('/api/sales',headers=headers,json={'rows':[{'date':'2026-10-05','amount':0},{'date':'2026-11-02','amount':0}]})
        first_cookie=client.cookies.get('weekly_session')
        response=client.post('/api/report-jobs',headers=headers,json={'week_start':'2026-11-02'})
        assert response.status_code==202
        key=response.json()['job_id'];client.portal.call(started.wait)
        assert client.get('/api/report-jobs/'+key).json()['state']=='processing'
        assert client.post('/api/report-jobs',headers=headers,json={'week_start':'2026-11-02'}).json()['job_id']==key
        client.cookies.clear()
        assert client.get('/api/report-jobs/'+key).status_code==404
        assert client.get('/api/store').json() is None
        second_cookie=client.cookies.get('weekly_session')
        client.portal.call(gate.set)
        async def finished():await main.JOBS[key]['task']
        client.portal.call(finished)
        assert client.get('/api/sales?from=2026-11-02&to=2026-11-02').json()==[]
        with connect(runtime/'public-data.db') as c:
            assert c.execute('SELECT count(*) FROM sales').fetchone()[0]==0
            assert c.execute('SELECT boardings FROM island_bus').fetchone()[0]==456
        client.cookies.clear();client.cookies.set('weekly_session',first_cookie,domain='demo.example',path='/')
        result=client.get('/api/report-jobs/'+key).json()
        assert result['state']=='complete' and result['result']['name']=='첫 가게'
        assert len(owners)==1 and first_cookie!=second_cookie
        gate.clear();started.clear()
        second=client.post('/api/report-jobs',headers=headers,json={'week_start':'2026-11-02'}).json()['job_id']
        client.portal.call(started.wait)
        assert client.delete('/api/report-jobs/'+second,headers=headers).json()['state']=='cancelled'
        assert client.get('/api/report-jobs/'+second).json()['state']=='cancelled'
        assert len(client.get('/api/sales?from=2026-10-05&to=2026-11-02').json())==2

def test_public_cache_is_reused_without_network_across_visitors(tmp_path,monkeypatch):
    shared=tmp_path/'public.db';one=tmp_path/'one.db';two=tmp_path/'two.db'
    for path in (shared,one,two):
        token=SESSION_DB.set(str(path))
        try:init()
        finally:SESSION_DB.reset(token)
    with connect(shared) as c:
        c.execute('INSERT INTO island_bus VALUES (?,456)',('2026-11-02',))
        hub.stamp(c,'island_bus','all','2026-11-02',1)
    async def unexpected(*args):raise AssertionError('cached data must not be fetched again')
    monkeypatch.setattr(hub,'hub_rows',unexpected)
    public_token=PUBLIC_DB.set(str(shared))
    try:
        for path in (one,two):
            token=SESSION_DB.set(str(path))
            try:assert asyncio.run(hub.fetch_island('2026-11-02'))
            finally:SESSION_DB.reset(token)
    finally:PUBLIC_DB.reset(public_token)
