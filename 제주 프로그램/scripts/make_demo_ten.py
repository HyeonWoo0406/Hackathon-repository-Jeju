"""Create isolated synthetic upload fixtures, verified against cached public data."""
import asyncio
import csv
import io
import json
import random
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from starlette.datastructures import UploadFile
from backend.app.db import ROOT, RESOURCE, SETTINGS, PUBLIC_DB, SESSION_DB, init
from backend.app.compute import calendar, build_report
from backend.app.collection import availability
from backend.app.hub import report_input
from backend.app.main import upload

CASES = [
    ('01-steady-cafe', '꾸준한 카페', '카페', 240000, [1,1,1,1,1,1,1], None),
    ('02-growing-restaurant', '매출 상승 음식점', '음식점', 780000, [1.4]*7, None),
    ('03-declining-retail', '매출 감소 소매점', '소매', 460000, [.6]*7, None),
    ('04-weekend-cafe', '주말 상승 카페', '카페', 320000, [.95,1,1.03,1.02,1.1,1.8,1.65], None),
    ('05-weekday-restaurant', '평일 상승 음식점', '음식점', 950000, [1.5,1.45,1.4,1.55,1.4,.85,.9], None),
    ('06-saturday-drop', '토요일 감소 소매점', '소매', 530000, [1,1.05,.97,1.02,1.04,.25,1.08], None),
    ('07-monday-closed', '월요일 휴무 카페', '카페', 180000, [1,1.15,1.1,1.2,1.05,1.3,1.25], 0),
    ('08-wednesday-closed', '수요일 휴무 음식점', '음식점', 670000, [.85,.9,1,.8,.95,1.1,1.05], 2),
    ('09-zero-recovery', '영업 중 0원과 회복', '기타', 85000, [.7,0,.8,1.1,1.4,1.8,1.6], None),
    ('10-volatile-retail', '날마다 차이가 큰 소매점', '소매', 1250000, [.5,1.7,.65,1.4,.75,1.9,.8], None),
]


async def make():
    week = '2026-11-02'
    dates = calendar(week)
    output = ROOT / 'examples' / '결산가능_더미데이터_10종'
    output.mkdir(parents=True, exist_ok=True)
    catalog = json.loads((RESOURCE/'data/stops.json').read_text(encoding='utf-8'))
    stop = next(s for s in catalog if s['id'] == '0003291')
    public_token = PUBLIC_DB.set(str(ROOT/'runtime/public-data.db'))
    results = []
    try:
        with tempfile.TemporaryDirectory() as temporary:
            session_token = SESSION_DB.set(str(Path(temporary)/'validation.db'))
            try:
                init()
                for index, (slug, title, industry, base, factors, closed_dow) in enumerate(CASES):
                    store = {'name': '가상 '+title, 'emd': '애월읍', 'industry': industry, 'stops': [stop]}
                    assert availability(dates, store)['ready'], 'Public data is not ready'
                    rng = random.Random(2026111900+index)
                    rows = []
                    for i, day in enumerate(dates):
                        dow = i % 7
                        closed = dow == closed_dow
                        weekday_factor = (1+.05*((dow+index)%4)) if dow < 5 else (1.1+.1*(index%4))
                        factor = factors[dow] if i >= 28 else [1,.96,1.04,1.02][i//7]
                        amount = None if closed else round(base*weekday_factor*factor*rng.uniform(.96,1.04)/10)*10
                        rows.append({'date':day,'amount':amount,'closed':closed})
                    path = output / f'example-sales-{slug}.csv'
                    with path.open('w', encoding='utf-8-sig', newline='') as stream:
                        writer = csv.DictWriter(stream, fieldnames=['date','amount','closed'])
                        writer.writeheader(); writer.writerows(rows)
                    imported = await upload(UploadFile(filename=path.name, file=io.BytesIO(path.read_bytes())))
                    assert imported['rows'] == rows and imported['example']
                    data = report_input(week, dates, store)
                    data['sales'] = {row['date']:row for row in rows}
                    data['example'] = True
                    report = build_report(data, SETTINGS)
                    assert report['indicators'][0]['valid'] and report['verdict'] != 'hold'
                    results.append({'file':path.name,'store':store,'week_start':week,
                                    'total':sum(r['amount'] or 0 for r in rows[28:]),
                                    'verdict':report['verdict_text']})
            finally:
                SESSION_DB.reset(session_token)
    finally:
        PUBLIC_DB.reset(public_token)
    notes = ['결산 가능한 더미 매출 10종', '', '모두 합성 매출이며 실제 가게 자료가 아닙니다.',
             '읍면동: 애월읍', '정류소: 애월환승정류장(애월리), ID 0003291 한 곳만 선택',
             '결산할 주의 월요일: 2026-11-02', '각 파일: 2026-10-05 ~ 2026-11-08, 이전 4주+대상 1주 총 35일',
             '', '1. 가게 등록에서 아래 가게 이름과 업종을 입력하고 위 지역·정류소를 선택합니다.',
             '2. 매출 입력에서 결산 주를 2026-11-02로 선택합니다.',
             '3. CSV 한 개 업로드 → 미리보기 확인 → 저장 → 결산 보기 순서로 진행합니다.',
             '4. 다음 사례는 다른 CSV를 업로드하고 저장합니다. 같은 날짜 매출은 교체됩니다.',
             '실제 매출을 입력해 둔 브라우저 대신 별도 브라우저 프로필에서 시험하세요.',
             '파일은 매출만 포함합니다. 가게 설정·날짜는 위와 같이 직접 선택해야 합니다.',
             '공개 자료와 실제 사용자 DB에는 더미 자료를 넣지 않았습니다.',
             '휴무일은 빈 매출+closed=True, 영업 중 0원은 amount=0+closed=False입니다.', '', '파일별 설정과 검증 결과:']
    for item in results:
        notes.append(f"{item['file']}\n  이름: {item['store']['name']} / 업종: {item['store']['industry']}\n  대상 주 총매출: {item['total']:,}원 / 계산 결과: {item['verdict']}")
    (output/'사용방법.txt').write_text('\n'.join(notes)+'\n', encoding='utf-8-sig')
    (output/'검증결과.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'PASS: {len(results)} CSV uploads and computed reports; public/private user data unchanged')


if __name__ == '__main__':
    asyncio.run(make())
