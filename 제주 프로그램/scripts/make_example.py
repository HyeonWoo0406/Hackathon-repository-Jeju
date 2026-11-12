"""Synthetic sales file only; does not replace any owner's sales."""
import sys,csv,random
from statistics import median
from datetime import date
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app.compute import calendar
from backend.app.db import connect,ROOT

def make():
    days=calendar('2026-11-02');rng=random.Random(42);base=[]
    with connect() as c:
        weather={r['date']:r['rain_mm'] for r in c.execute('SELECT * FROM weather WHERE stn=184')}
        island={r['date']:r['boardings'] for r in c.execute('SELECT * FROM island_bus')}
    for i,d in enumerate(days[:28]):
        amount=(600000 if i%7<5 else 900000)*rng.uniform(.95,1.05)
        if weather.get(d,0)>=10:amount*=.75
        base.append(round(amount))
    # Match the specification's weekly mean while keeping Saturday lower.
    included=[i for i,d in enumerate(days[:28]) if d in island and island[d]>=median([island[p] for p in days if p in island and date.fromisoformat(p).weekday()==i%7])*.5]
    if len(included)<10:raise ValueError('공공자료를 먼저 받아 주세요.')
    means=[sum(base[i] for i in included if i%7==dow)/len([i for i in included if i%7==dow]) for dow in range(7)]
    saturday=means[5]*.70
    factor=(sum(base[i] for i in included)/len(included)*7*.88-saturday)/(sum(means)-means[5])
    target=[round(saturday if i==5 else means[i]*factor) for i in range(7)]
    path=ROOT/'example-sales.csv'
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['date','amount']);w.writerows(zip(days,base+target))
    print('example-sales.csv created; synthetic sales only; no store records changed')
if __name__=='__main__':make()
