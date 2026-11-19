"""Build public demo results from public tables and synthetic CSVs only."""
import csv,json,os,sqlite3,sys,tempfile,shutil
from contextlib import closing
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app.db import ROOT,RESOURCE,SETTINGS,init
from backend.app.hub import report_input
from backend.app.compute import build_report,calendar

def main():
    source_path=ROOT/'data'/'app.db'
    if not source_path.is_file():raise RuntimeError('공개 자료를 먼저 수집하세요.')
    previous=os.environ.get('WEEKLY_DB')
    with tempfile.TemporaryDirectory() as temporary:
        target=Path(temporary)/'demo.db';os.environ['WEEKLY_DB']=str(target);init()
        try:
            with closing(sqlite3.connect(source_path.as_uri()+'?mode=ro',uri=True)) as source,closing(sqlite3.connect(target)) as dest:
                for table in ('stop_bus','wifi','island_bus','weather','holiday','fetch_log'):
                    rows=source.execute('SELECT * FROM '+table).fetchall()
                    if rows:dest.executemany('INSERT OR REPLACE INTO '+table+' VALUES ('+','.join('?' for _ in rows[0])+')',rows)
                dest.commit()
            stops=json.loads((RESOURCE/'data/stops.json').read_text(encoding='utf-8'))
            store={'name':'애월 가상 카페','emd':'애월읍','industry':'카페','stops':[s for s in stops if s['id'] in ['0003291','0001087','0001082']]}
            data=report_input('2026-11-02',calendar('2026-11-02'),store);data['example']=True
            labels=['동네와 비슷한 흐름','가게 매출이 더 줄어든 주','가게 매출이 오른 주','토요일을 확인할 주','비교일이 부족한 주']
            result=[]
            files=sorted((ROOT/'examples/sales').glob('example-sales-*.csv'))
            if len(files)!=5:raise RuntimeError('가상 매출 5종을 확인하세요.')
            for file,label in zip(files,labels):
                with file.open(encoding='utf-8-sig') as f:
                    data['sales']={r['date']:{'amount':int(r['amount']),'closed':r['closed'].lower()=='true'} for r in csv.DictReader(f)}
                report=build_report(data,SETTINGS)
                result.append({'id':file.stem.removeprefix('example-sales-'),'label':label,'report':report})
            directory=ROOT/'runtime';directory.mkdir(exist_ok=True)
            (directory/'demo-reports.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
            shutil.copyfile(target,directory/'demo-seed.db')
            print('Prepared 5 synthetic demo reports. Private records were not copied.')
        finally:
            if previous is None:os.environ.pop('WEEKLY_DB',None)
            else:os.environ['WEEKLY_DB']=previous

if __name__=='__main__':main()
