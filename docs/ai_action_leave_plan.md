# AI 업무 실행 — 치료사 휴무 등록 (Plan)

본 문서는 세션 12 ~ 15 에 걸쳐 진행되는 **"AI 에게 자연어로 치료사 휴무 등록 시키기"** 기능의 공통 작업 플랜이다.
이후 세션은 이전 세션 요약을 복붙하지 않고 **이 문서를 읽고 이어간다.**

세션 진행 기록은 [docs/ai_action_leave_session_log.md](ai_action_leave_session_log.md) 에 작성한다.
관련 기존 spec: [docs/specs/02_치료사_휴무_규칙.md](specs/02_치료사_휴무_규칙.md).
**세션 12 산출물 (설계 확정):** [docs/specs/04_ai_action_leave.md](specs/04_ai_action_leave.md) — 13 세션부터는 본 spec 을 코드로 옮기기만 하면 된다.

> ⚠️ **세션 13 사용자 결정 사항** (spec 04 와 다름):
> - 엔드포인트 **3 개** (parse / preview / execute) — `parse` 는 LLM 추출만 하는 read-only 엔드포인트로 추가.
> - 경로 prefix **`/api/ai/action/*`** (spec 의 `/api/ai/action/leave/*` 가 아니라 leave 세그먼트 없음).
> - intent 식별자 **`create_therapist_leave`** (spec 의 `leave.create` 가 아니라 snake_case).
>
> 그 외 모든 설계 결정 (날짜 표·매칭·토큰·에러 코드·할루시네이션 가드 13 항·테스트 시나리오) 은 spec 04 그대로 따름.

> ⚠️ **세션 15 정정 사항** (spec 04 § 4.1 정정):
> - DB 컬럼 `leave_type` 값 표준은 **`am` / `pm` / `full`** (기존 캘린더 + `fetchLeavesOn()` 호환).
> - spec 04 § 4.1 의 `morning` / `afternoon` 표기는 spec 작성 단계의 오해 — 실제 DB / 기존 API 표준은 `am` / `pm`.
> - 15 세션에서 `_map_leave()` / `_VALID_LEAVE_TYPE` / `_leave_label()` / 시드 / 테스트 어서션을 모두 `am` / `pm` / `full` 로 통일.

---

## 1. 전체 목표

AI 에게 자연어로 치료사 휴무를 등록시키되, **AI 가 직접 DB 를 만지지 않고** 사람이 검증/승인한 뒤에만 기존 휴무 API 를 통해 반영한다.

- 입력 예: `"김테스트치료사 30일 종일 휴무"`, `"이테스트치료사 내일 오전 반차 (병원)"`
- 출력: 사용자가 미리보기를 확인하고 "이대로 등록" 을 누르면, 기존 `POST /api/employee-leaves` 로 1건이 생성된다.
- 사용자 의도 = "더 빨리 휴무 등록", 기술적 위험 = "할루시네이션으로 잘못된 직원 / 잘못된 날짜에 휴무가 박힘".
- 위험 통제 수단 = **2 단 흐름 (preview → execute)** + **DB 재검증** + **사용자 명시 확인**.

---

## 2. 1차 구현 범위

이번 4개 세션에서 다루는 범위는 다음으로 한정한다.

- 휴무 등록 **1 건**.
- 흐름: `텍스트 입력 → LLM 파싱 → JSON 후보 추출 → DB 매칭/검증 → 미리보기 → 사용자 확인 → 백엔드가 기존 휴무 API 호출`.
- 신규 엔드포인트 prefix: `/api/ai/action/leave/*`.
- DB 변경은 **기존 `EmployeeLeave` 테이블 / 기존 휴무 등록 로직**만 사용. 신규 테이블 / 신규 컬럼 추가 없음.
- LLM provider 는 기존 `app/services/ai/provider.py` 추상 + 기존 OpenAI/Anthropic 클라이언트 재사용.
- 로깅은 기존 `AuditLog` + `AiUsageLog` 사용.

---

## 3. 보류 범위 (1차에 안 함)

다음은 본 4 개 세션에서 **건드리지 않는다.** 추후 별도 플랜으로 다룬다.

- 예약 자동 이동 / 자동 취소 / 자동 문자 발송.
- 관리자 설정 변경 (AiSetting 변경, SMS 설정 변경 등).
- 휴무 외 다른 action (예약 생성, 환자 등록, 통계 변경 등).
- **일괄 등록** ( `"이번 주 월수금 종일"` 같은 다중 휴무 추출 ).
- 음성 입력 / STT.
- 휴무 **수정 / 삭제** 자연어 명령. 1차는 "등록"만.

---

## 4. 핵심 안전 원칙

이 원칙은 세션 12 ~ 15 동안 **절대로 풀지 않는다.**

1. **AI 는 DB 를 직접 수정하지 않는다.** AI 는 후보값을 만들기만 하고, DB 호출은 백엔드 검증 코드만 한다.
2. **parse / preview 는 절대 DB 를 수정하지 않는다 (read-only).** 조회만 한다.
3. **execute 는 `confirm=true` + 직전 preview 검증값 (서버 발급 토큰 또는 해시) 이 함께 있을 때만** 실행한다. 둘 중 하나라도 없으면 차단.
4. **LLM 결과는 후보값일 뿐.** DB / 코드 검증을 통과하지 않은 값은 신뢰하지 않는다.
5. **치료사명은 DB 의 employees 테이블에서 정확히 1 명 매칭** 되어야 한다 (대소문자 / 공백 정규화 후 exact match 1 건). 0 명 / 2 명 이상 → 실행 불가.
6. **사용자 명시 확인 전에는 어떤 DB 변경도 불가.** "방금 분석한 그대로 등록" 버튼 클릭이 사용자 명시 확인이다.
7. **기존 휴무 등록 API / 로직을 재사용한다.** AI 전용 입력 경로를 새로 파지 않는다 — 동일 검증 / 동일 시드 / 동일 차단 로직을 통과시켜야 한다.
8. **모든 시도 / 실행은 `AuditLog` + `AiUsageLog` 에 기록한다.** 실패한 preview 도 기록한다.

---

## 5. 할루시네이션 방지 원칙

LLM 이 자기 확신을 표명해도 다음 원칙을 우선한다.

- **LLM 이 만들어낸 employee_id, 날짜, leave_type 을 그대로 사용 금지.** 이름은 DB 조회로 다시 매칭, 날짜 / 타입은 서버에서 enum / 형식 검증.
- 응답이 JSON 스키마에 안 맞거나 필수 필드가 비면 **즉시 차단.** ( `safe_to_execute=false` )
- 파싱된 의도 (intent) 가 `"leave.create"` 외이면 **차단** (1차 범위 한정).
- 한 발화에서 추출된 휴무가 **2 건 이상이면 1차에서는 차단** (보류 범위).
- LLM 이 "확실합니다" 라고 답해도 DB 매칭 실패 / 날짜 모호 → 무시.
- 의심 신호 (이름 다중 매칭, 날짜 모호, 미래 / 과거 한계 초과, 반차인데 오전 / 오후 미상 등) 가 **하나라도 있으면 실행 차단.** preview 의 `warnings[]` 에 사유를 누적해 사용자에게 전부 보여준다.

---

## 6. 날짜 해석 규칙

서버 시각 기준으로 모든 날짜를 해석한다. LLM 이 해석한 값과 서버 해석값이 다르면 **서버 값 우선.**

| 입력 | 해석 | preview 응답 |
|------|------|------|
| `"2026-05-30"` (절대) | 그대로 사용 | `resolved_date=2026-05-30`, `assumption=null` |
| `"내일"`, `"다음 주 월요일"` (상대) | 서버 현재 시각 기준 계산 | `resolved_date=...`, `assumption="서버 시각 기준"` |
| `"30일"`, `"5월 30일"` (일자만) | **현재 월** (또는 명시된 월) 기준 | `resolved_date=2026-04-30`, `assumption="현재 월 기준"` ⚠️ |
| `"이번 주 어느 날"`, `"곧"`, `"적당한 때"` | 모호 → 실행 불가 | `safe_to_execute=false`, `warnings=["날짜가 모호합니다"]` |

추가 제약:

- **과거 90 일 이전 / 미래 365 일 이후** 는 1 차에서 차단 ( `safe_to_execute=false` ).
- 일자만으로 해석한 경우 미리보기 응답에 `resolved_date` (YYYY-MM-DD) 와 `assumption` 안내 문자열을 **반드시** 포함하고, UI 에서 강조 표시한다.
- "반차" 만 있고 오전 / 오후 표시가 없으면 → 모호 → 실행 불가.

---

## 7. API 설계

신규 엔드포인트 prefix: `/api/ai/action/leave/*` (모두 [app/routers/ai.py](../app/routers/ai.py) 에 추가 예정).

### 7.1 `POST /api/ai/action/leave/preview`

| 항목 | 값 |
|------|------|
| 입력 | `{ "text": "<자연어 발화>" }` |
| 동작 | LLM 호출 → JSON 후보 추출 → DB 매칭 / 검증 → preview 응답 작성 |
| DB 수정 | ❌ 절대 미수정 |
| 로깅 | `AiUsageLog.feature = "action_leave_preview"`, `outcome ∈ {ok, parse_fail, no_match, ambiguous, ...}` |
| 응답 (예시) | 아래 |

```json
{
  "candidate": {
    "intent": "leave.create",
    "employee_name_raw": "김테스트치료사",
    "employee_id": 17,
    "employee_name": "김테스트치료사",
    "resolved_date": "2026-04-30",
    "assumption": "현재 월 기준",
    "leave_type": "full",
    "leave_kind": "annual",
    "memo": ""
  },
  "warnings": [],
  "safe_to_execute": true,
  "preview_token": "<서버 발급 단기 토큰>"
}
```

### 7.2 `POST /api/ai/action/leave/execute`

| 항목 | 값 |
|------|------|
| 입력 | `{ "preview_token": "...", "confirm": true }` |
| 동작 | token 으로 직전 preview 결과 재현 → `safe_to_execute=true` 검증 → 기존 `create_employee_leave` 로직 호출 |
| DB 수정 | ✅ EmployeeLeave 1 건 생성 (또는 동일 키 upsert) |
| 차단 | `confirm != true` / token 없음 / token 만료 / token 으로 재현한 결과가 `safe_to_execute=false` → 400 |
| 로깅 | `AuditLog.action = "ai.leave.create"` (target = leave id, before/after JSON), `AiUsageLog.feature = "action_leave_execute"` |

### 7.3 `GET /api/ai/action/leave/health` (선택, 14 세션)

설정 / 모델 상태 노출. 기존 `GET /api/ai/health` 와 동일한 구조 — provider 와 LLM 호출 가용성, 매칭에 필요한 직원 데이터 존재 여부 등.

---

## 8. UI 설계

### 8.1 위치

메인 화면 (또는 우측 사이드 패널) 에 **"AI 비서" 박스 1 개.**
구현 파일: [app/templates/main.html](../app/templates/main.html) + [app/static/css/app.css](../app/static/css/app.css).
Alpine.js 로 클라이언트 상태 관리.

### 8.2 흐름

1. **입력**: textarea + "분석" 버튼. 비어 있거나 너무 짧으면 버튼 비활성.
2. **분석 (preview)**: 버튼 클릭 → `POST /api/ai/action/leave/preview` 호출 → 로딩 스피너.
3. **미리보기 카드**: 후보값 (치료사 / 날짜 / 유형 / 메모) 을 사람이 읽기 쉬운 형태로 표시.
   - 일자만 해석된 경우 `해석된 날짜: 2026-04-30 (현재 월 기준)` 라인을 **강조 색상 / 아이콘** 으로 표시.
   - `warnings[]` 가 있으면 항목별로 노란 / 빨간 박스에 표시.
4. **확인**: "이대로 등록" / "취소" 버튼.
   - `safe_to_execute=false` → "이대로 등록" 버튼 **비활성** + "차단 사유: ..." 안내.
   - `safe_to_execute=true` → 버튼 활성.
5. **실행 (execute)**: "이대로 등록" 클릭 → `POST /api/ai/action/leave/execute` 호출 → 토스트 성공 / 실패 메시지 + 휴무 화면 자동 새로고침.
6. **취소**: 미리보기 닫기, 입력 textarea 비우기.

### 8.3 안 만드는 것

- 채팅 UI / 멀티턴 대화 / 음성 입력 → 전부 보류 범위.
- 일괄 등록 화면 → 보류 범위.
- preview 결과 수정 (이름 / 날짜 손으로 고치기) → 1 차에서는 안 함. 잘못 분석되면 **취소 → 다시 입력** 흐름만.

---

## 9. 로그 / AuditLog / AiUsageLog 원칙

기존 로깅 헬퍼 그대로 사용. 신규 로그 테이블 추가 없음.

### 9.1 AiUsageLog ( [app/models/models.py:301](../app/models/models.py:301) )

- 모든 `preview` / `execute` 호출에 대해 **1 건씩** 기록.
- prompt / response **본문은 저장하지 않는다.** 해시 (`prompt_hash`, `response_hash`) 와 길이 (`prompt_chars`, `completion_chars`) 만 저장.
- `pii_filter_hits` 에 PII 가드 적중 수 기록.
- `outcome`: `ok` / `parse_fail` / `no_match` / `ambiguous_date` / `ambiguous_half_day` / `out_of_range_date` / `multi_match` / `provider_error` / `pii_blocked` / 기타.
- `error_detail`: 짧은 한국어 요약 (개인정보 미포함).

### 9.2 AuditLog

- `execute` **성공 시에만** 1 건. `action="ai.leave.create"`, `target_type="employee_leave"`, `target_id=<생성된 id>`, `before=null`, `after=<휴무 요약 JSON>`.
- `execute` 실패 (검증 차단 등) 는 AuditLog 안 남기고 AiUsageLog 의 outcome 으로 충분.

### 9.3 사용자 노출 메시지

- 사용자에게 보여주는 에러는 **한국어**, **PII 미포함**.
- 내부 로그 (AiUsageLog.error_detail, server log) 는 충분히 상세 — 단, 환자 / 직원 개인정보는 미포함.

---

## 10. 테스트 기준

기존 하네스 ( [docs/HARNESS.md](HARNESS.md) ) 와 [tests/test_therapist_leave.py](../tests/test_therapist_leave.py) 가 깨지지 않을 것이 전제.

### 10.1 단위 테스트

- LLM 응답 → JSON 스키마 검증 (성공 / 누락 / 형식 오류).
- 치료사 매칭: 0 명 / 1 명 / 2 명 이상 분기.
- 날짜 해석: 절대 / 상대 / 일자만 / 모호 / 과거 90 일 초과 / 미래 365 일 초과.
- 반차 모호 (오전 / 오후 미상) 분기.

### 10.2 API 테스트

- `preview` 호출 후 DB 의 `EmployeeLeave` count 가 변하지 않을 것.
- `execute` 호출:
  - token 없음 → 400.
  - `confirm != true` → 400.
  - token 으로 재현한 결과가 `safe_to_execute=false` → 400.
  - 정상 흐름 → `EmployeeLeave` 1 건 생성 + `AuditLog` 1 건 + `AiUsageLog` 2 건 (preview + execute).

### 10.3 보안 / 위조 테스트

- preview 에서 `safe_to_execute=false` 받은 케이스의 토큰을 그대로 execute 에 보내도 차단.
- 다른 사용자의 token 위조 / 직접 만든 임의 문자열 token → 차단.
- token 만료 시간 초과 → 차단.

### 10.4 회귀

- 기존 `tests/test_therapist_leave.py` 전부 PASS / 기존 XFAIL 그대로 유지.
- `run_check.bat` 통과 (pytest + ruff + DB 경로 안전 검사).

### 10.5 LLM mock

- 실제 OpenAI / Anthropic 호출 금지. 테스트는 **mock provider** 로 결정적 응답.

---

## 11. 세션별 작업 순서

각 세션 종료 시 [docs/ai_action_leave_session_log.md](ai_action_leave_session_log.md) 에 결과 기록 필수.

### 세션 12 — 설계

- 본 plan 문서를 입력으로 받아, 다음을 합의 / 확정.
  - LLM 응답 JSON 스키마 (intent / employee_name_raw / date_raw / leave_type 등) 정확한 키 / 타입.
  - `preview_token` 포맷 / 서명 방식 / 만료 시간.
  - 에러 코드 일람 (outcome 값과 1:1 매칭).
  - 직원 매칭 알고리즘 의사코드 (정규화 규칙, 예: 공백 / 직책 접미사 처리).
  - UI 와이어프레임 (텍스트 + 박스 위치 / 버튼 / 카드).
- **코드 변경 없음.**
- 산출물: `docs/specs/04_ai_action_leave.md` 신설 또는 본 plan 문서에 "설계 확정" 섹션 추가.

### 세션 13 — 백엔드

- `app/services/ai/action_leave.py` 신설 — parse / 매칭 / 토큰 / 실행 헬퍼.
- [app/routers/ai.py](../app/routers/ai.py) 에 `preview` / `execute` (필요 시 `health`) 엔드포인트 추가.
- AiUsageLog / AuditLog 연동.
- mock provider 기반 단위 테스트 ( `tests/test_ai_action_leave.py` 신설 ).
- 기존 휴무 API 의 검증 / 차단 로직을 그대로 통과시킬 것.

### 세션 14 — UI

- [app/templates/main.html](../app/templates/main.html) 에 AI 비서 박스 추가 + Alpine.js 핸들러.
- [app/static/css/app.css](../app/static/css/app.css) 에 박스 / 카드 / 강조 색상 추가.
- dev 서버에서 시연 — 정상 / 모호 날짜 / 다중 매칭 / 일자만 해석 케이스 4 개 확인.
- preview 도구 (스크린샷 등) 로 결과 첨부.

### 세션 15 — 테스트 / 보안

- pytest 통합 테스트 (preview → execute 정상 / 위조 / 거부).
- token 만료 처리.
- 운영 DB 격리 재확인 (`scripts/check_db_path.py` + 테스트 실행 시 임시 DB 경로 검증).
- `run_check.bat` 한 방에 통과.
- 보안 회귀 점검: LLM 응답 / 로그 / 에러 메시지에 환자 / 직원 PII 가 새지 않는지.

---

## 12. 변경하지 않는 것

이 4 개 세션 동안 **건드리지 않는다.**

- 기존 휴무 spec ( [docs/specs/02_치료사_휴무_규칙.md](specs/02_치료사_휴무_규칙.md) ) — 휴무 차단 규칙 자체는 변경 없음. AI 흐름은 그 위에 올라타기만 함.
- DB 스키마 (`EmployeeLeave` 컬럼 / 인덱스 / 마이그레이션 추가 없음).
- 기존 휴무 API 경로 ( `/api/employee-leaves`, `/api/employee-leaves/bulk-set` ).
- 기존 화면 흐름 (휴무 탭 / 예약 탭 등).
- 업종 / 용어 / 브랜딩.
- `pyproject.toml` 의 `app/**` lint 면제.
