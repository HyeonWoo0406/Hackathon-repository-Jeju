import asyncio,json
from datetime import date,timedelta
import httpx,pytest
from backend.app import hub
from backend.app.collection import Policy,BudgetStop,enqueue
from backend.app.db import SESSION_DB,PUBLIC_DB,init,public_connect

@pytest.fixture
def cache(tmp_path,monkeypatch):
    path=str(tmp_path/'public.db');a=SESSION_DB.set(path);b=PUBLIC_DB.set(path)
    init();monkeypatch.setenv('JEJU_HUB_KEY','private-test-key');monkeypatch.setattr(hub,'QUOTA_DAY',{})
    yield
    PUBLIC_DB.reset(b);SESSION_DB.reset(a)

def test_daily_cap_and_provider_block_survive_new_policy_instances(cache):
    first=Policy(2);first.reserve()
    restarted=Policy(2);restarted.reserve()
    with pytest.raises(BudgetStop):Policy(2).reserve()
    first.block('provider quota')
    with pytest.raises(hub.DailyQuota):Policy(2).reserve()
    tomorrow=Policy(2,day=(date.today()+timedelta(days=1)).isoformat());tomorrow.reserve()
    assert tomorrow.status()['calls']==1

def test_only_one_collector_can_hold_lease(cache):
    a=Policy();b=Policy();a.acquire()
    with pytest.raises(BudgetStop):b.acquire()
    a.release();b.acquire();b.release()

def test_partial_pages_resume_without_repeating_network_calls(cache):
    calls=[]
    def reply(request):
        page=int(request.url.params['number']);calls.append(page)
        return httpx.Response(200,json={'data':[{'row':page}],'totCnt':2,'hasMore':page==1})
    async def run(policy):
        async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as client:
            a=hub.CLIENT.set(client);b=hub.REQUEST_POLICY.set(policy)
            try:return await hub.hub_rows('stop_bus',{'startDate':'20261102'})
            finally:hub.CLIENT.reset(a);hub.REQUEST_POLICY.reset(b)
    with pytest.raises(BudgetStop):asyncio.run(run(Policy(1)))
    assert calls==[1]
    next_day=Policy(1,day=(date.today()+timedelta(days=1)).isoformat())
    assert asyncio.run(run(next_day))==[{'row':1},{'row':2}]
    assert calls==[1,2]
    assert asyncio.run(run(next_day))==[{'row':1},{'row':2}] and calls==[1,2]
    with public_connect() as c:
        stored=json.dumps([tuple(r) for r in c.execute('SELECT * FROM collection_pages')])
    assert 'private-test-key' not in stored

def test_retry_attempts_count_toward_budget(cache,monkeypatch):
    calls=[]
    async def no_wait(*args):pass
    monkeypatch.setattr(hub.asyncio,'sleep',no_wait)
    def fail(request):calls.append(1);return httpx.Response(500)
    async def run():
        token=hub.REQUEST_POLICY.set(Policy(1))
        try:
            async with httpx.AsyncClient(transport=httpx.MockTransport(fail)) as client:
                await hub.request_json(client,'https://example.invalid/data',{})
        finally:hub.REQUEST_POLICY.reset(token)
    with pytest.raises(BudgetStop):asyncio.run(run())
    assert len(calls)==1

def test_requests_deduplicate_and_never_store_private_store_fields(cache):
    store={'name':'private shop','industry':'private industry','emd':'애월읍','stops':[{'id':'0001081','name':'애월고등학교'}]}
    a=enqueue(['2026-11-02'],store)
    b=enqueue(['2026-11-02'],{**store,'name':'another shop'})
    assert a['request_id']==b['request_id']
    with public_connect() as c:rows=list(c.execute('SELECT body FROM collection_jobs'))
    assert len(rows)==1 and 'private' not in rows[0][0] and 'another' not in rows[0][0]

def test_network_is_forbidden_outside_collector():
    def forbidden(request):raise AssertionError('network must not be reached')
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(forbidden)) as client:
            await hub.request_json(client,'https://example.invalid/data',{})
    with pytest.raises(hub.Unavailable,match='정기 수집기'):asyncio.run(run())
