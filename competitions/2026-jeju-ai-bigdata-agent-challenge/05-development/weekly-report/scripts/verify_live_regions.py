"""Check uncached regions through the public app using synthetic sales."""
import csv,io,json,sys,time
from datetime import date,timedelta
from pathlib import Path
import httpx

def main():
    origin=sys.argv[1].rstrip('/');results=[]
    for emd,sid,week in [('조천읍','0000192','2026-10-26'),('이도2동','0003270','2026-11-02')]:
        with httpx.Client(base_url=origin,headers={'X-Weekly-Client':'1','Origin':origin},timeout=110,trust_env=False) as c:
            stop=c.get('/api/stops',params={'q':sid}).json()[0]
            c.put('/api/store',json={'name':'다른 지역 검증 가게','emd':emd,'industry':'카페','stops':[stop]}).raise_for_status()
            try:
                stream=io.StringIO();writer=csv.writer(stream);writer.writerow(['date','amount','closed'])
                start=date.fromisoformat(week)-timedelta(days=28)
                for n in range(35):writer.writerow([(start+timedelta(days=n)).isoformat(),500000+(n%7)*10000,'false'])
                preview=c.post('/api/sales/upload',files={'file':('example-sales-api.csv',stream.getvalue().encode(),'text/csv')});preview.raise_for_status()
                c.put('/api/sales',json={'rows':preview.json()['rows'],'example':True}).raise_for_status()
                t=time.monotonic();response=c.get('/api/report',params={'week_start':week});response.raise_for_status()
                elapsed=round(time.monotonic()-t,2);r=response.json()
                assert r['emd']==emd and r['week_start']==week and len(r['days'])==7
                # Island-wide bus is deliberately reference-only, not a verdict input.
                assert r['indicators'][0]['valid'] and r['indicators'][1]['valid'],r['indicators']
                wifi=r['indicators'][2]
                assert wifi['days_target']==7
                if wifi['sum_target']==0:assert not wifi['valid'] and wifi['change'] is None
                assert r['indicators'][3]['change'] is not None
                repeat=c.get('/api/report',params={'week_start':week});repeat.raise_for_status()
                assert repeat.json()['indicators']==r['indicators']
                result={'emd':emd,'station':sid,'week':week,'seconds':elapsed,'verdict':r['verdict'],'store_and_bus_valid':True,'wifi_target_total':wifi['sum_target'],'wifi_valid':wifi['valid'],'sources_status':r['sources_status'],'repeat':'passed'}
                results.append(result);print(json.dumps(result,ensure_ascii=True),flush=True)
            finally:c.delete('/api/my-data').raise_for_status()
    out=Path(__file__).resolve().parents[1]/'output/public-live-api-verification.json'
    out.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    print('PASS: two uncached selections collected, computed, and repeated through public HTTP.')

if __name__=='__main__':main()
