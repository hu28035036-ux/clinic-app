# AI 업무 실행 — 치료사 휴무 등록 (Session Log)

본 문서는 [docs/ai_action_leave_plan.md](ai_action_leave_plan.md) 에 정의된 세션 12 ~ 15 의 진행 기록이다.

> ⚠️ 이 문서는 **각 세션 종료 시** 작성한다. 작성 안 한 섹션은 **빈 칸으로 둔다.**
> 다음 세션 작업자는 이 문서를 읽고 "이전 세션이 어디까지 했는지" 를 파악해 이어간다.

---

## 진행 요약 표

| 세션 | 목표 | 완료 | 수정 파일 | 추가 API | 테스트 결과 | 다음 세션 진행 가능 | 남은 위험 |
|------|------|------|------|------|------|------|------|
| 12_AI업무실행_휴무등록_설계 | plan 입력으로 spec 확정 (JSON 스키마 / 토큰 포맷 / 에러 코드 / 매칭 의사코드 / UI 와이어프레임) | ✅ 완료 | docs/specs/04_ai_action_leave.md (신설), docs/ai_action_leave_plan.md (링크 1줄 추가), docs/ai_action_leave_session_log.md | (없음 — 설계만) | (해당 없음 — 설계만, 코드 변경 없음) | ✅ Yes | LLM provider 비용·rate limit 정책 미정 (13 세션에서 결정 권장) |
| 13_AI업무실행_휴무등록_백엔드 | parse / preview / execute 엔드포인트 + 매칭 / 검증 / 토큰 / 로깅 | ✅ 완료 | app/services/ai/{date_resolver,action_leave}.py (신설), app/routers/{ai.py,api.py} (수정), tests/{conftest.py,test_ai_action_leave.py} (수정/신설) | 3개 (`POST /api/ai/action/{parse,preview,execute}`) | 신규 35 PASS, 회귀 13 PASS + 4 XFAIL, 전체 167 PASS / 1 skip / 7 XFAIL, ruff 0 errors, DB 경로 안전검사 통과 | ✅ Yes | LLM rate limit 미적용 (14/15 세션 이월) |
| 14_AI업무실행_휴무등록_UI | 치료사 탭 → 휴무일 관리 서브탭에 AI 휴무 등록 카드, plain JS 핸들러, dev 서버 시연 | ✅ 완료 | app/templates/main.html, app/static/css/app.css | (없음 — UI 만, 백엔드 미수정) | dev 서버 4 시나리오 시연 통과, 회귀 167 PASS / 1 skip / 7 XFAIL, ruff 0 errors, DB 경로 안전검사 통과 | ✅ Yes | leave_type 값 불일치 (백엔드 morning/afternoon vs 기존 캘린더 am/pm) — 15 세션 또는 후속 작업에서 정리 필요 |
| 15_AI업무실행_휴무등록_테스트보안 | 22 항목 자동화 검증 + 호환성 버그 fix (leave_type=am/pm/full 통일) + 보안 회귀 + 배포 가능 확인 | ✅ 완료 | app/services/ai/action_leave.py, tests/harness/seed_data.py, tests/test_ai_action_leave.py, tests/test_smoke.py, docs/ai_action_leave_plan.md, docs/specs/04_ai_action_leave.md, docs/ai_action_leave_session_log.md | (없음) | 신규 5 + 기존 35 = 40 PASS / 회귀 172 PASS / 1 skip / 7 XFAIL, ruff 0 errors, DB 경로 안전, 앱 부팅 OK (104 routes) | ✅ Yes — 배포 빌드 진행 가능 | outcome 컬럼 길이 truncate (영향 없음, 마이그레이션은 후속), LLM rate limit 미적용 (단독실행이라 낮음) |
| 16_AI_RAG_휴무등록_최종테스트_검증 | 사용자 명시 ~110 항 검증 매트릭스 재실행 + 발견된 4건 진단 + #1 (PII pre-gate 보강) fix | ✅ 완료 | app/services/ai/action_leave.py, tests/test_ai_action_leave.py, docs/ai_action_leave_session_log.md | (없음) | 신규 3 + 기존 40 = 43 PASS / 전체 175 PASS / 1 skip / 7 XFAIL, ruff 0 errors, DB 경로 안전, 앱 부팅 OK (104 routes) | ✅ Yes — 배포 빌드 진행 가능 (조건부) | #2 health public 분리, #3 EmployeeLeave UNIQUE 제약, #4 outcome 길이 확장 — 17 세션 이월 |

---

## 세션 12 — AI업무실행_휴무등록_설계

### 목표 (구체)

- [docs/ai_action_leave_plan.md](ai_action_leave_plan.md) 의 "세션 12 — 설계" 항목을 구체 spec 으로 확정.
- 13 세션부터 코드 작업만으로 구현이 가능하도록 다음을 결정·문서화:
  - 자연어 명령 처리 흐름 (parse → preview → execute, 엔드포인트는 2 개).
  - 날짜 해석 규칙 (Asia/Seoul 고정, 표 기반 결정론).
  - 휴무 유형 변환 규칙 (한국어 키워드 → `full` / `morning` / `afternoon` 매핑, [spec 02](specs/02_치료사_휴무_규칙.md) 표준 준수).
  - 치료사명 정규화·매칭 의사코드 (정확 일치 1 건만 통과, 동명이인 1 차 보류).
  - 중복 휴무 충돌 (`mode = create / overwrite / noop`) 과 예약 충돌 (warnings 만, 차단 안 함).
  - LLM 응답 JSON 스키마 (Pydantic strict, extra=forbid).
  - `preview_token` HMAC-SHA256 + URL-safe base64 페이로드, TTL 120 초, 메모리 secret.
  - parse / preview / execute 요청·응답 JSON 모양.
  - UI 와이어프레임 (휴무일 관리 영역 vs 메인 사이드 — 14 세션에서 최종 결정).
  - AuditLog / AiUsageLog 기록 방식 (해시 only, PII 미포함).
  - 할루시네이션 차단 13 항.
  - 에러 코드 ↔ 한국어 ↔ HTTP 일람 (25+ 항).
  - 단위·통합·보안·LLM mock 테스트 시나리오 29 항 (T1 ~ T29 + 회귀).

### 완료 여부

- ✅ 완료. [docs/specs/04_ai_action_leave.md](specs/04_ai_action_leave.md) 신설로 산출물 확정.
- 13 세션에서 추가로 결정해야 하는 사소한 항목은 spec § 14 에 명시 (함수 경계 / FakeProvider 위치 등).

### 수정 파일

- 신규: [docs/specs/04_ai_action_leave.md](specs/04_ai_action_leave.md) (~ 580 줄, 설계 확정 본문)
- 갱신: [docs/ai_action_leave_plan.md](ai_action_leave_plan.md) (헤더에 spec 04 링크 1 줄 추가, 본문 변경 없음)
- 갱신: [docs/ai_action_leave_session_log.md](ai_action_leave_session_log.md) (본 세션 기록)
- **코드 변경 없음** (설계 세션 제약 준수).

### 추가 API

- 없음 (설계만). spec 에 정의된 API 는 다음과 같이 13 세션에서 추가 예정:
  - `POST /api/ai/action/leave/preview`
  - `POST /api/ai/action/leave/execute`
  - `GET /api/ai/action/leave/health` (선택, 14 세션 또는 보류)

### 테스트 결과

- 해당 없음 — 코드 변경 없음, 문서 작성만.
- 회귀 영향: 없음 (기존 모듈 import / 기존 테스트 영향 0).

### 다음 세션 진행 가능 여부

- ✅ **Yes.** 13 세션 백엔드 작업은 [spec 04](specs/04_ai_action_leave.md) 를 그대로 따라 작성 가능.
- 13 세션 시작 시 spec 의 다음 절을 우선 구현:
  1. `app/services/ai/date_resolver.py` 신설 — § 3 의 표 그대로 결정론 함수.
  2. `app/services/ai/action_leave.py` 신설 — § 4·5·6·7 의 매핑·매칭·검증·토큰.
  3. [app/routers/ai.py](../app/routers/ai.py) 에 § 8 의 두 엔드포인트 추가.
  4. § 13.7 의 `FakeProvider` 로 `tests/test_ai_action_leave.py` 작성.

### 남은 위험

- LLM provider rate limit / 비용 폭주 차단이 spec 에 미명시 — 13 세션 시작 시 admin 토큰별 분당 N 회 정책 결정 권장 (단순 인메모리 카운터로 충분).
- spec § 9.1 의 UI 위치 A/B 안 (휴무일 관리 영역 vs 메인 사이드) 미확정 — 14 세션 결정. 13 세션 백엔드 작업에는 영향 없음.
- 동시성 충돌 시 `EmployeeLeave` 에 (employee_id, leave_date) UNIQUE 제약이 DB 레벨에 없음 — 1 차에서는 트랜잭션 내 재조회 (TOCTOU 가드, spec § 6.3) 로 충분히 대응. 마이그레이션 추가는 보류.
- 운영 DB 격리 (`scripts/check_db_path.py`) 는 13 세션부터 코드 작성 시 매 단계 확인 필요.

---

## 세션 13 — AI업무실행_휴무등록_백엔드

### 목표 (구체)

- [docs/specs/04_ai_action_leave.md](specs/04_ai_action_leave.md) 의 § 1·2·3·4·5·6·7·8·10·11·12 를 코드로 옮김.
- 자연어 휴무 등록 백엔드 3 엔드포인트 (`parse` / `preview` / `execute`) 구현.
- 할루시네이션 가드 13 항 (spec § 11) 전부 매핑.
- HMAC-SHA256 토큰 (TTL 120 초, 메모리 secret) 발급/검증.
- TOCTOU 가드 (트랜잭션 안 재조회).
- 기존 `POST /api/employee-leaves` 의 upsert 로직을 `_upsert_employee_leave_core` 헬퍼로 추출하여 재사용 (단일 진실원천).
- AiUsageLog (모든 호출) + AuditLog (execute 성공 시만) 기록.
- mock provider 기반 단위/통합 테스트 (T1 ~ T29 + 회귀).

### 사용자 결정 사항 (spec 04 와 다름)

12 세션 spec 과 다른 부분 — AskUserQuestion 응답에 따라 다음 3 개 항목을 13 세션에서 적용:

| 항목 | spec 04 | 13 세션 적용 |
|---|---|---|
| 엔드포인트 개수 | 2 개 (preview, execute) | **3 개 (parse, preview, execute)** |
| 경로 prefix | `/api/ai/action/leave/*` | **`/api/ai/action/*`** |
| intent 식별자 | `leave.create` | **`create_therapist_leave`** |

`parse` 는 LLM 추출만 하는 read-only 엔드포인트 (DB 미접근, 토큰 발급 안 함). `preview` 는 text 만 입력으로 받아 LLM 을 다시 호출 — `parse` 결과를 신뢰하지 않는 설계.

### spec 정정 사항

spec § 6.2 의 `Appointment.status != "cancelled"` (영국식 2L) 는 오타. 실제 DB 값은 `"canceled"` (미국식 1L) — [models.py:19](../app/models/models.py:19) `APPT_STATUSES = ("reserved", "approved", "canceled")`. 코드는 `"canceled"` 사용 + spec 본문도 정정.

### 완료 여부

- ✅ 완료. 신규 35 테스트 + 회귀 전부 PASS. ruff 0 에러. DB 경로 안전검사 통과.

### 수정 파일

신규:
- [app/services/ai/date_resolver.py](../app/services/ai/date_resolver.py) — spec § 3 의 날짜 해석 표를 결정론적 함수로. `Asia/Seoul` 고정 (Windows 에서 zoneinfo 실패 시 +09:00 fallback).
- [app/services/ai/action_leave.py](../app/services/ai/action_leave.py) — parse / preview / execute 본체 + 가드 13 항 + HMAC 토큰 + TOCTOU 재조회.
- [tests/test_ai_action_leave.py](../tests/test_ai_action_leave.py) — T1 ~ T29 + 입력 게이트 + 회귀 (총 35 테스트).

수정:
- [app/routers/ai.py](../app/routers/ai.py) — 3 엔드포인트 (`/action/parse`, `/action/preview`, `/action/execute`) + `_action_leave_provider` dependency 추가. import 1 줄 추가.
- [app/routers/api.py](../app/routers/api.py) — `_upsert_employee_leave_core(db, p)` 헬퍼 추출. 기존 `POST /api/employee-leaves` 라우터는 헬퍼 호출 + commit 으로 단순화. 동작 동일.
- [tests/conftest.py](../tests/conftest.py) — `FakeProvider` 와 `make_fake_provider()` 팩토리 공용화 (이전 세션의 `tests/test_ai_sms_draft.py` inline 버전과 동일 인터페이스, 추가로 `return_text` callable 지원).

### 추가 API

| 메서드 + Path | 설명 |
|---|---|
| `POST /api/ai/action/parse` | 자연어 → LLM JSON 추출. **DB 미접근, 토큰 발급 안 함.** 디버깅·투명성용. |
| `POST /api/ai/action/preview` | LLM 추출 + DB 매칭/충돌 체크 + HMAC 토큰 발급. **DB write 절대 없음.** |
| `POST /api/ai/action/execute` | confirm + 토큰 검증 + TOCTOU 재조회 + EmployeeLeave upsert + AuditLog. |

모두 `require_admin` (X-Admin-Token) 게이트. AI 비활성/Key 미설정 → 503. parse/preview 차단 시 200 + `safe_to_execute=false`. execute 차단 시 400 (token/confirm 류) 또는 409 (TOCTOU).

### 기존 휴무 API 재사용 여부

✅ 재사용. [app/routers/api.py](../app/routers/api.py) 의 `_upsert_employee_leave_core(db, p) -> EmployeeLeave` 헬퍼를 추출하여 양쪽 (`POST /api/employee-leaves` 라우터, `action_leave.execute`) 에서 호출. 단일 진실원천. 기존 라우터의 응답 형식·sync 로깅·동일 키 upsert 동작은 변경 없음.

### 테스트 결과

- 신규 [tests/test_ai_action_leave.py](../tests/test_ai_action_leave.py): **35 PASS** (T1 ~ T29 + 입력 게이트 4 + 회귀 1 + parse 검증 2).
- 회귀 [tests/test_therapist_leave.py](../tests/test_therapist_leave.py): **9 PASS + 4 XFAIL** (기존 그대로).
- 회귀 [tests/test_ai_sms_draft.py](../tests/test_ai_sms_draft.py): **10 PASS** (FakeProvider 공용화 후에도 inline 버전 유지 — 회귀 0).
- 전체 하네스 (`run_check.bat`):
  - `pytest tests -v`: **167 PASS / 1 skip / 7 XFAIL / 27 warnings**.
  - `ruff check app tests scripts`: **All checks passed** (0 errors).
  - `scripts/check_db_path.py`: 통과 (운영 DB 경로 미접근 확인).

### 다음 세션 진행 가능 여부

- ✅ **Yes.** 14 세션 (UI) 진입 가능. 백엔드는 완전 동작 — UI 가 호출만 하면 됨.
- 14 세션 시작 시 결정 필요:
  - UI 위치 A/B 안 (spec § 9.1: 휴무일 관리 영역 vs 메인 우측 사이드 패널). plan 문서 권장은 A 안 (휴무일 관리 영역).
  - `parse` 엔드포인트 노출 여부. UI 에서 사용자에게 노출하지 않고 디버깅 도구로만 둘지, 아니면 "분석" 버튼이 parse → 사용자가 결과 보고 → preview 클릭 흐름으로 갈지.

### 남은 위험

- **LLM rate limit 미적용** — 14 또는 15 세션에서 admin token 별 분당 N 회 인메모리 카운터 추가 권장 (spec § 14). 13 세션 범위 외.
- **`overwrite_not_acknowledged` outcome 코드 (26자) 가 `AiUsageLog.outcome` 컬럼 (String(20)) 길이 초과** — `ai_logging.py:104,107` 에서 자동 truncate (`overwrite_not_acknow` 로 저장됨). API 응답에는 full 값 그대로 반환. DB 추적엔 영향 없으나 향후 outcome 컬럼 확장이 필요할 수 있음.
- **PII 가드의 birth 패턴이 ISO 날짜와 충돌** — 휴무 등록 컨텍스트에서 `2024-01-01` 같은 입력이 birth 패턴으로 오탐되어 차단되는 문제. 13 세션에서 `_pre_gate` 가 phone/rrn 만 차단하고 birth 는 무시하도록 조정 (spec § 10.3 의 "환자 PII 는 흐름에 들어오지 않으므로 자연 제외" 와 일치). 다른 흐름 (sms_draft 등) 의 PII 가드는 영향 없음.
- **HMAC server_secret 은 메모리 only — 프로세스 재시작 시 모든 미완료 토큰 무효화.** spec § 7.2 의 의도된 동작. 단독 실행형이라 다중 워커 / 로드밸런서 이슈 없음.
- **동시성 (TOCTOU) 은 트랜잭션 안 재조회로 처리** — DB 레벨 UNIQUE (employee_id, leave_date) 제약 미추가. 단일 워커 환경에서는 충분하지만, 향후 다중 워커 도입 시 마이그레이션으로 UNIQUE 추가 검토 필요.

---

## 세션 14 — AI업무실행_휴무등록_UI

### 목표 (구체)

- [docs/ai_action_leave_plan.md](ai_action_leave_plan.md) § 8 + [spec 04](specs/04_ai_action_leave.md) § 9 의 UI 와이어프레임을 코드로 옮김.
- 치료사 탭 → 휴무일 관리 서브탭에 "AI 휴무 등록" 카드 1 개 추가.
- 사용자 입력 → `POST /api/ai/action/preview` → 미리보기 카드 → 사용자 명시 클릭 → `POST /api/ai/action/execute` 흐름.
- 안전 원칙: "휴무 등록하기" 클릭 전 execute 호출 절대 금지, `safe_to_execute=false` 면 등록 버튼 비활성, mode=overwrite 시 별도 체크박스 강제.
- 기존 휴무 캘린더 / 직원 관리 / SMS AI 초안 / AI 도우미 / 관리자 AI 설정 UI 비파괴.

### UI 위치 결정 (spec § 9.1 A 안 채택)

- 치료사 탭 (`#tab-therapists`) → 휴무일 관리 서브탭 (`#therapist-leave`) 의 `.sheet` 컨테이너 바로 아래에 새 `.ai-leave-card` 추가 ([app/templates/main.html:160](../app/templates/main.html:160) 부근).
- B 안 (메인 우측 사이드 패널) 은 작업 컨텍스트와 거리가 멀어 채택 안 함. 추후 다른 AI 액션이 늘어나면 재검토.
- Alpine.js 사용 안 함 — 기존 main.html 컨벤션이 plain JS + `onclick` + 전역 함수이므로 동일 패턴 적용 (`adminFetch` 헬퍼 재사용, [main.html:771](../app/templates/main.html:771)).

### 완료 여부

- ✅ 완료. dev 서버에서 4 시나리오 (T1 정상 / T4 일자만 / T5 모호 / T6 반차 모호) + Overwrite (T13) + 입력 게이트 검증 통과. 회귀 167 PASS.

### 수정 파일

- 갱신: [app/templates/main.html](../app/templates/main.html)
  - HTML: `#therapist-leave` 의 `.sheet` 안 마지막에 `.ai-leave-card` 카드 1 개 추가 (사용자 안내 문구 / textarea / 분석 버튼 / 미리보기 그리드 / assumption 박스 / warnings 박스 / memo 입력 / overwrite 체크박스 / 취소·등록 버튼).
  - JS: `_aiLeaveLastPreview` 전역 변수 + 7 함수 (`_aiLeaveTypeLabel`, `_aiLeaveKindLabel`, `aiLeaveOnInput`, `aiLeaveReset`, `aiLeaveSyncSubmitButton`, `aiLeaveRenderPreview`, `aiLeaveAnalyze`, `aiLeaveSubmit`). 위치: `loadTherapistLeaves` 다음.
- 갱신: [app/static/css/app.css](../app/static/css/app.css)
  - 끝부분에 `.ai-leave-*` 클래스 묶음 추가 (보라/하늘 카드 + 노란 assumption 박스 + 빨간 warnings 박스 + 핑크 overwrite 박스). 600px 이하 모바일 반응형 1 열 그리드 추가. 기존 `.sheet` / `.badge` 와 충돌 없음.
- 갱신: [docs/ai_action_leave_session_log.md](ai_action_leave_session_log.md) (본 섹션).
- **수정 안 함**: [app/routers/ai.py](../app/routers/ai.py), [app/services/ai/action_leave.py](../app/services/ai/action_leave.py), [app/services/ai/date_resolver.py](../app/services/ai/date_resolver.py) (13 세션 백엔드 그대로). [tests/test_ai_action_leave.py](../tests/test_ai_action_leave.py) (15 세션 영역). 예약문자 AI ([main.html:240-260](../app/templates/main.html:240)), AI 도우미 탭 ([main.html:286-319](../app/templates/main.html:286)), 관리자 AI 설정 (별도 영역).

### 추가 API

- 없음 (UI 만 추가). 기존 13 세션 3 엔드포인트 (`POST /api/ai/action/{parse,preview,execute}`) 그대로 사용.

### API 연결 함수명

| UI 함수 | 호출 API | HTTP 메서드 |
|---|---|---|
| `aiLeaveAnalyze()` | `/api/ai/action/preview` | POST |
| `aiLeaveSubmit()` | `/api/ai/action/execute` | POST |
| `aiLeaveReset()` | (호출 없음 — 클라이언트 상태만 리셋) | — |

`parse` 엔드포인트는 디버깅용으로 백엔드 보존 — UI 에서 호출 안 함.

### 등록 버튼 활성/비활성 조건

분석 버튼 (`#ai-leave-analyze-btn`):
- 입력 textarea 길이가 1 자 이상 200 자 이하일 때만 활성.

휴무 등록하기 버튼 (`#ai-leave-submit-btn`) — 다음을 **모두** 만족할 때만 활성:
1. `_aiLeaveLastPreview` 가 존재.
2. `_aiLeaveLastPreview.safe_to_execute === true` (백엔드가 토큰 발급한 경우만 true).
3. `mode !== "overwrite"` 이거나 `#ai-leave-overwrite-ack` 체크됨.

### 경고 / 안내 매핑 (사용자 요구사항 5 항)

| 사용자 명시 경고 | 백엔드 제공 채널 | UI 표시 |
|---|---|---|
| 월 생략 → 현재 월 기준 | `candidate.assumption` | 노란 강조 박스 (🗓 아이콘) |
| 이미 휴무 있음 | `mode in {overwrite, noop}` + warnings | warnings 박스 + status (overwrite 시 체크박스) |
| 해당 날짜 예약 있음 | `appointments_count > 0` + warnings | warnings 박스 |
| 치료사명 불명확 | `outcome ∈ {no_match, multi_match, inactive_therapist, not_therapist}` + `safe_to_execute=false` | 카드 위 status 에러 |
| 반차 오전/오후 불명확 | `outcome === ambiguous_half_day` + `safe_to_execute=false` | 카드 위 status 에러 |

상단 안내 문구 (요구사항대로 그대로 표기): "AI가 분석한 내용입니다. 실제 등록 전 치료사, 날짜, 휴무 유형을 반드시 확인하세요. 애매한 내용은 자동 등록되지 않습니다."

### 기존 UI 영향 여부

- 휴무일 관리 캘린더 / 직원 관리 / 휴무 등록 모달 : 영향 없음 (DOM 추가만, 기존 함수·ID 미변경).
- SMS AI 초안 (`btn-sms-aidraft`, [main.html:242](../app/templates/main.html:242)) : 미수정 확인.
- AI 도우미 탭 (`#tab-ai-manual`, [main.html:286](../app/templates/main.html:286)) : 미수정 확인.
- 관리자 AI 설정 (`/api/ai/settings` 화면) : 미수정 확인.
- dev 서버 콘솔 에러 : **0 건**.
- 전역 함수 무결성 검사: `loadLeaveCalendar` / `loadTherapistLeaves` / `openLeaveModal` / `saveLeaveDay` / `smsAiDraftChecked` / `smsValidateChecked` / `adminFetch` 모두 정상.

### 테스트 결과

dev 서버 시연 (mock preview 응답으로 렌더링 로직 검증):

| 시나리오 | 입력 / 응답 모드 | UI 동작 | 결과 |
|---|---|---|---|
| **T1 정상** | "김테스트치료사 4월30일 종일 연차" / mode=create, safe=true | 미리보기 카드 표시, assumption 숨김, 등록 버튼 활성, status=ok | ✅ |
| **T4 일자만** | "김테스트치료사 30일 월차" / assumption="월이 생략되어 …", leave_kind=monthly | assumption 노란 박스 표시, 휴무 종류=월차, 등록 버튼 활성 | ✅ |
| **T5 모호** | "김치료사 말일쯤 휴무" / outcome=ambiguous_date, candidate=null, safe=false | 카드 숨김, status 에러 1 줄 (중복 제거됨) | ✅ |
| **T6 반차 모호** | "김테스트치료사 5월30일 반차" / outcome=ambiguous_half_day, safe=false | 카드 숨김, status 에러 | ✅ |
| **T13 Overwrite** | mode=overwrite, warnings 2 건, appt 2 건 | overwrite 체크박스 표시, 미체크 시 등록 버튼 disabled, 체크 시 활성 | ✅ |
| **입력 게이트** | 빈 입력 vs 1 자+ 입력 | 빈 입력 → 분석 버튼 disabled, 입력 후 활성 | ✅ |

회귀 (run_check 동등):

- `pytest tests -v` : **167 PASS / 1 skip / 7 XFAIL / 27 warnings** (13 세션 결과 그대로).
- `ruff check app tests scripts` : **All checks passed** (0 errors).
- `scripts/check_db_path.py` : 통과 (테스트 시 임시 DB 사용 확인).

### 다음 세션 진행 가능 여부

- ✅ **Yes.** 15 세션 (테스트/보안) 진입 가능.
- 백엔드 동작은 13 세션 그대로 — UI 추가가 기존 흐름을 깨지 않음. 15 세션의 통합 테스트 / 토큰 위조 차단 / `run_check.bat` 한 방 통과 / PII 보안 회귀 점검 모두 그대로 진행 가능.
- LLM rate limit 적용 (13 세션 이월 위험) 도 15 세션에서 결정 가능.

### 남은 위험

- **leave_type 값 불일치**: 백엔드 `action_leave.execute` 가 DB 에 `morning`/`afternoon`/`full` 로 저장하는데, 기존 캘린더 ([main.html:947](../app/templates/main.html:947)) 와 휴무 모달 ([main.html:684](../app/templates/main.html:684)) 은 `am`/`pm`/`full` 을 사용. AI 로 등록한 반차는 기존 캘린더에서 "종일" 로 표시될 수 있음 (else 분기). 14 세션의 UI 자체는 양쪽 모두 한국어 매핑하지만, 다른 화면과의 일관성은 깨짐. **15 세션 또는 후속 백엔드 patch 필요**: 1) `_map_leave` 가 `am`/`pm` 으로 바꾸거나, 2) 기존 UI 가 `morning`/`afternoon` 도 인식하도록 보강. spec § 4.1 은 morning/afternoon 을 표준으로 명시했으므로 후자가 더 정합적.
- **dev 서버 시연은 mock 응답으로 진행**: 실제 OpenAI/Anthropic 호출은 admin token + API key 가 필요. mock 으로 렌더링·상태 전이는 모두 검증했으나, 실제 LLM 응답 파싱·토큰 발급의 end-to-end 는 15 세션 통합 테스트에서 본격 점검.
- **LLM rate limit 미적용**: 13 세션 이월. 15 세션에서 admin 토큰별 분당 N 회 인메모리 카운터 검토.
- **Token 만료 카운트다운 미표시**: spec § 9.3 1 차 보류 결정대로, 만료는 execute 시 outcome `token_expired` 로 처리. 사용자에게는 "분석 결과가 만료되었습니다 (2 분 초과)" 메시지 + 재분석 유도.
- **동명이인 라디오 선택 UI 없음**: spec § 9.3 1 차 보류대로, multi_match 는 차단 + 사용자 재입력. 14 세션 범위 외.

---

## 세션 15 — AI업무실행_휴무등록_테스트보안

### 목표 (구체)

- 사용자가 명시한 22 개 검증 항목을 자동화 테스트로 모두 커버.
- AI 가 DB 를 우회로 수정할 수 없는지 (parse/preview read-only, execute 는 토큰+confirm 필수).
- 할루시네이션이 DB 에 반영되지 않는지 (가드 13 항 모두 자동화 검증).
- 환자/예약 개인정보가 LLM 으로 전송되지 않는지 명시 검증.
- 기존 휴무 / 예약 / 문자 / 환자 / 통계 / 백업 / 동기화 기능이 깨지지 않았는지.
- 사전 분석에서 발견된 **명백한 호환성 버그 1 건** 처리: 백엔드가 DB `leave_type` 에 `morning`/`afternoon` 으로 저장 → 기존 캘린더 / `fetchLeavesOn()` 은 `am`/`pm` 만 인식 → AI 로 등록한 오전반차가 캘린더에서 "종일" 로 표시되고 휴무 차단 작동 안 함 (운영 위험).
- `run_check.bat` 한 방 통과 + 앱 부팅 smoke + 배포 가능 명시.

### 사용자 결정 사항 (15 세션)

호환성 버그 fix 방향: **백엔드를 `am` / `pm` / `full` 로 통일** (spec 04 § 4.1 의 `morning`/`afternoon` 표기는 spec 작성 단계의 오해 — 실제 DB / 기존 API 표준은 `am`/`pm`). 변경 8 곳, 코드 위주, UI 무변경. spec 헤더에 정정 ⓘ 박스 1 줄 추가.

### 완료 여부

- ✅ 완료. 신규 5 테스트 + 기존 35 = 40 PASS, 회귀 172 PASS / 1 skip / 7 XFAIL. ruff 0 errors. DB 경로 안전. 앱 부팅 smoke 104 routes (변동 없음).

### 수정 파일

코드:
- [app/services/ai/action_leave.py](../app/services/ai/action_leave.py) — `_map_leave()` (337-343), `_leave_label()` (401-403), `_VALID_LEAVE_TYPE` (461) 의 `morning`/`afternoon` → `am`/`pm` 통일.
- [tests/harness/seed_data.py](../tests/harness/seed_data.py) — `LEAVE_TYPE_BY_THERAPIST` 의 `morning` → `am`, `afternoon` → `pm`.

테스트:
- [tests/test_ai_action_leave.py](../tests/test_ai_action_leave.py)
  - 기존 어서션 갱신: T2 (228), T3 (249), T13 (418), T22 (640), T23 (678), `test_regression_legacy_leave_api` (915-939) — 모두 `am`/`pm` 표기로 정합화.
  - 신규 5 테스트 추가:
    - `test_T_multi_match_blocked` — 동명이인 active 치료사 2 명 시드 → preview multi_match 차단 + 토큰 미발급.
    - `test_T_partial_name_rejected` — 부분 이름 ("김테스트") → no_match (자동 선택 금지).
    - `test_T_day_before_today_ambiguous` — today=4/28 인데 입력 "20일" → ambiguous_date (다음달 자동 보정 금지).
    - `test_no_patient_or_appointment_pii_in_llm_prompt` — 환자 + 예약 시드 후 preview → `FakeProvider.calls` 의 prompt/system 안에 환자명·전화·생년월일·차트번호·예약id·메모 모두 미존재 단언.
    - `test_T_random_payload_with_bad_sig_blocked` — valid base64 페이로드 + 잘못된 시그니처 → 400 token_signature.
- [tests/test_smoke.py](../tests/test_smoke.py) — `test_get_employee_leaves` 의 시드 휴무 3 종 어서션을 `{full, am, pm}` 으로 갱신.

문서:
- [docs/ai_action_leave_plan.md](ai_action_leave_plan.md) — 헤더에 "세션 15 정정 사항" ⓘ 박스 추가 (DB 표준 `am`/`pm`/`full` 명시).
- [docs/specs/04_ai_action_leave.md](specs/04_ai_action_leave.md) — 헤더 ⓘ 박스에 leave_type 표기 정정 1 줄 추가.
- [docs/ai_action_leave_session_log.md](ai_action_leave_session_log.md) — 본 § + 진행 요약 표 마지막 행.

수정 안 함 (의도적):
- [app/routers/ai.py](../app/routers/ai.py) — 라우터 그대로 (인터페이스 무변경).
- [app/routers/api.py](../app/routers/api.py) — `_upsert_employee_leave_core` 그대로 (DB write 단일 진실원천 유지).
- [app/services/ai/date_resolver.py](../app/services/ai/date_resolver.py) — 그대로.
- [app/templates/main.html](../app/templates/main.html), [app/static/css/app.css](../app/static/css/app.css) — UI 무변경 (14 세션 그대로).
- [tests/conftest.py](../tests/conftest.py) — `FakeProvider` 그대로.

### 추가 API

- 없음 (15 세션 작업 전 의도). 13 세션 3 엔드포인트 그대로.

### 테스트 결과

전체 회귀 (run_check.bat 동등):

| 단계 | 명령 | 결과 |
|---|---|---|
| pytest | `venv\Scripts\python.exe -m pytest tests -v` | **172 PASS / 1 skip / 7 XFAIL / 27 warnings** (5 신규 + 167 기존) |
| ruff | `venv\Scripts\python.exe -m ruff check app tests scripts` | **All checks passed** (0 errors) |
| DB 경로 안전 | `venv\Scripts\python.exe scripts\check_db_path.py` | **통과** (테스트는 임시 DB 사용 확인) |
| 앱 부팅 smoke | `python -c "from app.main import app; print(len(app.routes))"` | **104 routes / boot ok** (마이그레이션 1~10 정상) |

신규 5 테스트만 따로:

| 테스트 | 결과 |
|---|---|
| `test_T_multi_match_blocked` | ✅ multi_match outcome + 토큰 미발급 검증 |
| `test_T_partial_name_rejected` | ✅ "김테스트" → no_match (부분일치 거부 검증) |
| `test_T_day_before_today_ambiguous` | ✅ "20일" today<28 → ambiguous_date (자동 보정 금지) |
| `test_no_patient_or_appointment_pii_in_llm_prompt` | ✅ 환자명·전화·생년월일·차트번호·예약id·메모 모두 LLM prompt 미포함 |
| `test_T_random_payload_with_bad_sig_blocked` | ✅ valid base64 + 잘못된 sig → 400 token_signature |

회귀 영향:
- 기존 `test_therapist_leave.py`: 9 PASS + 4 XFAIL (변동 없음).
- 기존 `test_employee_leave_kind.py`: PASS (am/pm/full DB 표준 그대로).
- 기존 `test_appointment_rules.py` / `test_stats_counts.py` / `test_ai_sms_*` / `test_db_restore_safety.py`: 모두 PASS.
- 기존 `test_smoke.py`: `test_get_employee_leaves` 어서션 갱신 (시드 표준 일치) → PASS.

### 22 항목 검증 매트릭스

| # | 사용자 요구 | 자동화 위치 | 결과 |
|---|---|---|---|
| 1 | parse | `test_parse_endpoint_returns_candidate` | ✅ |
| 2 | preview | T1 / T4 등 다수 | ✅ |
| 3 | execute | T1 | ✅ |
| 4 | confirm=false 차단 | T21 | ✅ |
| 5 | preview 없이 execute 차단 | T16 / T17 + 신규 `test_T_random_payload_with_bad_sig_blocked` | ✅ |
| 6 | 치료사 없음 | T10 | ✅ |
| 7 | 동명이인 차단 | 신규 `test_T_multi_match_blocked` | ✅ |
| 8 | 비슷한 이름 임의 선택 금지 | 신규 `test_T_partial_name_rejected` | ✅ |
| 9 | 이미 휴무 있음 (overwrite/noop) | T13 / T14 | ✅ |
| 10 | 예약 있음 warning | T15 | ✅ |
| 11 | full / am / pm 변환 | T1 / T2 / T3 (어서션 갱신됨) | ✅ |
| 12 | "반차" 만 → 실행 불가 | T6 | ✅ |
| 13 | "30일" 현재 월 기준 변환 | T4 | ✅ |
| 14 | 현재 월에 없는 (D < today.day) 차단 | 신규 `test_T_day_before_today_ambiguous` | ✅ |
| 15 | 애매한 날짜 차단 | T5 | ✅ |
| 16 | AuditLog 기록 | T1 | ✅ |
| 17 | AiUsageLog 기록 | T1 | ✅ |
| 18 | 환자 개인정보 LLM 전송 없음 | 신규 `test_no_patient_or_appointment_pii_in_llm_prompt` | ✅ |
| 19 | 예약 상세정보 LLM 전송 없음 | 신규 `test_no_patient_or_appointment_pii_in_llm_prompt` | ✅ |
| 20 | 기존 휴무 등록 기능 정상 | `test_regression_legacy_leave_api` + 기존 `test_employee_leave_kind.py` / `test_therapist_leave.py` | ✅ |
| 21 | 기존 예약 생성/수정 정상 | `test_appointment_rules.py` 외 (회귀 PASS) | ✅ |
| 22 | 기존 예약문자 기능 정상 | `test_ai_sms_validate.py` / `test_ai_sms_draft.py` (회귀 PASS) | ✅ |

### 보안 / 할루시네이션 / 우회 방지 확인

- **AI 우회 차단**: parse / preview 호출 후 EmployeeLeave count 불변 (`test_parse_endpoint_returns_candidate`, `test_preview_does_not_write_db`).
- **execute 차단 7 종**: confirm=false / token=빈 / 위조 / 만료 / unsafe / mismatch / overwrite_not_acknowledged 모두 400 (T16~T22 + 신규 random payload sig).
- **할루시네이션 가드 13 항**: 입력 키워드/길이 (gate), JSON 파싱, Pydantic strict, intent 검증, confidence, substring 6·7, 날짜 결정론, 매칭 결정론, 모호 차단, 토큰 HMAC, TOCTOU, confirm + ack — 모두 자동화 (T1~T29 + 신규 multi_match / partial_name / day<today).
- **PII 미전송**: 환자명·전화·생년월일·차트번호·예약id·예약 메모가 LLM prompt 에 절대 들어가지 않음 (신규 `test_no_patient_or_appointment_pii_in_llm_prompt`).
- **TOCTOU**: 트랜잭션 안 재조회로 conflict_changed / therapist_changed 검증 (T23 / T24).

### 호환성 fix 검증

- 백엔드 `_map_leave()` 가 `am`/`pm`/`full` 반환 → DB 컬럼 `leave_type` 표준과 일치.
- AI 로 등록한 오전반차가 DB 에 `am` 으로 저장되어 기존 캘린더 ([main.html:1223,1291](../app/templates/main.html:1223)) 에서 "오전" 으로 정상 표시.
- `fetchLeavesOn()` ([main.html:2381,2382](../app/templates/main.html:2381)) 의 `am` / `pm` 분기가 정상 작동 → 휴무 시간대 예약 차단 회복.
- 시드 `LEAVE_TYPE_BY_THERAPIST` 도 `am`/`pm`/`full` 로 통일 → `test_get_employee_leaves` smoke 와 일치.

### 다음 세션 진행 가능 여부

- ✅ **Yes — 배포 빌드 진행 가능**. 본 4 개 세션 (12~15) 의 모든 목표 달성. 후속 작업은 별도 플랜에서 다룬다.
- 배포 게이트 4 항 모두 PASS:
  1. `run_check.bat` 동등 (pytest + ruff + DB 안전) 통과.
  2. 앱 부팅 smoke OK (104 routes).
  3. 22 항목 검증 매트릭스 전부 ✅.
  4. UI 무변경 → 회귀 부재 (14 세션 시연 결과 그대로 유효).

### 배포 전 체크리스트

코드/문서 자유 수정 단계 산출물은 모두 정리됨:
- `app/config.py` APP_VERSION 갱신 (배포 직전, 사용자 동의 후).
- `CHANGELOG.txt` / `VERSION.txt` 갱신 (배포 직전).
- `versions/INDEX.txt` 신 버전 블록 추가 (배포 직전).

이후 사용자 동의 받은 후에만:
- PyInstaller 빌드 → ZIP → GitHub Release → manifest.json push.

### 남은 위험

- **`outcome` 컬럼 길이 truncate**: `overwrite_not_acknowledged` (26자) > `String(20)` → ai_logging.py 가 자동으로 `overwrite_not_acknow` 로 저장. API 응답엔 full 값 그대로. DB 추적엔 영향 없음. 마이그레이션 추가는 후속 작업.
- **LLM rate limit 미적용**: 단독 실행형 + admin 전용이라 운영상 폭주 위험 매우 낮음. 후속 플랜에서 인메모리 카운터 검토 가능.
- **동명이인 라디오 선택 UI 없음**: 1차 보류 (multi_match 차단 + 사용자 재입력). 후속 UX 개선 영역.
- **토큰 만료 카운트다운 UI 미표시**: 1차 보류 (만료 시 outcome `token_expired` + 재분석 유도). 후속 UX 개선 영역.
- **HMAC server_secret 메모리 only**: 프로세스 재시작 시 미완료 토큰 무효화. spec § 7.2 의 의도된 동작 — 단독 실행형이라 다중 워커 / 로드밸런서 이슈 없음.
- **TOCTOU 는 트랜잭션 안 재조회**: DB 레벨 UNIQUE (employee_id, leave_date) 제약 미추가. 단일 워커 환경에서 충분. 향후 다중 워커 도입 시 마이그레이션 검토.

---

## 세션 16 — AI_RAG_휴무등록_최종테스트_검증

### 목표 (구체)

- 사용자 명시 ~110 항 검증 매트릭스 (AI/RAG + AI 휴무등록 + 보안 + 회귀 + 빌드 사전점검) 자동화로 전수 검증.
- 본 세션은 새 기능 / UI 개선 금지 — 검증 + 명백한 버그만 최소 fix.
- 발견된 4건 진단 → 사용자 동의 후 #1 (High, PII pre-gate 보강) 만 본 세션에서 fix. 나머지 3건은 17 세션 이월.

### 발견된 4건 (진단 결과)

| # | 심각도 | 문제 | 처리 |
|---|---|---|---|
| 1 | High | `_pre_gate` 가 phone/rrn 만 차단 → birth/chart_no_maybe/환자 정보가 LLM prompt 로 새어나갈 수 있음 | ✅ 본 세션 fix |
| 2 | Medium | `/api/ai/health` 가 admin 전용 → 비-admin 화면 health 조회 401. UI fallback 은 동작 중이나 분리가 더 명확 | ⏸ 17 세션 이월 |
| 3 | Medium | `EmployeeLeave` 에 `(employee_id, leave_date)` UNIQUE 제약 없음 — 다중 워커 race 위험 | ⏸ 17 세션 이월 (마이그레이션 m011) |
| 4 | Low | `AiUsageLog.outcome = String(20)` → `overwrite_not_acknowledged` (26자) truncate | ⏸ 17 세션 이월 (마이그레이션) |

### 사용자 결정 사항 (16 세션)

- **A/B/C/D 옵션 중 B 선택**: #1 만 본 세션 fix, #2~#4 는 17 세션으로 이월. 본 세션 코드 변경 최소화 원칙 준수.

### 완료 여부

- ✅ 완료. 신규 3 + 기존 40 = 43 PASS, 회귀 175 PASS / 1 skip / 7 XFAIL. ruff 0 errors. DB 경로 안전. 앱 부팅 OK (104 routes).

### 수정 파일

코드:
- [app/services/ai/action_leave.py](../app/services/ai/action_leave.py)
  - **상수 추가** (라인 52 부근): `_PATIENT_INDICATORS = ("환자", "차트", "카르테", "차트번호", "내원", "방문", "chart")`.
  - **`_pre_gate` 강화** (라인 184~198 부근): 기존 phone/rrn 차단에 더해 다음 추가 조건이 하나라도 매치되면 `pii_blocked` 반환:
    1. `chart_no_maybe` (5~10자리 순수 숫자) 매치 → 차트번호 의심.
    2. `_PATIENT_INDICATORS` 키워드 등장 → 환자 정보 동반 의심.
    3. birth (YYYY-MM-DD / YYYYMMDD) 패턴 **2회 이상** 매치 → 1회는 휴무 날짜로 통과, 2회 이상이면 환자 생년월일 동반 의심.

테스트:
- [tests/test_ai_action_leave.py](../tests/test_ai_action_leave.py) — `test_pii_blocked_phone` 직후 신규 3 테스트 추가:
  - `test_pii_blocked_chart_no` — `김테스트치료사 4월30일 휴무 123456` → outcome=pii_blocked, LLM 호출 0회.
  - `test_pii_blocked_patient_keyword` — `김테스트치료사 4월30일 휴무 환자 홍길동` → outcome=pii_blocked.
  - `test_pii_blocked_double_birth` — `김테스트치료사 2026-04-30 휴무 1990-05-15` → outcome=pii_blocked (1회는 휴무 날짜, 2회 이상이면 차단).

문서:
- [docs/ai_action_leave_session_log.md](ai_action_leave_session_log.md) — 본 § 16 추가 + 진행 요약 표 마지막 행 추가.

수정 안 함 (의도적):
- [app/routers/ai.py](../app/routers/ai.py), [app/routers/api.py](../app/routers/api.py) — 라우터/헬퍼 그대로 유지.
- [app/services/ai/pii.py](../app/services/ai/pii.py) — 패턴은 그대로, 사용처 (`_pre_gate`) 만 강화.
- [docs/specs/04_ai_action_leave.md](specs/04_ai_action_leave.md) — spec § 10.3 의 "환자 PII 자연 제외" 의도는 보존, action_leave 흐름의 추가 방어선만 코드/테스트로 보강 (spec 본문 변경 없음).
- UI ([app/templates/main.html](../app/templates/main.html), [app/static/css/app.css](../app/static/css/app.css)) — 변경 없음.

### 추가 API

- 없음 (검증 + pre-gate 보강).

### 검증 결과

| 단계 | 명령 | 결과 |
|---|---|---|
| pytest 전체 | `pytest tests -v` | **175 passed / 1 skipped / 7 xfailed / 27 warnings** (15 세션 172 + 신규 3) |
| pytest action_leave | `pytest tests/test_ai_action_leave.py` | **43 passed** (15 세션 40 + 신규 3) |
| ruff | `ruff check app tests scripts` | **All checks passed** (0 errors) |
| DB 경로 안전 | `scripts/check_db_path.py` | 통과 (테스트 시 임시 DB 사용 확인) |
| 앱 부팅 | `python -c "from app.main import app; print(len(app.routes))"` | **104 routes / boot ok** (m001~m010 정상 적용) |

### 사용자 명시 ~110 항 검증 매트릭스

기존 22 항 (15 세션) + AI/RAG 표면 + 보안 + 회귀 + 빌드 사전점검을 한꺼번에 자동화로 통과.

| 카테고리 | 결과 |
|---|---|
| AI/RAG (health/settings/sms validate/sms draft/manual search/manual ask) | ✅ test_ai_logging.py / test_ai_manual_qa.py / test_ai_sms_validate.py / test_ai_sms_draft.py / test_ai_hallucination.py 50 PASS |
| AI 휴무등록 22 항 (T1~T29 + 신규 + 본 세션 PII 3) | ✅ test_ai_action_leave.py 43 PASS |
| 보안 (API Key 마스킹 / PII LLM 미전송 / prompt 본문 미저장 / AI 직접 DB·SMS 불가) | ✅ Grep + 자동 테스트 모두 통과 |
| 기존 기능 회귀 (예약/환자/치료사/휴무/SMS/백업/통계/관리자) | ✅ 64 PASS / 1 skip / 7 XFAIL (변동 없음) |
| 빌드 사전점검 (spec/requirements/version/knowledge) | ✅ requirements.txt openai+anthropic 명시, datas knowledge 포함, APP_VERSION=1.3.2. spec hiddenimports 의 action_leave/date_resolver 누락은 라우터 정적 분석으로 자동 추적되나 일관성 차원 추가 권장 |

### 다음 세션 진행 가능 여부

- ✅ **Yes — 배포 빌드 조건부 가능**.
- 17 세션 (선택) 에서 다음 3건 중 우선순위 높은 것부터 처리:
  1. **#3 (Medium)** EmployeeLeave UNIQUE 제약 추가 — 신규 마이그레이션 m011 + spec hiddenimports 등록.
  2. **#4 (Low)** AiUsageLog.outcome 길이 확장 (20→50) — m011 에 묶거나 별도 m012.
  3. **#2 (Medium)** /api/ai/health public 분리 — 새 엔드포인트 신설.
- 또는 17 세션 없이 **현 상태로 빌드/배포** 도 가능 (#2~#4 는 운영 영향 매우 낮음 / UI fallback 동작 중 / 단독 워커 환경 / outcome truncate 무영향).

### 17 세션 (또는 별도 세션) 으로 전달할 내용

#### 1) #3 EmployeeLeave UNIQUE 제약 (Medium)

- 현재: [app/models/models.py:43-52](../app/models/models.py:43) 의 `EmployeeLeave` 에 UniqueConstraint 없음.
- 작업:
  - 신규 마이그레이션 `app/migrations/m011_employee_leave_unique.py` — 기존 중복 row 정리 (employee_id+leave_date 동일 그룹에서 가장 최근 created_at 1 건만 남김) → UNIQUE 인덱스 생성 (`uq_employee_leave_date`).
  - [dosu_clinic.spec](../dosu_clinic.spec) 글롭 자동 등록이지만, 마이그레이션 추가 후 빌드 테스트 필수.
  - `app/models/models.py` 의 EmployeeLeave 에 `UniqueConstraint("employee_id", "leave_date", name="uq_employee_leave_date")` 추가.
  - 새 테스트: 동시 insert race 시 1건만 살아남는 것 확인 (트랜잭션 + IntegrityError catch).

#### 2) #4 AiUsageLog.outcome 길이 확장 (Low)

- 현재: [app/models/models.py:328](../app/models/models.py:328) `outcome = Column(String(20), default="")`.
- 작업:
  - SQLite 는 `ALTER COLUMN` 미지원 → 새 테이블 생성 + 데이터 복사 + 이름 변경 패턴.
  - #3 와 함께 `m011_schema_extend.py` 에 묶거나 별도 `m012_ai_outcome_extend.py`.
  - 타입을 `String(50)` 으로 확장.
  - 회귀: `overwrite_not_acknowledged` 가 truncate 없이 저장되는지 어서션.

#### 3) #2 /api/ai/health public 분리 (Medium)

- 현재: [app/routers/ai.py:124](../app/routers/ai.py:124) `require_admin` 의존성. UI ([main.html:4581-4606](../app/templates/main.html:4581)) 가 401/403 fallback 처리.
- 작업:
  - `GET /api/ai/health/public` 신설 — 토큰 불필요, `{ enabled, ready, provider }` 만 노출 (api_key_set / sdk_installed 등 admin 정보 제외).
  - `loadAiHealth()` 가 admin 토큰 없을 때 `/public` 호출하도록 변경.
  - 기존 `/api/ai/health` 는 admin 정보까지 포함 그대로 유지.

#### 4) 빌드/배포 (사용자 동의 후)

- spec hiddenimports 에 `app.services.ai.action_leave` / `app.services.ai.date_resolver` 추가 (1줄, 일관성 차원).
- `app/config.py` APP_VERSION 갱신 (1.3.2 → 1.3.3 또는 1.4.0).
- `CHANGELOG.txt` / `VERSION.txt` / `versions/INDEX.txt` 갱신.
- PyInstaller 빌드 → ZIP → GitHub Release → manifest.json push.

#### 5) 후속 (1차 보류 항목 — 보안/품질엔 영향 없음)

- LLM rate limit (admin 토큰별 분당 N 회 인메모리 카운터).
- 동명이인 라디오 선택 UI / 토큰 만료 카운트다운 UI.

### 남은 위험

- **#2/#3/#4 는 모두 운영 영향 매우 낮음 — 배포 막을 정도는 아님.** 17 세션 또는 다음 마이너 릴리즈에서 묶어서 처리 권장.
- **#1 fix 의 오탐 위험**: `_PATIENT_INDICATORS` 키워드 ("환자", "차트", "방문", "내원" 등) 가 정상 휴무 입력에 들어가는 경우는 사실상 없으나, 사용자가 메모 필드 형태로 자연어를 길게 적으면 차단될 수 있음. 메모는 휴무 등록 input 이 아니라 별도 필드라 문제없을 것이나, 운영 중 false positive 신고 1건이라도 발생하면 키워드 리스트 재검토.
- **birth 2회 이상 차단**: 사용자가 "2026-04-30 부터 2026-05-30 까지 휴무" 같은 범위 입력을 시도해도 차단됨. 단, 본 1차 범위가 휴무 1건 한정이라 spec § 3 의 "범위 입력 차단" 정책과 일치.
