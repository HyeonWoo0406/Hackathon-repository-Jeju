from copy import deepcopy
import pytest
from backend.app.compute import calendar,build_report,judge
from backend.app.note import valid_numbers,explain

SETTINGS={'flat':.05,'gap':.1,'day_gap':.2}
def sample():
    days=calendar('2026-11-02')
    return dict(week_start='2026-11-02',store={'emd':'애월읍','industry':'카페'},sales={d:{'amount':110 if d>=days[28] else 100,'closed':False} for d in days},series={k:{d:1000 for d in days} for k in ['stop_bus','wifi_visit','island_bus']},weather={},holidays={})

def test_change():
    r=build_report(sample(),SETTINGS)
    assert r['indicators'][0]['change']==pytest.approx(.1)
    assert r['verdict']=='area'
    assert r['weather']['rain_days'] is None

@pytest.mark.parametrize('fraction,excluded',[(.49,True),(.51,False)])
def test_median(fraction,excluded):
    d=sample();d['series']['island_bus']['2026-11-02']=1000*fraction
    r=build_report(d,SETTINGS)
    assert bool(r['excluded'])==excluded
    assert r['indicators'][0]['days_target']==(6 if excluded else 7)

def test_small_target_and_zero_base():
    d=sample()
    for day in calendar(d['week_start'])[28:4+28]:d['sales'][day]['closed']=True
    assert build_report(d,SETTINGS)['indicators'][0]['change'] is None
    d=sample()
    for day in calendar(d['week_start'])[:28]:d['sales'][day]['amount']=0
    assert build_report(d,SETTINGS)['verdict']=='hold'

@pytest.mark.parametrize('total,valid',[(199,False),(200,True)])
def test_small_area(total,valid):
    d=sample();days=calendar(d['week_start'])[28:]
    for day in days:d['series']['stop_bus'][day]=0
    d['series']['stop_bus'][days[0]]=total
    assert build_report(d,SETTINGS)['indicators'][1]['valid']==valid

@pytest.mark.parametrize('store,area,verdict',[(None,0,'hold'),(0,0,'normal'),(-.2,0,'store_down'),(.2,0,'store_up'),(.1,0,'area'),(-.1,0,'area'),(-.12,-.02,'area')])
def test_verdict(store,area,verdict):assert judge(store,area,SETTINGS)==verdict

@pytest.mark.parametrize('change,flag',[(-.21,True),(-.19,False),(-.20,False)])
def test_day(change,flag):
    d=sample();d['sales']['2026-11-07']['amount']=100*(1+change)
    assert build_report(d,SETTINGS)['days'][5]['flag']==flag

def test_missing_not_zero():
    d=sample();d['sales']['2026-11-02']['amount']=None
    r=build_report(d,SETTINGS)
    assert len(r['excluded'])==1 and all(i['days_target']==6 for i in r['indicators'])
    d=sample();del d['series']['wifi_visit']['2026-11-02']
    assert not build_report(d,SETTINGS)['indicators'][2]['valid']

def test_number_guard():
    assert valid_numbers('-12.0% / 13.5',{12,13.5})
    assert not valid_numbers('15%',{12,13.5})
    assert not valid_numbers('다음 주',set())

def test_pure_deterministic():
    d=sample();original=deepcopy(d)
    assert build_report(d,SETTINGS)==build_report(d,SETTINGS)
    assert d==original
