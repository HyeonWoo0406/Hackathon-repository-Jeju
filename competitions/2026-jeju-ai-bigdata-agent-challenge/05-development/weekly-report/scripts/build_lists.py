import sys,asyncio,json,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app.hub import hub_rows
from backend.app.db import RESOURCE,SETTINGS
from backend.app.note import clean

async def main(day):
    stops=await hub_rows('stop_bus',{'startDate':day,'endDate':day})
    wifi=await hub_rows('wifi',{'searchDate':day})
    stations=sorted({(str(r['stationId']),r['stationName']) for r in stops if clean(r['stationName'])})
    emds=sorted({r['emd'] for r in wifi})
    if not stations or not emds:raise ValueError('목록 자료 없음')
    (RESOURCE/'data'/'stops.json').write_text(json.dumps([{'id':i,'name':n} for i,n in stations],ensure_ascii=False,indent=2),encoding='utf-8')
    (RESOURCE/'data'/'emds.json').write_text(json.dumps(emds,ensure_ascii=False,indent=2),encoding='utf-8')
    for r in wifi:
        if r['emd'] not in SETTINGS['asos_station']:SETTINGS['asos_station'][r['emd']]=189 if r['city']=='서귀포시' else 184
    (RESOURCE/'settings.json').write_text(json.dumps(SETTINGS,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'stops={len(stations)} emds={len(emds)}')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--date',required=True);asyncio.run(main(p.parse_args().date))
