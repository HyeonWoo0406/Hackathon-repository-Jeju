# 제주 가게 주간 장사 결산

제주 소상공인이 본인 매출과 공개된 지역 지표를 주별로 비교해 보는 개발용 프로그램입니다. 비교 결과는 참고 정보이며, 매출 변화의 원인을 입증하지 않습니다.

## 공개 저장소에 포함한 범위

저장소에는 소스 코드, 테스트, 설치 설정, 문서, 그리고 명시적으로 가상 자료라고 표시한 예시 매출만 포함합니다. 실제 매출이나 방문자 자료, API 키, 데이터베이스, 방문자 세션, 로그, 모델 가중치, 실행 파일 및 빌드 결과물은 포함하지 않습니다.

일부 공공자료 기능을 쓰려면 각 제공처의 이용 신청과 키가 필요합니다. 제공처의 최신 이용 조건과 사용 권한을 확인한 뒤 사용하세요. 실제 API 키는 `.env`에만 저장하며 GitHub에 올리지 마세요.

## 개발 실행

필요 환경: Python 3.11 이상, Node.js/npm.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Copy-Item .env.example .env
cd frontend
npm ci
npm run build
cd ..
.\.venv\Scripts\python.exe run.py
```

앱은 기본적으로 `http://127.0.0.1:8765`에서 실행됩니다. 제공처 키가 없거나 해당 기간 자료가 준비되지 않은 경우 일부 기능은 사용할 수 없습니다. `.env.example`을 `.env`로 복사한 뒤 필요한 키를 본인 환경에만 입력하세요.

`collection-plan.example.json`은 빈 예시 설정입니다. 수집 작업을 사용하려면 복사해 `collection-plan.json`을 만들고, 본인이 권한을 확인한 지역·정류소를 설정하세요. 실제 설정 파일은 Git에서 제외됩니다. 수집 작업을 실행하기 전에 호출 제한과 제공처 이용 조건을 확인하세요.

## 로컬 모델(선택)

모델 가중치와 llama.cpp 실행 파일은 크기와 별도 라이선스가 있어 저장소에 포함하지 않았습니다. `scripts/setup_model.py`는 명시적으로 실행할 때 모델과 CPU 런타임을 공식 배포처에서 내려받고 SHA-256을 확인합니다. 내려받은 파일은 Git에 추가하지 마세요. 이 스크립트는 모델과 런타임 파일을 내려받을 뿐이며, `run.py`에서 사용하는 위치로의 배치는 별도로 확인해야 합니다. 모델 없이도 기본 계산 및 고정 문구 기능을 사용할 수 있습니다.

## 검사

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -q
npm --prefix frontend test
npm --prefix frontend run build
```

## 주요 파일

- `backend/`: API, 계산, 자료 수집, 서버 테스트
- `frontend/`: React/TypeScript 사용자 화면
- `examples/sales/`: 가상 매출 예시
- `scripts/`: 개발·검증 도구와 선택적 모델 설치
- [데이터 목록](데이터_목록.md): 코드에서 사용하는 자료와 저장 항목
- [로컬 실행 안내](데모_실행.md): 개발 서버 실행 방법

실제 데이터 기반 완성도, 제공처 권한, 외부 배포 설정은 각 환경에서 별도로 확인해야 합니다. 이 저장소는 제출 완료나 운영 서비스 배포를 의미하지 않습니다.
