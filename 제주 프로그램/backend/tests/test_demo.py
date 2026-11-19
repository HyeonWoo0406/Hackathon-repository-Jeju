import asyncio,json
import httpx
from fastapi.testclient import TestClient
from backend.app import note,demo
from backend.app.compute import build_report
from backend.tests.test_compute import sample,SETTINGS

def test_grounded_selection_and_rejection(monkeypatch):
    report=build_report(sample(),SETTINGS)
    async def chosen(*args,**kwargs):return '{"facts":["day_토"]}'
    monkeypatch.setattr(note,'model',chosen)
    result=asyncio.run(note.answer_question(report,'토요일은 어땠어?'))
    assert result['by']=='model' and result['evidence']==['day_토']
    assert result['answer']==note.question_facts(report)['day_토']
    assert asyncio.run(note.answer_question(report,'월요일은 어땠어?')) is None
    async def invented(*args,**kwargs):return '{"facts":["매출이 900% 올랐습니다"]}'
    monkeypatch.setattr(note,'model',invented)
    assert asyncio.run(note.answer_question(report,'매출은?')) is None
    async def reason(*args,**kwargs):return '{"facts":["summary"]}'
    monkeypatch.setattr(note,'model',reason)
    assert 'limit' in asyncio.run(note.answer_question(report,'왜 줄었어?'))['evidence']

def test_public_demo_is_read_only_and_offline_is_honest(tmp_path,monkeypatch):
    file=tmp_path/'reports.json'
    file.write_text(json.dumps([{'id':'case','label':'test','report':build_report(sample(),SETTINGS)}]),encoding='utf-8')
    monkeypatch.setattr(demo,'REPORTS',file)
    async def offline(*args,**kwargs):raise httpx.ConnectError('offline')
    monkeypatch.setattr(note,'model',offline)
    with TestClient(demo.app) as client:
        assert client.get('/').status_code==200
        assert client.get('/api/report?case=case').json()['example'] is False
        assert client.delete('/api/my-data').status_code==404
        assert client.put('/api/store',json={}).status_code==404
        response=client.post('/api/ask',json={'case':'case','question':'토요일은 어땠어?'})
        assert response.json()['by']=='template' and response.json()['notice']
        assert client.post('/api/ask',json={'case':'case','question':'a'*501}).status_code==422
        assert client.post('/api/ask',content='a'*5000).status_code==413
        assert client.post('/api/ask',headers={'Origin':'https://elsewhere.invalid'},json={'case':'case','question':'토요일'}).status_code==403
