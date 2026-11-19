import csv,json
from fastapi.testclient import TestClient
from backend.app import main
from backend.app.db import ROOT,RESOURCE,SESSION_DB,init,connect

def test_full_app_sessions_preserve_all_routes(tmp_path,monkeypatch):
    runtime=tmp_path/'runtime';runtime.mkdir()
    token=SESSION_DB.set(str(runtime/'demo-seed.db'))
    try:
        init()
        stops=json.loads((RESOURCE/'data/stops.json').read_text(encoding='utf-8'))
        stops=[s for s in stops if s['id']=='0003291']
        with connect() as c:
            c.execute('INSERT INTO store VALUES (1,?,?,?,?)',('시연 가게','애월읍','카페',json.dumps(stops)))
            with (ROOT/'example-sales.csv').open(encoding='utf-8-sig') as f:
                c.executemany('INSERT INTO sales VALUES (?,?,0)',[(r['date'],int(r['amount'])) for r in csv.DictReader(f)])
    finally:SESSION_DB.reset(token)
    monkeypatch.setattr(main,'ROOT',tmp_path)
    monkeypatch.setenv('DEMO_PUBLIC_ORIGIN','https://demo.example')
    headers={'X-Weekly-Client':'1','Origin':'https://demo.example'}
    with TestClient(main.app,base_url='https://demo.example') as one,TestClient(main.app,base_url='https://demo.example') as two:
        assert 'assets/index-' in one.get('/').text
        assert one.get('/api/store').json() is None
        assert two.get('/api/store').json() is None
        assert one.cookies.get('weekly_session')!=two.cookies.get('weekly_session')
        assert one.get('/api/sales?from=2026-10-05&to=2026-11-08').json()==[]
        assert two.get('/api/history').json()==[]
        changed={'name':'별도 시연 가게','emd':'애월읍','industry':'카페','stops':stops}
        assert one.put('/api/store',headers=headers,json=changed).status_code==200
        assert one.get('/api/store').json()['name']=='별도 시연 가게'
        assert two.get('/api/store').json() is None
        sale={'rows':[{'date':'2026-11-02','amount':12345,'closed':False}]}
        assert one.put('/api/sales',headers=headers,json=sale).status_code==200
        assert len(one.get('/api/sales?from=2026-10-05&to=2026-11-08').json())==1
        assert two.get('/api/sales?from=2026-10-05&to=2026-11-08').json()==[]
        assert two.put('/api/store',headers=headers,json={**changed,'name':'다른 시연 가게'}).status_code==200
        assert two.put('/api/sales',headers=headers,json=sale).status_code==200
        assert one.delete('/api/my-data',headers=headers).status_code==200
        assert one.get('/api/store').json() is None
        assert two.get('/api/store').json()['name']=='다른 시연 가게'
        assert len(two.get('/api/sales?from=2026-10-05&to=2026-11-08').json())==1
        assert two.put('/api/store',headers={**headers,'Origin':'https://evil.invalid'},json=changed).status_code==403
        assert two.get('/api/store',headers={'Host':'evil.invalid'}).status_code==403
