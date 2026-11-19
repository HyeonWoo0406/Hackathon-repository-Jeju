"""Calendar comparisons. No disk, database, network, or model access."""
from datetime import date, timedelta
from statistics import mean, median
import math

LABELS={'store':'우리 가게 매출','stop_bus':'고른 정류소 버스 승차','wifi_visit':'방문 장소 와이파이 이용자','island_bus':'제주 전체 버스 승차(참고)'}
VERDICTS={'hold':'판정 보류','normal':'평소와 비슷한 주','store_down':'우리 가게만 줄어든 주','store_up':'우리 가게만 좋았던 주','area':'동네 전체 흐름'}

def calendar(week_start):
    w=date.fromisoformat(week_start)
    if w.weekday()!=0:raise ValueError('월요일을 선택하세요.')
    return [(w+timedelta(days=i)).isoformat() for i in range(-28,7)]

def ratio(current,base):
    return current/base-1 if base>0 else None

def boarding_total(rows):
    return sum(int(str(r['userCount']).replace(',','')) for r in rows if r['moveType']=='승차')

def wifi_totals(rows):
    totals={}
    for r in rows:totals[r['category']]=totals.get(r['category'],0)+int(str(r['userCount']).replace(',',''))
    return totals

def judge(store,area,settings):
    if store is None or area is None:return 'hold'
    if abs(store)<settings['flat'] and abs(area)<settings['flat']:return 'normal'
    gap=store-area
    if gap < -settings['gap'] and not math.isclose(gap,-settings['gap'],abs_tol=1e-12):return 'store_down'
    if gap > settings['gap'] and not math.isclose(gap,settings['gap'],abs_tol=1e-12):return 'store_up'
    return 'area'

def build_report(data,settings):
    dates=calendar(data['week_start']); w=data['week_start']
    series=data['series']; sales=data['sales']; excluded=[]; included=[]
    for d in dates:
        dow=date.fromisoformat(d).weekday()
        peers=[series['island_bus'][p] for p in dates if date.fromisoformat(p).weekday()==dow and series['island_bus'].get(p) is not None]
        value=series['island_bus'].get(d)
        row=sales.get(d,{})
        if value is None or (peers and value<median(peers)*0.5):reason='버스 운행 중단 또는 자료 빠짐'
        elif row.get('closed') or row.get('amount') is None:reason='휴무 또는 입력 없음'
        else:reason=None
        if reason:excluded.append({'date':d,'reason':reason})
        else:included.append(d)
    values={**series,'store':{d:r.get('amount') for d,r in sales.items()}}
    indicators=[]
    for key,label in LABELS.items():
        base=[values[key][d] for d in included if d<w and values[key].get(d) is not None]
        target=[values[key][d] for d in included if d>=w and values[key].get(d) is not None]
        a=mean(target) if target else None; b=mean(base) if base else None
        missing=any(values[key].get(d) is None for d in included)
        note=None; change=None
        if missing:note='비교 자료가 빠짐'
        elif len(target)<4 or len(base)<10:note='비교할 날이 모자람'
        elif b==0:note='기준 금액 또는 인원이 0이라 비교 불가'
        else:change=ratio(a,b)
        valid=change is not None
        if key in ('stop_bus','wifi_visit') and sum(target)<200:valid=False;note='숫자가 작아 참고만'
        if key=='island_bus':valid=False;note=note or '참고'
        indicators.append(dict(key=key,label=label,avg_target=a,avg_base=b,change=change,valid=valid,note=note,sum_target=sum(target),days_target=len(target),days_base=len(base)))
    lookup={i['key']:i for i in indicators}
    valid_area=[key for key in ('stop_bus','wifi_visit') if lookup[key]['valid']]
    area=mean(lookup[k]['change'] for k in valid_area) if valid_area else None
    store=lookup['store']['change']; verdict=judge(store,area,settings)
    days=[]
    for d in dates[28:]:
        dow=date.fromisoformat(d).weekday(); changes={}
        for key in ('store',*valid_area):
            peers=[values[key][p] for p in included if p<w and date.fromisoformat(p).weekday()==dow and values[key].get(p) is not None]
            changes[key]=ratio(values[key][d],mean(peers)) if d in included and values[key].get(d) is not None and len(peers)>=2 else None
        ac=[changes[k] for k in valid_area if changes.get(k) is not None]
        ad=mean(ac) if ac else None; sd=changes.get('store')
        gap=sd-ad if sd is not None and ad is not None else None
        weather=data.get('weather',{}).get(d,{})
        days.append(dict(date=d,dow='월화수목금토일'[dow],store=sd,area=ad,flag=gap is not None and gap < -settings['day_gap'] and not math.isclose(gap,-settings['day_gap'],abs_tol=1e-12),rain_mm=weather.get('rain_mm'),max_ws=weather.get('max_ws'),holiday=data.get('holidays',{}).get(d),excluded=d not in included))
    weather={}
    for key,field,limit in [('rain_days','rain_mm',1),('wind_days','max_ws',14)]:
        for period,suffix,denominator in [(dates[:28],'_base_per_week',4),(dates[28:],'',1)]:
            vals=[data.get('weather',{}).get(d,{}).get(field) for d in period]
            weather[key+suffix]=sum(v>=limit for v in vals)/denominator if all(v is not None for v in vals) else None
    for period,suffix,denominator in [(dates[:28],'_base_per_week',4),(dates[28:],'',1)]:
        known=data.get('holiday_known',[])
        weather['holiday_days'+suffix]=sum(bool(data.get('holidays',{}).get(d)) for d in period)/denominator if all(d in known for d in period) else None
    return dict(week_start=w,week_end=dates[-1],base_start=dates[0],base_end=dates[27],emd=data['store']['emd'],industry=data['store']['industry'],name=data['store'].get('name',''),indicators=indicators,neighborhood=area,gap=store-area if store is not None and area is not None else None,verdict=verdict,verdict_text=VERDICTS[verdict],days=days,weather=weather,excluded=excluded,sources=data.get('sources',[]),example=data.get('example',False),limits='버스 승차와 와이파이 이용은 동네 흐름의 일부입니다. 매출 변화의 원인을 확정하지 않습니다.')
