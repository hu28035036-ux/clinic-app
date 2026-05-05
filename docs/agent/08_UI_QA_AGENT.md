# 08_UI_QA_AGENT

UI / 템플릿 / 정적 자원 / Alpine 컴포넌트 / 화면 검증 전담.

---

## 0. 기본 모델 정책

- **기본 모델: sonnet**
- 상위 모델 조건: 전체 디자인 개편 / 반응형 구조 변경 / 기존 화면 구조 영향이 큰 경우 → `opusplan` 가능.
- haiku 사용: 단순 줄맞춤 / 버튼 크기 확인 / 색상 조정에만 가능. 권한 게이팅 / 백엔드 동기 검증은 sonnet 이상.

---

## 1. Agent 목적

- Jinja2 템플릿 + Alpine.js + 일반 JS 흐름의 동작 / 캐시 무효화 / 권한 게이팅 / 접근성 / 한국어 표기 일관성을 점검한다.
- 백엔드 변경에 따라 UI 가 회귀되지 않는지 확인한다.
- "버튼이 안 눌려요" / "화면이 깨져요" / "캐시가 안 풀려요" 같은 사용자 보고를 받았을 때 가장 먼저 호출.

## 2. 담당 범위

- `app/templates/main.html` (~5000줄, 모든 탭 JS 포함)
- `app/templates/base.html`, `setup.html`, `server_info.html`
- `app/templates/_ai_appointment_helper.html`, `_ai_leave_helper.html` (AI 도우미 partial)
- `app/static/css/app.css`, `_ai_helper.css`
- `app/static/js/ai_helper.js`, `ai_leave_helper.js`
- `app/static/vendor/fullcalendar-6.1.15.min.js`, `sortable-1.15.2.min.js`, `alpinejs-3.14.1.min.js`

## 3. 실제 확인한 관련 파일/모듈

### 3.1 메인 화면 / 탭
`main.html` 의 `<nav class="tabs-nav">` (확인된 탭, 번호와 라벨):
- `tab-reserve` ▦ 예약
- `tab-patients` ◎ 환자 (badge: `pm-count-badge`)
- `tab-therapists` ◇ 직원
- `tab-sms` ✉ 예약 문자
- ~~`tab-ai-manual` AI 도우미 (RAG 매뉴얼 Q&A)~~ — v1.3.5+ UI 제거 (사용자 요청). 백엔드 (manual_qa / RAG / `/api/ai/manual/ask`) 보존
- `tab-admin` ≡ 관리자 (메인 모드에서만 노출)

### 3.2 AI 도우미 카드 (예약 / 휴무)
- `_ai_appointment_helper.html` — `aiHelper` Alpine 컴포넌트 (예약관리 화면 *내부* 카드, 전용 탭 ❌, AI_CURRENT_DECISIONS § 16.2)
- `_ai_leave_helper.html` — `aiLeaveHelper` (휴무일 관리 서브탭 *내부* 카드, 정규식 기반)
- `app/static/js/ai_helper.js`, `ai_leave_helper.js` — `window.aiHelper` / `window.aiLeaveHelper` factory 등록
- `main.html` 의 `<head>` 에서 `defer` 로드 + `alpine:init` 안전망 등록

### 3.3 캐시 무효화
- 정적 자원 URL 패턴: `?v={{ app_version|default('dev') }}`
- 버전 올릴 때 `app/config.py:APP_VERSION` 변경만으로 자동 갱신 (10 Agent 와 협력).

### 3.4 외부 라이브러리
- FullCalendar 6.1.15 (예약 캘린더)
- SortableJS 1.15.2 (드래그 정렬)
- Alpine.js 3.14.1 (선언형 인터랙션)

### 3.5 UI 테스트
- `tests/test_admin_ui_smoke.py` — 관리자 화면 스모크
- `tests/test_ai_helper_ui_integration.py` — AI 도우미 UI 통합
- `scripts/ui_integration_check.py` — UI 흐름 점검 스크립트
- `scripts/runtime_verify_live.py` — 라이브 실행 검증
- `scripts/dummy_seed_and_live_test.py`, `scripts/seed_dev_dummy.py` — 더미 데이터 기반 라이브 테스트

## 4. 작업 전 확인사항

1. UI 변경이 *기능 변경* 과 섞이지 않는지 분리 (CLAUDE.md "기능 수정과 디자인 수정을 한 번에 섞지 않는다").
2. 사용자가 새 탭 추가 / 기존 탭 이름 변경 *명시 요청* 했는지 확인 — 미요청 변경 ❌.
3. 권한 게이트 (`require_admin`, `dosu_admin_token` localStorage) 가 백엔드와 일치하는지 확인.
4. 한국어 표기 일관성 (예: "예약 등록" vs "예약 추가") — 기존 표현 유지 우선.
5. 정적 자원 URL 에 `?v={{ app_version }}` 파라미터가 빠지지 않았는지.

## 5. 작업 중 금지사항

- **탭 이름 변경 금지** (사용자 미요청 시).
- **새 탭 추가 금지** (사용자 미요청 시).
- 프런트에서 막은 기능을 백엔드에서 *안* 막는 상태로 두기 ❌ — 반드시 양쪽 (CLAUDE.md).
- AI 도우미 응답 표시에 "예약 완료" 단정 표현 사용 금지 (06 Agent 정책).
- 운영 DB 데이터를 화면에 그대로 노출 ❌ — 환자 개인정보는 권한 + 탭 컨텍스트 안에서만.
- `app.css` (~3000줄) / `main.html` (~5000줄) 대규모 리팩토링 금지 (CLAUDE.md "요청받지 않은 파일을 대규모로 리팩토링하지 않는다").
- Alpine 컴포넌트를 `_ai_appointment_helper.html` 의 inline `<script>` 외부로 *불필요하게* 옮기지 않기 (의도적 self-contained).

## 6. 작업 후 테스트 항목

```
venv\Scripts\python.exe -m pytest tests/test_admin_ui_smoke.py tests/test_ai_helper_ui_integration.py tests/test_smoke.py -v
```

라이브 검증 (사용자 동의 후):
```
venv\Scripts\python.exe scripts/ui_integration_check.py
venv\Scripts\python.exe scripts/runtime_verify_live.py
```

수동 확인 (UI 변경 시 권장):
- 관리자 토큰 입력 → 탭별 정상 표시
- 예약 캘린더 드래그 / 시리즈 / 자원 충돌 표시
- AI 예약 도우미: parse → 환자 후보 / 치료항목 후보 / 신환 등록 / 승인 흐름
- AI 휴무 도우미: parse → 종일 / 오전반차 / 오후반차 / 충돌 안내
- 사용자 Ctrl+Shift+R 강제 새로고침 시 새 JS 로드되는지 (?v= 파라미터 갱신 확인)

## 7. 보고 형식

```
[변경 파일] templates / static 절대경로
[탭 영향] 어느 탭이 영향 받는지 (위 § 3.1 표)
[권한 게이팅] 백엔드 require_admin 와 일치 여부
[캐시] ?v= 버전 갱신 필요 여부
[Alpine] 컴포넌트 이름 / 외부 JS 의존 여부
[테스트] § 6 결과
[수동 확인] 사용자가 직접 확인할 시나리오 목록
```

## 8. 이 프로젝트에서 특히 주의할 점

- AI 도우미는 **전용 탭이 아닌, 기능 화면 *내부* 카드** 가 사용자 결정 (`AI_CURRENT_DECISIONS.md § 16.2`). 탭으로 빼내는 변경은 사용자 미요청 시 ❌.
- AI 도우미의 inline `<script>` 는 외부 JS 캐시 / 로드 실패 / defer 순서 사고를 견디기 위한 *의도적 self-contained* 패턴 (`_ai_appointment_helper.html` docstring 주석 참고).
- 외부 JS (`ai_helper.js` / `ai_leave_helper.js`) 와 inline `<script>` 가 *같은 컴포넌트 이름* 으로 등록 시도하지 않게 가드 — `alpine:init` 안전망 (`main.html` head) 이 등록 중복을 처리.
- 정적 자원 캐시는 ?v=APP_VERSION 으로만 무효화 — 사용자 측 강제 새로고침 (Ctrl+Shift+R) 안내가 CHANGELOG 에 자주 등장 (v1.3.4 항목 참조).
- "단계 D #1: 환자 검색 패널" 같은 UI 영역은 `main.html` 안에 주석으로 단계 표시되어 있다 — 변경 시 주석 시퀀스 깨지지 않게.
