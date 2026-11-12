"""Exercise live AI over HTTP; never report template fallback as AI success."""
import json,time,sys
from pathlib import Path
import httpx

def main():
    base=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8770'
    results=[]
    with httpx.Client(base_url=base,timeout=45,trust_env=False) as client:
        assert client.get('/').status_code==200
        assert client.get('/api/health').json()['ai_ready']
        assert len(client.get('/api/cases').json())==5
        for case,question,required in [
            ('01-area','이번 주 매출을 요약해줘',['summary']),
            ('01-area','토요일은 어땠어?',['day_토']),
            ('02-store-down','왜 매출이 줄었어?',['summary','limit']),
            ('03-store-up','매출은 얼마나 변했어?',['summary']),
            ('04-saturday','토요일과 일요일을 비교해줘',['day_토','day_일']),
            ('01-area','비 온 날은 언제야?',['rain']),
            ('01-area','어떤 자료를 사용했어?',['sources']),
            ('05-hold','이번 주 결산을 요약해줘',['summary'])]:
            start=time.monotonic();response=client.post('/api/ask',json={'case':case,'question':question});response.raise_for_status();answer=response.json()
            result={'case':case,'question':question,'seconds':round(time.monotonic()-start,2),**answer}
            results.append(result)
            print(json.dumps({'case':case,'by':answer['by'],'evidence':answer['evidence'],'seconds':result['seconds']},ensure_ascii=True),flush=True)
            assert answer['by']=='model' and all(k in answer['evidence'] for k in required),result
        assert client.delete('/api/my-data').status_code==404
        assert client.get('/api/store').status_code==404
    directory=Path(__file__).resolve().parents[1]/'output';directory.mkdir(exist_ok=True)
    (directory/'demo-ai-verification.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    print('PASS: 8 actual model answers; 5 cases; no private/write API exposed.')

if __name__=='__main__':main()
