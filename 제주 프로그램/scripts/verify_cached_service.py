"""Exercise concurrent visitors without any public-data API calls."""
import asyncio,json,sys,time
from datetime import date,timedelta
from pathlib import Path
import httpx
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app.db import ROOT,PUBLIC_DB
from backend.app.collection import Policy

async def visitor(origin,index):
    headers={'X-Weekly-Client':'1','Origin':origin}
    async with httpx.AsyncClient(base_url=origin,headers=headers,timeout=40,trust_env=False) as c:
        stops=(await c.get('/api/stops',params={'q':'0003291'})).json()
        r=await c.put('/api/store',json={'name':f'동시 검증 {index}','emd':'애월읍','industry':'카페','stops':stops});r.raise_for_status()
        try:
            ready=await c.get('/api/data-availability',params={'week_start':'2026-11-02'});ready.raise_for_status();assert ready.json()['ready']
            rows=[{'date':(date(2026,10,5)+timedelta(days=i)).isoformat(),'amount':500000+index*1000,'closed':False} for i in range(35)]
            r=await c.put('/api/sales',json={'rows':rows,'example':True});r.raise_for_status()
            start=time.monotonic();r=await c.post('/api/report-jobs',json={'week_start':'2026-11-02'});r.raise_for_status();key=r.json()['job_id']
            for _ in range(120):
                r=await c.get('/api/report-jobs/'+key);r.raise_for_status();job=r.json()
                if job['state']=='complete':break
                assert job['state']=='processing',job
                await asyncio.sleep(.5)
            else:raise AssertionError('job did not complete')
            assert job['result']['name']==f'동시 검증 {index}'
            return {'visitor':index,'seconds':round(time.monotonic()-start,2),'private_name_correct':True}
        finally:await c.delete('/api/my-data')

async def missing(origin):
    async with httpx.AsyncClient(base_url=origin,headers={'X-Weekly-Client':'1','Origin':origin},timeout=20,trust_env=False) as c:
        stops=[]
        for sid in ('0001081','0001626'):stops.append((await c.get('/api/stops',params={'q':sid})).json()[0])
        r=await c.put('/api/store',json={'name':'미준비 검증','emd':'애월읍','industry':'카페','stops':stops});r.raise_for_status()
        try:
            start=time.monotonic();r=await c.get('/api/data-availability',params={'week_start':'2026-11-02'});r.raise_for_status()
            assert not r.json()['ready']
            r=await c.post('/api/data-requests',json={'week_start':'2026-11-02'});r.raise_for_status()
            request_id=r.json()['request_id']
            again=await c.post('/api/data-requests',json={'week_start':'2026-11-02'});assert again.json()['request_id']==request_id
            r=await c.put('/api/sales',json={'rows':[{'date':'2026-10-05','amount':1},{'date':'2026-11-02','amount':1}]});r.raise_for_status()
            r=await c.post('/api/report-jobs',json={'week_start':'2026-11-02'});assert r.status_code==409
            return {'blocked_before_start':True,'request_deduplicated':True,'seconds':round(time.monotonic()-start,2)}
        finally:await c.delete('/api/my-data')

async def main(origin):
    token=PUBLIC_DB.set(str(ROOT/'runtime/public-data.db'))
    try:
        before=Policy(100).status()['calls']
        results=await asyncio.gather(*(visitor(origin,i) for i in range(5)))
        unavailable=await missing(origin)
        after=Policy(100).status()['calls'];assert before==after
        output={'concurrent_visitors':results,'missing_selection':unavailable,'collector_calls_added':after-before}
        (ROOT/'output/cache-only-verification.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(output))
    finally:PUBLIC_DB.reset(token)

if __name__=='__main__':asyncio.run(main(sys.argv[1].rstrip('/')))
