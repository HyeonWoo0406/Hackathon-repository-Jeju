"""Generate five synthetic sales uploads; public-data cache stays unchanged."""
import csv
import json
import sys
from copy import deepcopy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app.db import ROOT,RESOURCE,SETTINGS
from backend.app.hub import report_input
from backend.app.compute import calendar,build_report

def make():
    dates=calendar('2026-11-02')
    catalog=json.loads((RESOURCE/'data/stops.json').read_text(encoding='utf-8'))
    store={'name':'가상 시험 가게','emd':'애월읍','industry':'카페','stops':[s for s in catalog if s['id'] in ['0003291','0001087','0001082']]}
    data=report_input('2026-11-02',dates,store)
    with (ROOT/'example-sales.csv').open(encoding='utf-8-sig') as f:
        original=[{'date':r['date'],'amount':int(r['amount']),'closed':False} for r in csv.DictReader(f)]
    data['sales']={r['date']:r for r in original}
    reference=build_report(data,SETTINGS)['indicators'][0]['avg_base']
    cases=[('01-area','동네와 비슷한 흐름',.88,'area'),('02-store-down','가게만 줄어듦',.55,'store_down'),('03-store-up','가게만 좋음',1.25,'store_up'),('04-saturday','토요일 크게 줄어듦',.88,None),('05-hold','비교일 부족',.88,'hold')]
    directory=ROOT/'dist'/'시험자료_5종';directory.mkdir(parents=True,exist_ok=True)
    results=[]
    for key,label,ratio,expected in cases:
        rows=deepcopy(original)
        for row in rows[28:]:row['amount']=round(reference*ratio)
        if key=='04-saturday':rows[33]['amount']=100000
        if key=='05-hold':
            for row in rows[28:32]:row.update(amount=0,closed=True)
        data['sales']={r['date']:r for r in rows}
        report=build_report(data,SETTINGS)
        if expected:assert report['verdict']==expected,(key,report['verdict'])
        flagged=[d['date'] for d in report['days'] if d['flag']]
        if key=='04-saturday':assert '2026-11-07' in flagged
        destination=directory/f'example-sales-{key}.csv'
        if destination.exists():raise FileExistsError(destination)
        with destination.open('w',encoding='utf-8-sig',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=['date','amount','closed']);writer.writeheader();writer.writerows(rows)
        results.append({'file':destination.name,'scenario':label,'verdict':report['verdict_text'],'store_change':report['indicators'][0]['change'],'flagged':flagged})
    (ROOT/'output'/'test-cases-verified.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    return results
if __name__=='__main__':print(json.dumps(make(),ensure_ascii=True))
