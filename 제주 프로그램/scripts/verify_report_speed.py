"""Measure actual public job latency and reuse across independent visitors."""
import json,sys,time
from datetime import date,timedelta
from pathlib import Path
import httpx

def job(client):
    started=time.monotonic()
    response=client.post('/api/report-jobs',json={'week_start':'2026-10-26'});response.raise_for_status()
    accepted=round(time.monotonic()-started,2);key=response.json()['job_id']
    while True:
        response=client.get('/api/report-jobs/'+key);response.raise_for_status();state=response.json()
        if state['state']=='failed':raise AssertionError(state['detail'])
        if state['state']=='complete':break
        time.sleep(.5)
    assert state['result']['emd']=='조천읍'
    return {'accepted_seconds':accepted,'completed_seconds':round(time.monotonic()-started,2)},key,state['result']

def main():
    origin=sys.argv[1].rstrip('/');headers={'X-Weekly-Client':'1','Origin':origin}
    with httpx.Client(base_url=origin,headers=headers,timeout=30,trust_env=False) as a,httpx.Client(base_url=origin,headers=headers,timeout=30,trust_env=False) as b:
        stops=a.get('/api/stops',params={'q':'0000192'}).json()
        start=date(2026,9,28)
        rows=[{'date':(start+timedelta(days=i)).isoformat(),'amount':500000+i%7*10000,'closed':False} for i in range(35)]
        for client,name in ((a,'첫 방문 검증'),(b,'다른 방문 검증')):
            assert client.get('/api/store').json() is None
            client.put('/api/store',json={'name':name,'emd':'조천읍','industry':'카페','stops':stops}).raise_for_status()
            client.put('/api/sales',json={'rows':rows,'example':True}).raise_for_status()
        try:
            first,key,report_a=job(a);print(json.dumps({'first':first}),flush=True)
            assert b.get('/api/report-jobs/'+key).status_code==404
            other,_,report_b=job(b);print(json.dumps({'other_visitor':other}),flush=True)
            repeated,_,report_repeat=job(a)
            assert report_a['name']=='첫 방문 검증' and report_b['name']=='다른 방문 검증'
            assert report_a['indicators']==report_b['indicators']==report_repeat['indicators']
            results={'first':first,'other_visitor':other,'repeat':repeated,'private_records_isolated':True}
            output=Path(__file__).resolve().parents[1]/'output/report-speed-verification.json'
            output.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(results),flush=True)
        finally:
            a.delete('/api/my-data').raise_for_status();b.delete('/api/my-data').raise_for_status()

if __name__=='__main__':main()
