# 19-13 Codex 검증 요청서

## 1. 세션 이름

`19-13_ai_commands_boundary` — AI commands Preview / Approval / Execute 경계 helper
분리. 라우터 / AI 서비스 본체 *완전 무수정*. **AI 가 사용자 승인 없이 DB 변경 ⊥
+ Local-first / no_sources / low_confidence / PII 분기에서 provider 호출 ⊥
정책 가드** 명시.

## 2. 이번 세션 목표

`app/routers/ai.py` (929줄) 의 13 endpoint 응답 dict / outcome 분기 / HTTP 상태
코드 매핑 + `app/services/ai/action_leave.py` (917줄) 의 USER_MESSAGES / 토큰
정책 / mode / leave_type / leave_kind / confidence + `sms_draft.py` (469줄) 응답
key 셋 + `manual_qa.py` (78줄) 응답 key 셋을 `app/modules/ai/commands/` 후보
구조에 byte-equivalent 로 분리. **AI 자연어 명령 → Safety / Preview / Approval /
Execute 경계 명확화 + provider 호출 차단 reason_code 셋 + 승인 없는 DB 변경 차단
reason_code 셋 정책 단일 원천**. *라우터 본체 / AI 서비스 본체 / 응답 key /
DB schema 완전 무수정*.

## 3. 변경 파일 목록

| 파일 | 변경 종류 | 줄 수 |
|---|---|---:|
| `app/modules/ai/__init__.py` | 신규 | 70 |
| `app/modules/ai/commands/__init__.py` | 신규 | 46 |
| `app/modules/ai/commands/schemas.py` | 신규 | 304 |
| `app/modules/ai/commands/safety.py` | 신규 | 207 |
| `app/modules/ai/commands/preview.py` | 신규 | 165 |
| `app/modules/ai/commands/executor.py` | 신규 | 84 |
| `app/modules/ai/commands/service.py` | 신규 | 81 |
| `app/modules/ai/commands/adapters.py` | 신규 | 100 |
| `tests/test_19_13_ai_commands.py` | 신규 (156 cases) | 797 |
| `dosu_clinic.spec` | 수정 (+29) | — |
| `tests/test_pyinstaller_hidden_imports.py` | 수정 (+22) | — |

## 4. 실제 이동/정리한 AI commands 연결부

- 응답 키 contract → `commands/schemas.py:*_RESPONSE_KEYS` (frozenset, 14 셋).
- INTENT_NAMES (`create_therapist_leave` 현재 + 후속 5개 TODO) 셋.
- ACTION_LEAVE_OUTCOMES 33 outcome — services/ai/action_leave.py:USER_MESSAGES
  cross-check.
- HTTP 상태 코드 매핑 (`ACTION_EXECUTE_OUTCOME_HTTP_STATUS`) — 409/500/400 분기
  byte-equivalent.
- `_serialize_parse_result` / `_serialize_preview_result` byte-equivalent →
  `commands/preview.py:serialize_*`.
- `action_execute` body + 분기 byte-equivalent → `commands/executor.py:
  build_execute_response` + `http_status_for_execute`.
- 정책 상수 (TOKEN_TTL_SEC=120, TOKEN_VERSION=1, mode/leave_type/leave_kind/
  confidence/tone 셋) → `commands/service.py`.
- INPUT_MAX_LEN=200 / LEAVE_KEYWORDS / PATIENT_INDICATORS → `commands/safety.py`.
- 라우터 / AI 서비스 본체는 *완전 무수정*. 라우터 채택 ⊥.

## 5. Preview / Approval / Execute 경계 정리 방식

### Safety 단계 (LLM 호출 전 차단)

`commands/safety.py:is_provider_blocked_outcome(outcome)` → True 면 LLM/Embedding
호출 ⊥.

`REASON_CODES_PROVIDER_BLOCKED` 9 reason:
- `pii_detected` / `llm_skipped_pii`
- `no_sources` / `llm_skipped_no_sources`
- `low_confidence` / `llm_skipped_low_confidence`
- `unknown_feature`
- `external_api_not_allowed`
- `llm_skipped_local_only`

services/ai/action_leave.py:_pre_gate (PII / 환자 키워드 / 다중 명령) +
sms_draft.py:assert_safe_for_external + manual_qa hallucination guard 와
byte-equivalent.

### Preview 단계 (read-only)

`commands/preview.py:build_*_response` / `serialize_*` 가 응답 dict 빌더.

- Action: `parse` (read-only, 토큰 발급 없음, 6키 응답) → `preview` (read-only,
  HMAC 토큰 발급 TTL 120s, 11키 응답).
- SMS draft: read-only, `needs_user_confirm=True` (10키 응답, prompt_text /
  response_text 부재 가드).
- Manual QA: read-only (실행 단계 부재 — 단순 답변).

### Approval 단계 (HMAC 토큰 + confirm 검증)

`commands/safety.py:is_approval_required_outcome(outcome)` → True 면 DB write ⊥.

`REASON_CODES_APPROVAL_REQUIRED` 10 reason:
- `approval_required` / `execution_blocked` / `validation_failed`
- `not_confirmed` / `overwrite_not_acknowledged`
- `token_format` / `token_signature` / `token_unsafe` / `token_mismatch` / `token_expired`

services/ai/action_leave.py:_verify_token + execute() 의 ``confirm=True`` 가드와
byte-equivalent.

### Execute 단계 (확인된 Approval 후 단일 행 upsert)

`commands/executor.py:build_execute_response` 가 5키 응답.
`http_status_for_execute(ok, outcome)` 가 분기:
- ok=True → 200
- conflict_changed / therapist_changed → 409
- db_error → 500
- 그 외 → 400

services/ai/action_leave.py:execute() 의 _toctou_recheck + _do_upsert
(EmployeeLeave 1행) 와 byte-equivalent. SMS 흐름은 별도 /api/sms/send (관리자).

## 6. appointments / leaves / sms 연결 방식

`commands/adapters.py` 가 *문서화* 만 — 라우터 / 서비스 채택 ⊥.

- `AI_LEAVE_FLOW_MODULES` (leaves / therapists / appointments) — 19-x 채택 후보.
- `AI_SMS_DRAFT_FLOW_MODULES` (sms / appointments / patients / therapists / treatments).
- `AI_MANUAL_QA_FLOW_MODULES` (services/ai/{rag,knowledge,vector}).
- 현재는 services/ai/* 가 ORM 직접 호출 — 19-x 채택 시점에 modules/{leaves,
  therapists,appointments,sms,patients,treatments} 경계로 분리 검토.
- AI 예약 흐름 (자연어 → 예약 생성) 은 *현재 미구현* —
  `AI_RESERVATION_FLOW_MODULES_TODO` 마커로 후속 19-x 명시.

## 7. compatibility wrapper 유지 여부

- `app/routers/ai.py` 본체 *완전 무수정* — 13 endpoint 그대로 동작.
- `app/services/ai/{action_leave,sms_draft,manual_qa,provider,pii,prompts,
  validators,ai_logging,health,date_resolver,openai_client,anthropic_client}.py`
  본체 *완전 무수정*.
- `app/services/ai/{rag,knowledge,vector}/` 패키지 무수정.
- `app/services/rag/` 패키지 무수정 (manual QA 흐름 참조).
- 라우터 / 서비스 시그니처 / 응답 dict / 정책 상수 / 마스킹 패턴 어느 것도 변경 ⊥.
- contract 테스트 라우터 시그니처 검증 13 케이스 + 서비스 본체 검증 12 케이스 통과.

## 8. 수정 금지 범위 준수 여부

| 금지 항목 | 준수 |
|---|---|
| AI 가 사용자 승인 없이 예약/휴무/문자 실행 | ✅ REASON_CODES_APPROVAL_REQUIRED + token_*/not_confirmed 분류 |
| AI 가 DB 근거 없이 환자/예약/휴무 정보 생성 | ✅ services/ai/action_leave.py:_match_therapist 본체 무수정 |
| AI 가 실제 외부 문자 발송 직접 수행 | ✅ httpx/requests/urllib post 패턴 부재 + needs_user_confirm 가드 |
| 외부 LLM/Embedding API 실제 호출 추가 | ✅ 8 파일 × openai/anthropic/httpx import 부재 |
| 예약/휴무/문자 핵심 로직 변경 | ✅ 19-1~19-12 무수정 |
| 예약 API 응답 key 변경 | ✅ schemas.py contract |
| AI/RAG 기존 API 응답 key 변경 | ✅ commands/schemas.py 14 contract 셋 |
| DB schema / migration | ✅ 무수정 |
| UI 디자인 | ✅ main.html 무수정 |
| 하네스/테스트 약화 | ✅ conftest.py / pyproject.toml 무수정 |
| 운영 DB 접근 | ✅ 8 파일 × sqlite3/shutil/urllib import 부재 |
| 실제 외부 API 호출 | ✅ 8 파일 × LLM provider 호출 패턴 부재 |
| requirements.txt / PyInstaller spec 불필요 수정 | ✅ spec 은 8 신규 모듈 hidden import 만 |
| 기존 SMS AI / 휴무 AI 동작 변경 | ✅ 회귀 테스트 통과 |

## 9. 승인 없는 DB 변경 차단 여부

**차단.**

- `REASON_CODES_APPROVAL_REQUIRED` 10 reason 셋이 정책 단일 원천.
- `is_approval_required_outcome(outcome)` → True 면 DB write ⊥.
- token_* (5종) + not_confirmed + overwrite_not_acknowledged + approval_required +
  execution_blocked + validation_failed 셋 모두 가드 발동 검증 (8+8 파라미터 케이스).
- services/ai/action_leave.py:execute() 의 ``confirm=True`` + HMAC 토큰 + TTL 120s +
  TOCTOU 재조회 정책 본체 무수정 검증.
- HTTP 상태 코드 매핑 — 모든 token_* / confirm 분기 → 400 (DB write ⊥).
- conflict_changed / therapist_changed → 409 (동시성, DB write ⊥).
- db_error → 500.

## 10. 기존 AI/RAG API 응답 key 유지 여부

**유지.**

- `ACTION_PARSE_RESPONSE_KEYS` (6키) — `_serialize_parse_result` 본체 정합.
- `ACTION_PREVIEW_RESPONSE_KEYS` (11키) — `_serialize_preview_result` 본체 정합.
- `ACTION_EXECUTE_RESPONSE_KEYS` (5키) — `action_execute` body 정합.
- `SMS_DRAFT_RESPONSE_KEYS` (10키) — `sms_draft` 응답 정합 (prompt_text/
  response_text 제거 후).
- `MANUAL_ASK_RESPONSE_KEYS` (9키) / `MANUAL_SEARCH_MIN_KEYS` / `SMS_VALIDATE_RESPONSE_KEYS`.
- 라우터 시그니처 검증 6 핸들러 + 본체 검증 12 케이스 모두 통과.

## 11. 기존 예약 / 휴무 / 문자 영향 여부

**영향 부재.** 회귀 테스트 모두 통과:

- 19-1~19-12 모듈 (appointments / leaves / treatments / patients / notes /
  therapists / sms / stats / admin / backup / audit / export_import) — 무수정.
- AI action_leave / sms_draft / manual_qa / sms_validate 흐름 — 무수정.
- RAG / Safety / Full / Vector / Hybrid 하네스 — 무수정.
- `tests -k "ai_sms or ai_leave or rag or safety or contract or action_leave"` —
  270 통과.
- 전체 1659 / 1 skipped / 7 xfailed.

## 12. local-first 원칙 유지 여부

**유지.**

- `REASON_CODES_PROVIDER_BLOCKED` 9 reason 셋 — Local-first 가드 정책 단일 원천.
- `is_provider_blocked_outcome(outcome)` → True 면 `len(provider.calls) == 0`
  단언 정합.
- `_pre_gate` 본체 무수정 (PII / 환자 키워드 / 다중 명령 → LLM 호출 ⊥).
- sms_draft 의 cancelled / no_appointment / no_appt_time 분기 → LLM 호출 ⊥
  본체 검증.
- manual_qa 의 hallucination guard / not_found / blocked 분기 본체 무수정.

## 13. provider 호출 차단 기준 유지 여부

**유지.**

- `REASON_CODES_PROVIDER_BLOCKED` 9 reason — pii / no_sources / low_confidence /
  unknown_feature / external_api_not_allowed / llm_skipped_*.
- 본 19-13 helper 8 파일 × `provider.generate(` / `provider.chat(` /
  `.chat.completions.create(` / `anthropic.messages.create(` 패턴 부재 검증.

## 14. 개인정보 / API key / 문자나라 계정 원문 노출 여부

**노출 부재.**

- `PII_FORBIDDEN_FIELDS` 10 필드 (phone/rrn/birth/chart_no/patient_memo/real_name/...) —
  LLM prompt / log / 응답 부재 보장.
- `SECRET_KEYS_FORBIDDEN_IN_LOG` 8 키 (api_key/munjanara_*/admin_password_*/
  sync_secret/preview_token) — 로그 부재 가드.
- `SMS_DRAFT_FORBIDDEN_RESPONSE_KEYS` (prompt_text/response_text) — sms_draft
  응답 부재 + isdisjoint 검증 통과.
- `app/routers/ai.py:sms_draft` 의 `if k not in ("prompt_text", "response_text")`
  가드 본체 무수정 검증.
- `app/services/ai/sms_draft.py` 의 `assert_safe_for_external` + clinic_phone
  마스킹 제외 + 환자명 토큰화 정책 본체 무수정.

## 15. 운영 DB 보호 여부

**보호.**

- 본 19-13 helper 8 파일 × `sqlite3` / `shutil` / `engine` / `db.commit/add/
  delete/flush` 패턴 부재 검증.
- 라우터 / 서비스 본체 무수정 (engine.dispose / atomic rename / before_restore /
  before_update 정책은 19-12 admin/backup 모듈 + 본체 단일 원천).
- `scripts/check_db_path.py` exit 0.

## 16. 외부 API 호출 여부

**호출 부재.**

- 본 19-13 helper 8 파일 × urllib/requests/httpx/openai/anthropic import 부재
  검증.
- 라우터 본체 무수정 — `app/routers/ai.py` 의 `ai_provider.get_provider()` 흐름
  그대로.
- 본 19-13 가 외부 LLM/Embedding 호출 추가 ⊥.

## 17. 실제 문자 발송 여부

**발송 부재.**

- 본 19-13 helper 8 파일 × `httpx.post` / `requests.post` / `urllib.request.Request` /
  `fetch(` 패턴 부재.
- `services/ai/sms_draft.py` 의 `needs_user_confirm=True` 가드 + 외부 SMS 호출
  패턴 부재 본체 검증.
- 19-10 sms 모듈의 FakeSmsProvider 정책 그대로.

## 18. 순환참조 위험 여부

**위험 부재.**

- `app/modules/ai/commands/*` 6 파일 모두 D-4 단방향:
  - `app.routers` 미참조 검증 (6 파일).
  - `app.services.ai` 직접 import ⊥ 검증 (6 파일) — services/ai/* 본체 단일 원천.
- 본 helper 는 `app.models` / `app.config` 도 직접 참조 ⊥ — caller 가 primitives
  주입 (str / dict / SimpleNamespace 등).
- 정적 분석으로 충분.

## 19. 주석 / 문서화 기준 적용 여부

**적용.**

- 2 패키지 docstring (ai/__init__ + commands/__init__) — 본 세션 범위 / 범위 외 /
  COMPAT / SAFETY / RISK / NOTE / TODO.
- 6 파일 모듈 docstring + 함수 / 상수 단위 주석:
  - `# COMPAT:` — 응답 키 / 시그니처 / 정책 상수 byte-equivalent
  - `# SAFETY:` — PII / API key / 비밀 값 / 외부 API / DB 차단 가드
  - `# RISK:` — Preview / Approval / Execute 경계 / TOCTOU / TTL
  - `# NOTE:` — 정책 / 임계치 / 후속 검토 위치
  - `# TODO(19-x):` — AI 예약 흐름 / 비-목표 명시
- 의미 없는 줄 주석 부재.
- 주석 작성 때문에 기능 동작 변경 부재.

## 20. 실행한 테스트와 결과

| 검증 | 결과 |
|---|---|
| `pytest tests -q` | **1659 passed, 1 skipped, 7 xfailed, 27 warnings** |
| `pytest tests/test_19_13_ai_commands.py` | **156 passed** |
| `pytest tests/test_pyinstaller_hidden_imports.py` | **195 passed** |
| `pytest tests -k "ai_sms or ai_leave or rag or safety or contract or action_leave"` | **270 passed** |
| `ruff check app tests scripts` | **All checks passed!** |
| `scripts/check_db_path.py` | **exit 0** |

## 21. 실패 / 수정 루프 횟수

**1 회차 코드 수정** + ruff 자동 보정 1회. 5회 한도 내. **5회 실패 미해당**.

| 회차 | 가설 | 변경 | 결과 |
|---|---|---|---|
| 1 | 156 contract 케이스 1회차 실행 | 8 신규 파일 + spec / hidden imports + contract test | 1 fail (`test_services_sms_draft_no_direct_send` — sms_draft.py docstring 의 `/api/sms/send 호출 금지` 정책 문구가 검출 패턴 매칭) |
| 2 | docstring 정책 문구 매칭 → 실제 호출 패턴으로 검증 | httpx.post / requests.post / urllib.request.Request / fetch( 패턴 부재 검증으로 교체 | 156 / 156 통과 |
| (보정) | ruff 자동 보정 | import block 정렬 | All checks passed |

## 22. 19-14 전체 회귀 테스트 / PyInstaller 검증으로 넘어가도 되는지 판단 기준

**Claude Code 자체 판단: yes (조건부).**

근거:
- 1659 passed (19-12 baseline 1487 → +172) / 1 skipped / 7 xfailed.
- 신규 156 contract + 16 hidden imports (8 모듈 × 2) — 회귀 0건.
- ruff All checks passed.
- DB path 검사 exit 0.
- 응답 key contract 14 셋 + 라우터 시그니처 검증 13 케이스 + 서비스 본체 검증 12
  케이스 통과.
- 단방향 경계 (D-4) 6 파일 통과.
- AI 가 사용자 승인 없이 DB 변경 ⊥ + Local-first / provider 호출 차단 가드 통과.
- PII / API key / 문자나라 계정 / sync_secret / preview_token 비노출 통과.

**조건**: Codex 가 다음을 독립 검증 후 19-14 진입 권고.

1. `app/modules/ai/__init__.py` + `commands/__init__.py` + `commands/{schemas,
   safety,preview,executor,service,adapters}.py` 줄 수 정합 (요청 문서 ↔ 실제).
2. 라우터 / AI 서비스 본체 diff = 0 (`app/routers/ai.py`,
   `app/services/ai/{action_leave,sms_draft,manual_qa,provider,...}.py`,
   `app/services/ai/{rag,knowledge,vector}/`).
3. `dosu_clinic.spec` hidden imports 8 신규 모듈 등록.
4. `tests/test_pyinstaller_hidden_imports.py` EXPECTED 8 추가.
5. 8 파일 × `app.routers` + `app.services.ai` 직접 import ⊥.
6. 8 파일 × urllib/requests/httpx/openai/anthropic/shutil/sqlite3 import 부재.
7. 8 파일 × `provider.generate(` / `.chat.completions.create(` /
   `anthropic.messages.create(` 패턴 부재.
8. 8 파일 × `db.commit/add/delete/flush` 부재.
9. `REASON_CODES_PROVIDER_BLOCKED` ⊃ {pii_detected, no_sources, low_confidence,
   unknown_feature, external_api_not_allowed, llm_skipped_*}.
10. `REASON_CODES_APPROVAL_REQUIRED` ⊃ {approval_required, execution_blocked,
    validation_failed, not_confirmed, overwrite_not_acknowledged, token_*}.
11. 세 reason_code 셋 (provider_blocked / approval_required / lookup_failed)
    isdisjoint.
12. `SMS_DRAFT_FORBIDDEN_RESPONSE_KEYS` (prompt_text, response_text) 와
    `SMS_DRAFT_RESPONSE_KEYS` isdisjoint.
13. `TOKEN_TTL_SEC == 120` / `TOKEN_VERSION == 1` (services/ai/action_leave.py
    정합).
14. `tests/test_19_13_ai_commands.py` 156 케이스 재실행 통과.
15. 전체 `pytest tests -q` 재실행 — 1659 통과.
16. AI 예약 흐름 비-목표 마커 (`INTENT_NAMES_TODO` /
    `AI_RESERVATION_FLOW_MODULES_TODO`) 정합.

## 18 (참고). Codex 가 집중 검토할 파일

1. `app/modules/ai/commands/schemas.py` (응답 키 contract + INTENT + reason_code 셋)
2. `app/modules/ai/commands/safety.py` (outcome → reason 매핑 + Local-first 분류)
3. `app/modules/ai/commands/preview.py` / `executor.py` (응답 빌더 byte-equivalent)
4. `app/modules/ai/commands/service.py` (TOKEN_TTL=120 / VERSION=1 정합)
5. `tests/test_19_13_ai_commands.py` 의 §9~§13 (단방향 경계 + 외부/DB/LLM 의존
   부재 + 라우터/서비스 본체 무수정)
6. `app/routers/ai.py` / `app/services/ai/{action_leave,sms_draft,manual_qa}.py`
   git diff = 0 확인

## 19 (참고). Codex 가 반드시 확인할 체크리스트

- [ ] 19-13 본 모듈 8 파일 × `app.routers` 미참조
- [ ] 19-13 본 모듈 8 파일 × `app.services.ai` 직접 import ⊥
- [ ] 19-13 본 모듈 8 파일 × urllib/requests/httpx/openai/anthropic/shutil/sqlite3
  미참조
- [ ] 19-13 본 모듈 8 파일 × LLM provider 호출 패턴 부재
- [ ] 19-13 본 모듈 8 파일 × `db.commit/add/delete/flush` 미참조
- [ ] `REASON_CODES_PROVIDER_BLOCKED` ⊃ Local-first 9 reason
- [ ] `REASON_CODES_APPROVAL_REQUIRED` ⊃ Approval 10 reason
- [ ] 세 reason_code 셋 isdisjoint
- [ ] `SMS_DRAFT_FORBIDDEN_RESPONSE_KEYS` ∩ `SMS_DRAFT_RESPONSE_KEYS` = ∅
- [ ] `TOKEN_TTL_SEC == 120` / `TOKEN_VERSION == 1`
- [ ] `INTENT_NAMES_IMPLEMENTED` ∩ `INTENT_NAMES_TODO` = ∅
- [ ] `dosu_clinic.spec` hidden imports 에 8 신규 모듈
- [ ] `tests/test_pyinstaller_hidden_imports.py` EXPECTED_19_X_MODULES 에 8 추가
- [ ] `tests -q` 재실행 — 1659 통과
- [ ] `ruff check app tests scripts` — clean
- [ ] `scripts/check_db_path.py` — exit 0

## 20. 다음 세션으로 넘어가도 되는지에 대한 Claude Code 의 자체 판단

**yes** — 위 §22 기준 충족. Codex 가 §18 집중 검토 + §19 체크리스트 확인 후
19-14 (전체 회귀 테스트 / PyInstaller 검증) 진입 가능.

남은 위험 요소:
- AI 예약 흐름 (자연어 → 예약 생성 / 수정 / 취소) 은 *현재 미구현* —
  INTENT_NAMES_TODO + AI_RESERVATION_FLOW_MODULES_TODO 마커로 19-x 후속 명시.
- AI SMS 일괄 발송 흐름은 *현재 미구현* — AI_SMS_BATCH_FLOW_MODULES_TODO 마커.
- AI 환자 등록 흐름은 *현재 미구현* — INTENT_NAMES_TODO 마커.
- 본 19-13 helper 의 라우터 / 서비스 채택은 19-x 점진적 — 본체 byte-equivalent
  검증으로 회귀 위험 0.
