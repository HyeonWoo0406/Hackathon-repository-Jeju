# 프론트엔드

React 19, TypeScript, Vite로 만든 제주 가게 주간 결산 웹앱 화면입니다. 글꼴은 npm으로 고정한 Pretendard 1.3.9를 로컬 번들에 포함하며, 라이선스 사본은 `public/licenses/Pretendard-OFL.txt`에 있습니다.

## 실행

이 폴더에서:

```powershell
npm ci
npm run dev
```

개발 주소는 `http://127.0.0.1:5173/`입니다. 실제 앱은 별도 로컬 백엔드가 필요하며 `/api` 요청을 `http://127.0.0.1:8765`로 전달합니다. 백엔드 실행 방법은 [프로젝트 README](../README.md)를 참고하세요.

가상 자료로 화면만 검수하려면 `http://127.0.0.1:5173/design/audit-preview.html`을 엽니다. 이 개발용 페이지는 API 호출을 자체 가상 응답으로 대체하고 실제 가게나 매출을 저장하지 않습니다. 프로덕션 빌드에는 포함하지 않습니다.

## 검사와 빌드

```powershell
npm test
npm run build
```

빌드는 TypeScript 검사 후 `dist/`를 생성합니다. `dist/`와 `node_modules/`는 저장소에서 제외합니다. 의존성 재현을 위해 `package-lock.json`을 포함합니다.

## 현재 화면

- 가게 설정, 매출 입력, 주간 결산의 공통 작업 메뉴
- 화면 크기에 맞춘 한 주의 가게/동네 막대그래프
- 날짜 아래 가게/동네 변화율, 날짜 선택 시 소수점 상세 표시
- 실제 비교 기준: 그 전 4주 같은 요일 대비. 시간대 자료와 전일 대비 기능은 사용하지 않습니다.
- 접을 수 있는 PC 결산 사이드바, 모바일 결산 시트, 기존 질문 패널
- 전체 수치 표는 접어서 제공하며, 자료 없음과 실제 0%는 구분합니다.

수치 계산과 API 계약은 백엔드가 담당합니다. 화면 시안의 장식 사진은 제거했습니다.

## 주요 파일

| 위치 | 역할 |
| --- | --- |
| `src/WorkspaceLayout.tsx` | 공통 헤더와 작업 메뉴 |
| `src/pages/Setup.tsx`, `Sales.tsx` | 가게 설정과 매출 입력 |
| `src/pages/Report.tsx` | 막대그래프와 결산 패널 |
| `src/pages/ReportChat.tsx` | 결산 질문창 |
| `src/report-comparison.css` | 결산 배치와 반응형 스타일 |
| `src/surface-theme.css` | 청회색 배너, 추상 곡선과 배경·요약 영역 색상 |
| `src/typography.css` | 글꼴과 글자 간격 |
| `design/` | 개발용 검수 화면, 디자인 근거와 검수 기록 |

실행 파일은 빌드 당시 화면을 포함합니다. 소스 수정이 기존 EXE에 자동 반영되지는 않습니다. 프로젝트의 `scripts/build_exe.ps1`로 다시 빌드할 수 있습니다.
