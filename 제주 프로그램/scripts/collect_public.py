"""Independent scheduled collector. Default mode plans only, without network calls."""
import argparse,asyncio,json,sys
from datetime import date,datetime,timedelta
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx
from backend.app.db import ROOT,RESOURCE,SETTINGS,PUBLIC_DB,SESSION_DB,init,public_connect
from backend.app import hub
from backend.app.collection import Policy,BudgetStop,enqueue,availability,init_collection

def prepare(path):
    path.parent.mkdir(parents=True,exist_ok=True)
    token=SESSION_DB.set(str(path))
    try:init()
    finally:SESSION_DB.reset(token)
    init_collection()

def plan(config):
    anchor=date.today()-timedelta(days=config.get('publication_lag_days',4))
    end=anchor-timedelta(days=(anchor.weekday()+1)%7)
    dates=[(end-timedelta(days=34-i)).isoformat() for i in range(35)]
    catalog={s['id']:s for s in json.loads((RESOURCE/'data/stops.json').read_text(encoding='utf-8'))}
    for target in config['targets']:
        store={'emd':target['emd'],'stops':[catalog[key] for key in target['stops']]}
        if not availability(dates,store)['ready']:enqueue(dates,store)

async def collect(config,run=False):
    policy=Policy(config['daily_call_cap'])
    policy.acquire()
    try:
        plan(config)
        with public_connect() as c:jobs=list(c.execute("SELECT * FROM collection_jobs WHERE state!='complete' AND (attempt_day IS NULL OR attempt_day!=?) ORDER BY created_at",(policy.day,)))
        result={'run':run,'eligible_jobs':len(jobs),'completed':0,'attempted':0,'usage':policy.status()}
        if not run:return result
        if result['usage']['blocked']:return {**result,'stopped':'provider_quota'}
        token=hub.REQUEST_POLICY.set(policy)
        try:
            async with httpx.AsyncClient(timeout=20,trust_env=False) as client:
                client_token=hub.CLIENT.set(client)
                try:
                    for job in jobs:
                        item=json.loads(job['body']);dates=item['dates'];store=item['store'];error=None;stop=False
                        result['attempted']+=1
                        try:
                            for d in dates:
                                if not await hub.fetch_island(d):continue
                                for station in store['stops']:await hub.fetch_stop(d,station)
                                await hub.fetch_wifi(d,store['emd'])
                            await hub.fetch_weather(dates[0],dates[-1],SETTINGS['asos_station'].get(store['emd'],184))
                            for month in sorted({d[:7] for d in dates}):await hub.fetch_holidays(int(month[:4]),int(month[5:]))
                        except (hub.DailyQuota,BudgetStop) as e:error=str(e);stop=True
                        except hub.Unavailable as e:error=str(e)
                        except (KeyError,ValueError,TypeError):error='제공 자료의 형식을 확인하지 못했습니다.'
                        ready=availability(dates,store)['ready']
                        with public_connect() as c:
                            c.execute('UPDATE collection_jobs SET state=?,attempt_day=?,updated_at=?,last_error=? WHERE key=?',('complete' if ready else 'pending',policy.day,datetime.now().isoformat(timespec='seconds'),error,job['key']))
                        if ready:result['completed']+=1
                        if stop:result['stopped']=error;break
                finally:hub.CLIENT.reset(client_token)
        finally:hub.REQUEST_POLICY.reset(token)
        result['usage']=policy.status()
        return result
    finally:policy.release()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',action='store_true');parser.add_argument('--db',type=Path,default=ROOT/'runtime/public-data.db');parser.add_argument('--config',type=Path,default=ROOT/'collection-plan.json')
    args=parser.parse_args();token=PUBLIC_DB.set(str(args.db.resolve()))
    log=ROOT/'runtime/collection-log.jsonl';log.parent.mkdir(exist_ok=True)
    try:
        prepare(args.db);config=json.loads(args.config.read_text(encoding='utf-8'))
        result=asyncio.run(collect(config,args.run));result['at']=datetime.now().isoformat(timespec='seconds')
        with log.open('a',encoding='utf-8') as f:f.write(json.dumps(result,ensure_ascii=False)+'\n')
        print(json.dumps(result,ensure_ascii=True))
    finally:PUBLIC_DB.reset(token)

if __name__=='__main__':main()
