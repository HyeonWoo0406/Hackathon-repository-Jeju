"""Check demo coverage from the local cache only; no API calls or private sales."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app.db import ROOT,RESOURCE,PUBLIC_DB,public_connect
from backend.app.collection import availability
from backend.app.compute import calendar
path=ROOT/'runtime/public-data.db'
if not path.is_file():
    print('Public DB missing. Run scripts/init_submission.py first.')
    sys.exit(1)
catalog=json.loads((RESOURCE/'data/stops.json').read_text(encoding='utf-8'))
store={'emd':'애월읍','stops':[s for s in catalog if s['id']=='0003291']}
dates=calendar('2026-11-02');token=PUBLIC_DB.set(str(path))
try:
    result=availability(dates,store)
    print(json.dumps(result,ensure_ascii=True,indent=2))
    with public_connect() as c:
        for table in ('island_bus','stop_bus','wifi','weather','holiday'):
            print(table,'rows in date range:',c.execute('SELECT count(*) FROM '+table+' WHERE date BETWEEN ? AND ?',(dates[0],dates[-1])).fetchone()[0])
    print('Ready refers to core source coverage only; holiday/weather and usable comparison days need separate review.')
finally:PUBLIC_DB.reset(token)
