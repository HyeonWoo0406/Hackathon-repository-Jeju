"""Exercise the public-data cache with synthetic sales in an isolated database."""
import sys,os,json,csv,sqlite3,tempfile
from pathlib import Path
from contextlib import closing
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app.db import ROOT,RESOURCE

def main():
    with tempfile.TemporaryDirectory() as temporary:
        db=Path(temporary)/'test.db'
        with closing(sqlite3.connect(ROOT/'data/app.db')) as source,closing(sqlite3.connect(db)) as target:source.backup(target)
        os.environ['WEEKLY_DB']=str(db)
        from backend.app.main import app
        from backend.app import hub
        from fastapi.testclient import TestClient
        # Disable external access after dotenv initialization, including all credentials.
        os.environ.pop('JEJU_HUB_KEY',None);os.environ.pop('DATA_GO_KR_KEY',None)
        stops=json.loads((RESOURCE/'data/stops.json').read_text(encoding='utf-8'))
        store={'name':'애월 예시 카페','emd':'애월읍','industry':'카페','stops':[s for s in stops if s['id'] in ['0003291','0001087','0001082']]}
        with (ROOT/'example-sales.csv').open(encoding='utf-8-sig') as f:rows=[{'date':r['date'],'amount':int(r['amount']),'closed':False} for r in csv.DictReader(f)]
        headers={'X-Weekly-Client':'1'}
        with TestClient(app) as client:
            assert client.put('/api/store',json=store,headers=headers).status_code==200
            assert client.put('/api/sales',json={'rows':rows,'example':True},headers=headers).status_code==200
            response=client.get('/api/report?week_start=2026-11-02',headers=headers)
            assert response.status_code==200,response.text
            r=response.json()
            assert r['example'] and r['verdict']=='area'
            assert r['indicators'][2]['sum_target']==1269
            assert r['indicators'][3]['sum_target']==579131
            assert r['weather']['rain_days']==3 and r['weather']['rain_days_base_per_week']==3
            assert len(r['excluded'])==4
            for intent in ['day_detail','rain','island','excluded','sources','history']:
                assert client.post('/api/ask',json={'week_start':'2026-11-02','intent':intent},headers=headers).status_code==200
            repeat=client.get('/api/report?week_start=2026-11-02',headers=headers).json()
            assert repeat['indicators']==r['indicators'] and repeat['verdict']==r['verdict']
            # Independent SQL checks use the same selected days but no compute helpers.
            with closing(sqlite3.connect(db)) as c:
                excluded=tuple(d['date'] for d in r['excluded'])
                baseline=c.execute('SELECT avg(boardings) FROM island_bus WHERE date BETWEEN ? AND ? AND date NOT IN (?,?,?,?)',('2026-10-05','2026-11-01',*excluded)).fetchone()[0]
                assert baseline==r['indicators'][3]['avg_base']
            assert client.delete('/api/my-data',headers=headers).status_code==200
            assert client.get('/api/history').json()==[]
    out=ROOT/'output';out.mkdir(exist_ok=True)
    (out/'verified-report.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'offline_report':'passed','repeat':'passed','followups':6,'delete':'passed','actual_wifi_total':1269,'actual_island_total':579131,'example_store_change':r['indicators'][0]['change'],'flagged':[d['date'] for d in r['days'] if d['flag']]},ensure_ascii=True))
if __name__=='__main__':main()
