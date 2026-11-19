import asyncio
import pytest
from backend.app import hub,note
from backend.tests.test_compute import sample,SETTINGS
from backend.app.compute import build_report

def test_quota_is_not_misreported_as_permission_error(monkeypatch):
    import httpx
    from datetime import date
    calls=[]
    from types import SimpleNamespace
    policy=SimpleNamespace(cached=lambda *args:None,reserve=lambda:None,block=lambda *args:None)
    async def check():
        token=hub.REQUEST_POLICY.set(policy)
        try:
            async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(403,text="Today's quota is full"))) as client:
                with pytest.raises(hub.DailyQuota,match='일일 조회 한도'):
                    await hub.request_json(client,'https://example.invalid/data',{})
        finally:hub.REQUEST_POLICY.reset(token)
    asyncio.run(check())
    monkeypatch.setattr(hub,'QUOTA_DAY',{})
    monkeypatch.setenv('JEJU_HUB_KEY','test')
    async def limited(*args,**kwargs):calls.append(1);raise hub.DailyQuota('일일 조회 한도')
    monkeypatch.setattr(hub,'request_json',limited)
    for _ in range(2):
        with pytest.raises(hub.DailyQuota):asyncio.run(hub.hub_rows('stop_bus',{}))
    assert len(calls)==1 and hub.QUOTA_DAY['stop_bus']==date.today()

def test_partial_page_is_not_accepted(monkeypatch):
    monkeypatch.setenv('JEJU_HUB_KEY','test')
    async def response(*a,**kw):return {'data':[{'x':1}],'totCnt':2,'hasMore':False}
    monkeypatch.setattr(hub,'request_json',response)
    with pytest.raises(hub.Unavailable):asyncio.run(hub.hub_rows('wifi',{}))

def test_model_wrong_fact_falls_back(monkeypatch):
    async def wrong(*a,**k):return '["매출이 999% 변했습니다."]'
    monkeypatch.setattr(note,'model',wrong)
    r=build_report(sample(),SETTINGS)
    result=asyncio.run(note.explain(r))
    assert result['by']=='template' and '999' not in result['text']

def test_missing_key_no_network(monkeypatch):
    monkeypatch.delenv('JEJU_HUB_KEY',raising=False)
    with pytest.raises(hub.Unavailable):asyncio.run(hub.hub_rows('wifi',{}))

@pytest.mark.parametrize('question,intent,days',[
    ('토요일은 어땠어?','day_detail',['토']),
    ('월요일과 화요일 비교해 줘','day_detail',['월','화']),
    ('주말은 어땠어?','day_detail',['토','일']),
    ('비 온 날만 보여줘','rain',[]),
    ('제주 전체와 비교해줘','island',[]),
    ('뺀 날과 이유 알려줘','excluded',[]),
    ('자료 출처는 어디야?','sources',[]),
    ('지난 결산 보여줘','history',[]),
])
def test_basic_questions_without_model(monkeypatch,question,intent,days):
    async def unexpected(*a,**k):raise AssertionError('Basic question must not need a model')
    monkeypatch.setattr(note,'model',unexpected)
    result=asyncio.run(note.classify(question))
    assert result['intent']==intent and result.get('days',[])==days and result['by']=='rule'

def test_unsupported_offline_question(monkeypatch):
    import httpx
    async def offline(*a,**k):raise httpx.ConnectError('offline')
    monkeypatch.setattr(note,'model',offline)
    assert asyncio.run(note.classify('어떤 메뉴를 만들까?'))['intent'] is None
