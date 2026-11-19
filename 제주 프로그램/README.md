# 제주 버스 노선·시간대 수요 분석 에이전트

챌린지: 제주 AI·빅데이터 활용 AI Agent 개발 챌린지 (https://daker.ai/public/hackathons/jeju-ai-bigdata-agent-challenge)

> 공개 저장소에는 합성 버스 노선·정류소 데이터와 소스 코드만 포함합니다.
> 참가자 전용 XLSX, 실자료, API 키, 개인정보, 실행 산출물은 포함하지 않습니다.

## 팀
- 팀명: HeadLine2
- 팀장: 윤현우
- 팀원: 라로스, 밥이다

## 목표
제주도민과 비전문가가 버스 이용자 집계를 자연어로 탐색하고, 노선·시간대·요일·정류소·승하차·이용자 유형별 이용량을 표와 차트로 검토하도록 돕는다. `user_count`는 태그 기반 이용자 집계이지 차량 정원이나 잔여 좌석이 아니다. 이 프로젝트는 혼잡률·혼잡 예측·최적 배차를 제공하지 않는다.

## 사용 흐름
1. 자연어로 버스 이용량 질문 입력
2. 카탈로그에서 노선별 또는 정류소별 데이터셋 선택
3. 분석 기준별 이용자 수 합계와 요약 제공
4. 출처, 데이터가 합성인지 실자료인지, 한계를 함께 표시

## 스택
Python · Streamlit · pandas · LLM 제공자 추상화(mock 기본 / ollama 로컬 / openai 외부)

## 구조
```
app.py                    Streamlit UI
cli.py                    CLI 실행
src/data_loader.py        데이터셋 카탈로그 + CSV 로더
src/llm.py                LLMProvider, Mock/Ollama/OpenAI
src/agent.py              질의→탐색→집계→요약
data/sample_bus_routes.csv 합성 노선별 시연 데이터(실제 통계 아님)
data/sample_bus_stops.csv  합성 정류소별 시연 데이터(실제 통계 아님)
docs/                     제안서, 매뉴얼, 평가·데이터·AI 사용 명세
```

## 실행
```
cd jeju-ai-agent
pip install -r requirements.txt
copy .env.example .env
python cli.py "시간대별 노선 이용량을 보여줘"
streamlit run app.py
```

질문 예시: “요일별 노선 이용량”, “정류소별 하차 이용자 수”, “이용자 유형별 이용량”. 현재 MVP는 그룹 기준 집계만 하며 자연어 기간·조건 필터는 지원하지 않는다.

## 센터 PC
- 목표 실행 환경: 제주빅데이터센터 PC Intel Core i7-8700 / GTX 1060 / 32GB RAM
- 기본 mock은 외부 호출·GPU가 필요 없다. Ollama/OpenAI는 선택적 제공자이며 외부 제공자 사용 시 `docs/ai-usage-and-external-resources.md`를 확인한다.
- API 키는 코드에 넣지 않고 `.env`로만 관리한다.

## 데이터 안내
- 전달받은 데이터명세서_kr.xlsx(2026-11-04 v13) 내용상 반출 가능 후보는 3-02 버스 노선별 이용 현황, 3-04 버스 정류소별 이용 현황이다. 원시 자료는 아직 제공되지 않았다.
- **참가자 전용 데이터 목록(xlsx)은 저장소에 포함하지 않는다.** `*.xlsx`와 `data/private/`는 `.gitignore` 처리됨. 이용 조건과 반출 승인을 확인한 자료만 `data/private/`에 두고 `src/data_loader.py` 카탈로그에 등록한다.
- 두 `sample_bus_*.csv`는 **합성 데이터**이며 실제 제주 통계가 아니다. 앱과 CLI 결과에 합성 자료임을 표시한다.
- 5-02 일일 날씨 정보는 MVP 범위에서 제외하고 후속 연동 후보로만 둔다. 실제 원시 자료가 연결되기 전까지 통계·추세를 주장하지 않는다.

## 평가·제출 정보
평가 체크리스트와 제출 마감 등은 `docs/evaluation-checklist.md`, 제안서 요구 섹션은 `docs/proposal-outline.md`를 참고한다. 제안서 제출 마감: **2026-11-20 10:00**.
