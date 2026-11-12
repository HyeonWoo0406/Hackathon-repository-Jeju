import asyncio,json
from fastapi.testclient import TestClient
from backend.app import main,hub
from backend.app.db import init,connect,SESSION_DB,RESOURCE
from backend.tests.test_compute import sample

def test_public_report_uses_cache_only_and_rejects_unprepared_selections(tmp_path,monkeypatch):
    runtime=tmp_path/'runtime';runtime.mkdir()
    token=SESSION_DB.set(str(runtime/'demo-seed.db'))
    try:init()
    finally:SESSION_DB.reset(token)
    monkeypatch.setattr(main,'ROOT',tmp_path)
    monkeypatch.setenv('DEMO_PUBLIC_ORIGIN','https://demo.example')
    async def collect(*args,**kwargs):raise AssertionError('Web reports must never call public APIs')
    async def explain(r):return {'text':'검증','by':'template'}
    monkeypatch.setattr(hub,'ensure',collect)
    monkeypatch.setattr(hub,'request_json',collect)
    state={'ready':True,'detail':'준비 완료','missing_sources':[]}
    monkeypatch.setattr(main,'availability',lambda *args:state)
    monkeypatch.setattr(main,'explain',explain)
    data=sample()
    monkeypatch.setattr(main,'report_input',lambda *args:data)
    stops=json.loads((RESOURCE/'data/stops.json').read_text(encoding='utf-8'))
    store={'name':'검증 가게','emd':'조천읍','industry':'카페','stops':[s for s in stops if s['id']=='0000192']}
    headers={'X-Weekly-Client':'1','Origin':'https://demo.example'}
    with TestClient(main.app,base_url='https://demo.example') as client:
        assert client.put('/api/store',headers=headers,json=store).status_code==200
        client.put('/api/sales',headers=headers,json={'rows':[{'date':'2026-10-05','amount':100},{'date':'2026-11-02','amount':100}]})
        response=client.get('/api/report?week_start=2026-11-02',headers=headers)
        assert response.status_code==200
        assert client.get('/api/data-availability?week_start=2026-11-02').json()['ready']
        state.update(ready=False,detail='공개 자료가 아직 준비되지 않았습니다.',missing_sources=[{'source':'조천읍 와이파이','dates':['2026-11-02']}])
        assert not client.get('/api/data-availability?week_start=2026-11-02').json()['ready']
        assert client.post('/api/report-jobs',headers=headers,json={'week_start':'2026-11-02'}).status_code==409
        response=client.get('/api/report?week_start=2026-11-02',headers=headers)
        assert response.status_code==409
        body=response.json()
        assert 'ready_on' not in body and '기다려' not in body['detail']
        assert any(x['source']=='조천읍 와이파이' for x in body['missing_sources'])
        assert '준비되지' in body['detail']

def test_collection_keeps_successful_days_when_one_source_fails(monkeypatch):
    visited=[]
    async def island(d):visited.append(('island',d))
    async def stop(d,s):visited.append((s['id'],d))
    async def wifi(d,e):raise hub.Unavailable('자료 사용 권한 확인 필요')
    async def other(*args):pass
    monkeypatch.setattr(hub,'fetch_island',island)
    monkeypatch.setattr(hub,'fetch_stop',stop)
    monkeypatch.setattr(hub,'fetch_wifi',wifi)
    monkeypatch.setattr(hub,'fetch_weather',other)
    monkeypatch.setattr(hub,'fetch_holidays',other)
    days=['2026-11-02','2026-11-03']
    errors=asyncio.run(hub.ensure(days,{'emd':'조천읍','stops':[{'id':'x','name':'검증 정류소'}]}))
    assert len(visited)==4
    assert errors==['조천읍 와이파이: 자료 사용 권한 확인 필요']
