import io
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db import connect
HEADERS={'X-Weekly-Client':'1'}

def test_local_validation_and_upload(tmp_path,monkeypatch):
    monkeypatch.setenv('WEEKLY_DB',str(tmp_path/'test.db'))
    with TestClient(app) as client:
        matches=client.get('/api/stops?q=0003291').json()
        assert len(matches)==1 and matches[0]['id']=='0003291'
        saved={'name':'검토 카페','emd':'애월읍','industry':'카페','stops':matches}
        assert client.put('/api/store',json=saved,headers=HEADERS).status_code==200
        loaded=client.get('/api/store').json()
        assert 'id' not in loaded and loaded==saved
        assert client.put('/api/store',json=loaded,headers=HEADERS).status_code==200
        assert client.get('/api/stops?q=%20%20').json()==[]
        assert client.get('/api/store',headers={'Host':'example.com'}).status_code==403
        assert client.put('/api/sales',json={'rows':[]}).status_code==403
        assert client.put('/api/sales',json={'rows':[{'date':'2026-11-02','amount':-1}]},headers=HEADERS).status_code==422
        data='date,amount\n2026-11-02,10000\n2026-11-03,\n'
        r=client.post('/api/sales/upload',files={'file':('sales.csv',data.encode(),'text/csv')},headers=HEADERS)
        assert r.status_code==200,r.text
        assert r.json()['rows'][1]['amount'] is None
        with connect() as c:assert c.execute('SELECT count(*) FROM sales').fetchone()[0]==0
        assert client.put('/api/sales',json={'rows':r.json()['rows']},headers=HEADERS).status_code==200
        assert len(client.get('/api/sales?from=2026-11-02&to=2026-11-03').json())==2
        assert client.delete('/api/my-data',headers=HEADERS).status_code==200
        assert client.get('/api/sales?from=2026-11-02&to=2026-11-03').json()==[]

def test_question_and_synthetic_uploads(tmp_path,monkeypatch):
    import json
    from pathlib import Path
    from backend.tests.test_compute import sample,SETTINGS
    from backend.app.compute import build_report
    from backend.app.db import ROOT
    monkeypatch.setenv('WEEKLY_DB',str(tmp_path/'test.db'))
    async def offline(*args,**kwargs):return None
    monkeypatch.setattr('backend.app.main.answer_question',offline)
    report=build_report(sample(),SETTINGS)
    with TestClient(app) as client:
        with connect() as c:c.execute('INSERT INTO report VALUES (?,?,?)',('2026-11-02',json.dumps(report),'2026-11-12'))
        answer=client.post('/api/ask',headers=HEADERS,json={'week_start':'2026-11-02','question':'토요일은 어땠어?'}).json()
        assert answer['intent']=='day_detail' and answer['by']=='rule'
        assert '2026-11-07(토요일)' in answer['answer'] and '2026-11-08' not in answer['answer']
        files=list((ROOT/'examples'/'sales').glob('*.csv'))
        assert len(files)==5
        for file in files:
            response=client.post('/api/sales/upload',headers=HEADERS,files={'file':(file.name,file.read_bytes(),'text/csv')})
            assert response.status_code==200,response.text
            assert response.json()['example'] and len(response.json()['rows'])==35
            if 'hold' in file.name:assert sum(row['closed'] for row in response.json()['rows'])==4
        with connect() as c:assert c.execute('SELECT count(*) FROM sales').fetchone()[0]==0
