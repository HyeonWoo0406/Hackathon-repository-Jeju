"""Check the original app through its public URL in isolated browser sessions."""
import json,sys,time
from pathlib import Path
import httpx

def main():
    origin=sys.argv[1].rstrip('/')
    headers={'X-Weekly-Client':'1','Origin':origin}
    with httpx.Client(base_url=origin,headers=headers,timeout=60,trust_env=False) as a,httpx.Client(base_url=origin,headers=headers,timeout=60,trust_env=False) as b:
        page=a.get('/');assert page.status_code==200 and '/assets/index-' in page.text
        status=a.get('/api/status').json();assert status['demo'] and status['llm']
        original=a.get('/api/store').json();assert original is None and b.get('/api/store').json() is None
        assert a.cookies.get('weekly_session')!=b.cookies.get('weekly_session')
        assert a.get('/api/stops',params={'q':'0003291'}).json()
        stops=[a.get('/api/stops',params={'q':key}).json()[0] for key in ('0003291','0001087','0001082')]
        store={'name':'웹 전체 흐름 검증 가게','emd':'애월읍','industry':'카페','stops':stops}
        assert a.put('/api/store',json=store).status_code==200
        assert b.get('/api/store').json()==original
        path=Path(__file__).resolve().parents[1]/'examples/sales/example-sales-04-saturday.csv'
        upload=a.post('/api/sales/upload',files={'file':(path.name,path.read_bytes(),'text/csv')});upload.raise_for_status()
        rows=upload.json()['rows'];assert len(rows)==35
        assert a.put('/api/sales',json={'rows':rows,'example':True}).status_code==200
        report=a.get('/api/report',params={'week_start':'2026-11-02'});report.raise_for_status()
        assert report.json()['name']==store['name'] and report.json()['example']
        assert len(report.json()['indicators'])==4 and len(report.json()['days'])==7
        assert a.get('/api/history').json()
        start=time.monotonic()
        answer=a.post('/api/ask',json={'week_start':'2026-11-02','question':'토요일은 어땠어?'});answer.raise_for_status()
        assert answer.json()['by']=='model' and 'day_토' in answer.json()['evidence']
        for intent in ('day_detail','rain','island','excluded','sources','history'):
            assert a.post('/api/ask',json={'week_start':'2026-11-02','intent':intent}).status_code==200
        assert b.put('/api/store',json={**store,'name':'다른 방문자 검증 가게'}).status_code==200
        assert b.put('/api/sales',json={'rows':[rows[0]],'example':True}).status_code==200
        assert a.delete('/api/my-data').status_code==200
        assert a.get('/api/store').json() is None
        assert b.get('/api/store').json()['name']=='다른 방문자 검증 가게'
        assert len(b.get('/api/sales',params={'from':'2026-10-05','to':'2026-11-08'}).json())==1
        assert b.delete('/api/my-data').status_code==200
        result={'full_app':True,'store_search_upload_sales_report_history_delete':'passed','separate_visitors':'passed','ai':answer.json(),'followup_buttons':6}
        output=Path(__file__).resolve().parents[1]/'output/full-demo-verification.json'
        output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print('PASS: original app, all workflow APIs, actual AI, and visitor isolation.')

if __name__=='__main__':main()
