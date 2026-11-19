# 제주 가게 주간 장사 결산 — 개발 산출물

2026-11-19 현재 웹 소스입니다. 개인 자료를 제외한 제출본입니다.
React 19 / TypeScript / Vite / Python FastAPI / SQLite / llama.cpp를 사용합니다.

## 포함 및 제외
소스·테스트·의존성 목록·실행 도구·합성 매출을 포함합니다.
.env 실값, API 키, 기존 DB 전체, 브라우저 세션, 로그, 개인 경로, 가상환경,
node_modules, 모델 파일, 실행 바이너리, 기존 빌드는 포함하지 않습니다.
.env.example에는 환경 변수 이름만 들어 있습니다.

## 데이터 준비 필독

**[데이터_목록.md](데이터_목록.md)**에 필요한 5종 데이터, API 식별자·필드·조회 범위, 키 설정, 더미 결산 수집 명령, 저장 위치와 한도 대응을 정리했습니다. 반드시 함께 확인하세요.

## 새 Windows PC에서 실행
Python 3.11과 Node.js 22 이상을 설치하고 weekly-report 폴더의 PowerShell에서 실행합니다.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-lock.txt
Copy-Item .env.example .env
Push-Location frontend
npm.cmd ci
npm.cmd run build
Pop-Location
.\.venv\Scripts\python.exe scripts/init_submission.py
.\.venv\Scripts\python.exe scripts/setup_model.py
```

.env에는 본인이 발급받은 키를 입력합니다. 다운로드에는 인터넷이 필요하며
모델·런타임은 대용량입니다. setup_model.py는 고정된 다운로드 파일의 해시를 확인합니다.
설치 환경에 따라 잠금 의존성을 설치할 수 없다면 오류를 확인하고 호환성을 검토해야 합니다.
이 제출본을 완전히 새 PC에 설치하는 과정은 별도로 검증하지 않았습니다.

자료 수집은 다음 명령입니다. API 승인·제공처 한도·자료 제공 범위에 따라 달라집니다.

```powershell
.\.venv\Scripts\python.exe scripts/collect_public.py --run
```

서버_관리.cmd를 더블클릭하고 1번을 선택하면 로컬 웹·AI 서버를 실행합니다.
http://127.0.0.1:8770 으로 접속하세요. 종료는 0번입니다.
2번 외부 공유 기능에는 cloudflared를 별도 설치해야 합니다.
현재 도구가 찾는 위치는 C:/Program Files (x86)/cloudflared/cloudflared.exe 입니다.
외부 주소는 임시 주소이며 실행할 때 바뀔 수 있습니다.

데이터수집_관리.cmd는 수집·로그·예약을 관리합니다.
자동 수집 예약은 새 PC에서 메뉴 4번으로 등록합니다. PC 전원과 로그인이 필요합니다.

## 중요한 시연 조건
이 ZIP에는 기존 공개 자료 DB도 없습니다. 압축만 풀면 즉시 모든 결산이 가능한 것은 아닙니다.
더미 CSV는 매출만 포함하며, 해당 지역·기간의 공개 자료는 별도 수집해야 합니다.
검증에 사용한 범위는 애월읍 / 애월환승정류장(애월리) 0003291 / 2026-11-02 주간입니다.
examples/결산가능_더미데이터_10종/사용방법.txt를 참고하세요.
실제 운영 PC에서 10종 결산을 확인한 것이며, 신규 설치의 자료 확보를 보장하지 않습니다.
제출 ZIP의 시연영상은 가상 매출과 당시 저장된 공개 자료로 녹화한 결과입니다.

## 검증 명령
```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests
Push-Location frontend
npm.cmd test
npm.cmd run build
Pop-Location
```

일부 scripts/verify_*.py는 서버·모델·수집된 자료가 있어야 실행되는 수동 검증 도구입니다.
기존 scripts/prepare_demo.py는 data/app.db에서 공개 자료를 복사하는 과거 도구입니다.
새 환경의 빈 DB 초기화에는 scripts/init_submission.py를 사용하세요.

## 구현 범위
공개 자료가 부족하면 결산을 막고 자료 준비 요청을 받습니다.
매출 단독 결산은 아직 구현하지 않았습니다.
숫자와 판정은 코드로 계산하고 AI는 현재 결산의 검증된 근거를 사용합니다.
지역 지표는 다른 가게의 실제 매출이 아니며 미래 예측이나 인과관계 확정을 하지 않습니다.
