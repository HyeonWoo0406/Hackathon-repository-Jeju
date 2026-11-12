"""Public, read-only demonstration. No private database or write routes."""
import asyncio
import json
from pathlib import Path
import httpx
from fastapi import FastAPI,HTTPException,Request
from fastapi.responses import FileResponse,JSONResponse
from pydantic import BaseModel,Field,ConfigDict
from .db import ROOT
from .note import answer_question,question_facts,classify_basic

app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None)
REPORTS=ROOT/'runtime'/'demo-reports.json'
BUSY=asyncio.Lock()

@app.middleware('http')
async def boundary(request:Request,call_next):
    if request.method=='POST':
        origin=request.headers.get('origin')
        if origin and origin not in ('https://'+request.headers.get('host',''),'http://'+request.headers.get('host','')):
            return JSONResponse({'detail':'허용하지 않는 요청입니다.'},403)
        body=b''
        async for chunk in request.stream():
            body+=chunk
            if len(body)>4096:return JSONResponse({'detail':'질문이 너무 깁니다.'},413)
        request._body=body
    response=await call_next(request)
    response.headers.update({'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"})
    return response

def reports():return json.loads(REPORTS.read_text(encoding='utf-8'))

def selected(case):
    result=next((x for x in reports() if x['id']==case),None)
    if result is None:raise HTTPException(404,'사례가 없습니다.')
    return result

@app.get('/')
def index():return FileResponse(Path(__file__).with_name('demo.html'))

@app.get('/demo.js')
def script():return FileResponse(Path(__file__).with_name('demo.js'),media_type='text/javascript')

@app.get('/demo.css')
def style():return FileResponse(Path(__file__).with_name('demo.css'),media_type='text/css')

@app.get('/api/cases')
def cases():return [{'id':x['id'],'label':x['label']} for x in reports()]

@app.get('/api/report')
def report(case:str='01-area'):return selected(case)['report']

@app.get('/api/health')
async def health():
    ready=False
    try:
        async with httpx.AsyncClient(timeout=2,trust_env=False) as client:
            ready=(await client.get('http://127.0.0.1:8766/health')).status_code==200
    except httpx.HTTPError:pass
    return {'demo':True,'ai_ready':ready}

class Question(BaseModel):
    model_config=ConfigDict(extra='forbid')
    case:str=Field(max_length=40)
    question:str=Field(min_length=1,max_length=500)

@app.post('/api/ask')
async def ask(q:Question):
    report=selected(q.case)['report']
    if BUSY.locked():raise HTTPException(429,'다른 질문에 답하는 중입니다. 잠시 후 다시 질문해 주세요.')
    async with BUSY:
        answer=await answer_question(report,q.question)
    if answer:return answer
    facts=question_facts(report);basic=classify_basic(q.question)
    keys=[]
    if basic:
        if basic['intent']=='day_detail':keys=['day_'+d for d in basic.get('days',list('월화수목금토일'))]
        elif basic['intent'] in facts:keys=[basic['intent']]
    if not keys and any(w in q.question for w in ('매출','요약','왜','원인','결산')):keys=['summary','limit']
    return {'answer':'\n'.join(facts[k] for k in keys) if keys else '이 결산의 매출 요약, 요일별 변화, 비 온 날, 제주 전체 비교, 뺀 날과 출처를 질문해 주세요. 자료에 없는 내용은 답할 수 없습니다.',
            'by':'template','evidence':keys,'notice':'AI 답변을 확정하지 못해 기본 안내를 표시했습니다.'}
