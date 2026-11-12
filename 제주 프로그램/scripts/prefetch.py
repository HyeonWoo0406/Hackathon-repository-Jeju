"""Register a bounded public-data request; scheduled collector performs network I/O."""
import argparse,json,sys
from datetime import date,timedelta
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app.db import ROOT,RESOURCE,PUBLIC_DB
from backend.app.collection import enqueue
from scripts.collect_public import prepare

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--from',dest='start',required=True);parser.add_argument('--to',dest='end',required=True)
    parser.add_argument('--emd',required=True);parser.add_argument('--stops',required=True)
    args=parser.parse_args()
    start=date.fromisoformat(args.start);end=date.fromisoformat(args.end)
    if not 0<=(end-start).days<=34:parser.error('자료 준비 요청은 한 번에 최대 35일입니다.')
    catalog={s['id']:s for s in json.loads((RESOURCE/'data/stops.json').read_text(encoding='utf-8'))}
    ids=args.stops.split(',')
    if not 1<=len(set(ids))<=3 or any(key not in catalog for key in ids):parser.error('목록의 정류소 ID를 1~3개 지정하세요.')
    if args.emd not in json.loads((RESOURCE/'data/emds.json').read_text(encoding='utf-8')):parser.error('목록의 읍면동을 지정하세요.')
    path=ROOT/'runtime/public-data.db';token=PUBLIC_DB.set(str(path))
    try:
        prepare(path)
        dates=[(start+timedelta(days=i)).isoformat() for i in range((end-start).days+1)]
        print(json.dumps(enqueue(dates,{'emd':args.emd,'stops':[catalog[key] for key in ids]}),ensure_ascii=True))
        print('Queued only. No external API was called. Use the scheduled collector.')
    finally:PUBLIC_DB.reset(token)

if __name__=='__main__':main()
