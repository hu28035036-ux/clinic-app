# 19-13 AI commands 분리 — 변경 요약

## 세션 이름

`19-13_ai_commands_boundary` — AI commands Preview / Approval / Execute 경계 후보
helper 분리. 라우터 (`app/routers/ai.py`) / AI 서비스 (`app/services/ai/*`) 본체
*완전 무수정*. **AI 가 사용자 승인 없이 DB 변경 ⊥ + Local-first / no_sources /
low_confidence / PII 분기에서 provider 호출 ⊥ 정책 가드** 명시.

## 작업 목표 (한 문장)

`app/routers/ai.py` (929줄) 의 13 endpoint 응답 dict / outcome 분기 / HTTP 상태
코드 매핑 + `app/services/ai/action_leave.py` (917줄) 의 USER_MESSAGES / 토큰
정책 / mode / leave_type / leave_kind / confidence + `sms_draft.py` (469줄) 의
응답 key 셋 + `manual_qa.py` (78줄) 응답 key 셋을 `app/modules/ai/commands/`
후보 구조에 byte-equivalent 로 분리. **AI 자연어 명령 → Safety / Preview /
Approval / Execute 경계 명확화 + provider 호출 차단 reason_code 셋 + 승인 없는
DB 변경 차단 reason_code 셋 정책 단일 원천**. *라우터 본체 / AI 서비스 본체 /
응답 key 완전 무수정*.

## 변경 파일 목록

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

(라우터 본체 / AI 서비스 본체 / 모델 / 마이그레이션 무수정.)

## 파일별 변경 요약

### `app/modules/ai/__init__.py` (신규, 70줄)

AI 패키지 docstring — 본 세션 범위 / 범위 외 / COMPAT / SAFETY / RISK / NOTE /
TODO.
- COMPAT: 13 AI endpoint + 9 AI 서비스 파일 + RAG / knowledge / vector 패키지 무수정.
- SAFETY: 환자 / 직원 PII / 차트 / 전화 / 생년월일 / 메모 원문 부재 보장.
- SAFETY: AI api_key / 문자나라 계정 / sync_secret 원문 부재.
- RISK: AI 가 사용자 승인 없이 DB 변경 ⊥ — Preview/Execute 경계 정책 단일 원천.
- RISK: AI 가 외부 SMS 직접 발송 ⊥ — sms_draft 는 needs_user_confirm=True 만.
- RISK: local-first 정책 (`local_only`/`no_sources`/`low_confidence`/PII) → provider 호출 0.
- TODO(19-x): AI 예약 흐름 (자연어 → 예약 생성) — 현재 미구현.

### `app/modules/ai/commands/__init__.py` (신규, 46줄)

commands 패키지 docstring.
- 6 파일 책임 분류 (schemas / safety / preview / executor / service / adapters).
- COMPAT: services/ai/{action_leave,sms_draft,manual_qa}.py 와 byte-equivalent.

### `app/modules/ai/commands/schemas.py` (신규, 304줄)

응답 키 contract + INTENT_NAMES + reason_code 셋.
- `ACTION_PARSE_RESPONSE_KEYS` (6키) / `ACTION_PREVIEW_RESPONSE_KEYS` (11키) /
  `ACTION_EXECUTE_RESPONSE_KEYS` (5키).
- `SMS_DRAFT_RESPONSE_KEYS` (10키) / `SMS_DRAFT_FORBIDDEN_RESPONSE_KEYS`
  (`prompt_text` / `response_text` 부재 가드).
- `MANUAL_SEARCH_MIN_KEYS` / `MANUAL_ASK_RESPONSE_KEYS` (9키) / `SMS_VALIDATE_RESPONSE_KEYS`.
- `ACTION_LEAVE_OUTCOMES` (33 outcome — services/ai/action_leave.py:USER_MESSAGES 정합).
- `INTENT_NAMES_IMPLEMENTED` (`create_therapist_leave`) / `INTENT_NAMES_TODO`
  (예약 / 환자 등록 / 일괄 SMS — 후속 19-x).
- **`REASON_CODES_PROVIDER_BLOCKED`** (9 reason — Local-first 가드).
- **`REASON_CODES_APPROVAL_REQUIRED`** (10 reason — DB write 차단 가드).
- `REASON_CODES_LOOKUP_FAILED` (6 reason — 매칭 실패).
- `ACTION_EXECUTE_OUTCOME_HTTP_STATUS` (409/500/400 분기 매핑).

### `app/modules/ai/commands/safety.py` (신규, 207줄)

Safety 게이트 helper.
- `ACTION_LEAVE_OUTCOME_TO_REASON` (33 매핑) — outcome → reason_code 단일 원천.
- `map_action_leave_outcome_to_reason(outcome)`.
- `is_provider_blocked_outcome(outcome)` — Local-first 가드 분류.
- `is_approval_required_outcome(outcome)` — Approval 가드 분류.
- `is_lookup_failed_outcome(outcome)` — 매칭 실패 분류.
- 정책 상수 (`INPUT_MAX_LEN=200` / `LEAVE_KEYWORDS` / `PATIENT_INDICATORS`) —
  services/ai/action_leave.py 와 byte-equivalent.
- `PII_FORBIDDEN_FIELDS` (10 필드 — phone/rrn/birth/chart_no/...).
- `SECRET_KEYS_FORBIDDEN_IN_LOG` (8 키 — api_key/munjanara_*/admin_password_*/
  sync_secret/preview_token).

### `app/modules/ai/commands/preview.py` (신규, 165줄)

Preview 응답 빌더.
- `build_parse_response` / `serialize_parse_result` —
  `app/routers/ai.py:_serialize_parse_result` byte-equivalent.
- `build_preview_response` / `serialize_preview_result` —
  `app/routers/ai.py:_serialize_preview_result` byte-equivalent.
- `build_sms_draft_response_public` — sms_draft 응답 (prompt_text / response_text
  제거 후) byte-equivalent.

### `app/modules/ai/commands/executor.py` (신규, 84줄)

Execute 응답 빌더 + HTTP 상태 코드 매핑.
- `build_execute_response` / `serialize_execute_result`.
- `http_status_for_execute(ok, outcome)` — `ai.py:action_execute` 분기 byte-equivalent
  (200 / 409 / 500 / 400).

### `app/modules/ai/commands/service.py` (신규, 81줄)

정책 상수 단일 원천.
- `TOKEN_TTL_SEC = 120` / `TOKEN_VERSION = 1` (services/ai/action_leave.py 정합).
- `ACTION_LEAVE_MODES` (create / overwrite / noop).
- `LEAVE_TYPES` (full / morning / afternoon / unknown).
- `LEAVE_KINDS` (annual / monthly / unknown).
- `CONFIDENCE_LEVELS` (high / low).
- `SMS_DRAFT_TONES` (friendly / formal).
- `ACTION_LEAVE_INTENT_NAME = "create_therapist_leave"`.

### `app/modules/ai/commands/adapters.py` (신규, 100줄)

19-x 후속 검토용 모듈 경계 *문서화* (라우터 채택 ⊥).
- `AI_LEAVE_FLOW_MODULES` (leaves / therapists / appointments).
- `AI_SMS_DRAFT_FLOW_MODULES` (sms / appointments / patients / therapists / treatments).
- `AI_MANUAL_QA_FLOW_MODULES` (services/ai/{rag,knowledge,vector}).
- **`AI_DIRECT_CALL_FORBIDDEN`** (7 패턴 — external_sms_send / db_commit_in_preview /
  llm_call_in_local_only / ...).
- `AI_RESERVATION_FLOW_MODULES_TODO` / `AI_SMS_BATCH_FLOW_MODULES_TODO` (19-x 후속).

### `tests/test_19_13_ai_commands.py` (신규, 797줄, 156 cases)

contract 검증.

1. schemas — 응답 key 셋 정합 (parse/preview/execute, sms/draft 평문 부재 가드,
   intent / outcome 셋, USER_MESSAGES cross-check).
2. reason_code 셋 — provider_blocked / approval_required / lookup_failed
   isdisjoint + 필수 원소 포함.
3. safety — outcome → reason_code 매핑 17 케이스 + provider_blocked 8 케이스 +
   approval_required 8 케이스 + lookup_failed 8 케이스.
4. safety 정책 상수 — INPUT_MAX_LEN / LEAVE_KEYWORDS / PATIENT_INDICATORS
   byte-equivalent + has_leave_keyword 5 케이스 + has_patient_indicator 5 케이스 +
   is_input_length_valid 5 케이스 + PII_FORBIDDEN_FIELDS / SECRET_KEYS_FORBIDDEN_IN_LOG.
5. preview — build_*  / serialize_* byte-equivalent (parse / preview / sms_draft).
6. executor — http_status_for_execute 13 케이스 + build_execute_response /
   serialize_execute_result.
7. service — TOKEN_TTL=120 / VERSION=1 byte-equivalent + mode / leave_type /
   leave_kind / confidence / tone 셋.
8. adapters — 19-x 후속 검토 모듈 셋 + DIRECT_CALL_FORBIDDEN 정책 가드.
9. **단방향 경계 (D-4)** — 6 파일 × `app.routers` 미참조 + 6 파일 × `app.services.ai`
   직접 import ⊥ (helper 만, 본체는 services/ai/* 단일 원천).
10. **외부 / DB / LLM 의존 가드** — 8 파일 × urllib/requests/httpx/shutil/sqlite3/
    openai/anthropic 부재 + db.commit/add/delete/flush 부재 + provider.generate(/
    .chat.completions.create(/anthropic.messages.create( 부재.
11. **라우터 / 서비스 본체 무수정** — `_serialize_parse_result` /
    `_serialize_preview_result` 본체 + 6 핸들러 시그니처 (action/parse,preview,execute /
    sms/draft,validate / manual/search,ask) + sms_draft 의 prompt_text/response_text
    제거 본체 + INTENT_NAME / TOKEN_TTL=120 / VERSION=1 / _SERVER_SECRET 본체.
12. **환각 / PII 가드 본체 검증** — `_pre_gate` 의 phone/rrn 검출 + sms_draft 의
    `assert_safe_for_external` + clinic_phone 마스킹 제외 + skip_reason 분기에서
    LLM 호출 ⊥.
13. action_execute body 응답 key 5개 본체 + 분기 (409/500/400) 본체 검증.
14. provider 호출 차단 cross-check (PII / low_confidence / unknown_feature).
15. 승인 가드 cross-check (token_* / not_confirmed / overwrite_not_acknowledged).

### `dosu_clinic.spec` (수정, +29줄)

`hidden` 리스트에 19-13 신규 8개 모듈 등록 + 5줄 주석.
- `app.modules.ai` + commands + 6 sub-files.

### `tests/test_pyinstaller_hidden_imports.py` (수정, +22줄)

`EXPECTED_19_X_MODULES_MODULES` 에 8개 모듈 추가.

## 의도 / 이유

- **byte-equivalent 분리** — 인라인 응답 dict / outcome 분기 / HTTP 상태 코드 /
  토큰 정책이 `app/routers/ai.py` (~929줄) + `app/services/ai/{action_leave,
  sms_draft}.py` (~1386줄) 안에 분산. 19-x 라우터 / 서비스 채택 시점에 본 helper 채택.
- **AI 가 사용자 승인 없이 DB 변경 ⊥** — `REASON_CODES_APPROVAL_REQUIRED` 셋
  (token_* / not_confirmed / overwrite_not_acknowledged) + Preview / Execute
  경계 분리 정책 단일 원천. action_leave 본체와 byte-equivalent.
- **Local-first / provider 호출 차단** — `REASON_CODES_PROVIDER_BLOCKED` 셋
  (pii_detected / no_sources / low_confidence / unknown_feature /
  llm_skipped_*) + outcome → reason 매핑 단일 원천. `len(provider.calls) == 0`
  단언 정합.
- **PII / API key / 문자나라 계정 원문 부재 보장** — `PII_FORBIDDEN_FIELDS` +
  `SECRET_KEYS_FORBIDDEN_IN_LOG` + `SMS_DRAFT_FORBIDDEN_RESPONSE_KEYS` 셋이
  정책 가드. 19-12 admin 모듈 + 19-13 commands 모듈이 정합.
- **계약 회귀 보호** — `schemas.py` 의 frozenset 응답 키 셋이 임의 변경 검출.
  AI 도우미 탭 / SMS 초안 모달 / 휴무 모달 의존.
- **단방향 경계 (D-4) 보존** — `commands.*` 모두 `app.routers` + `app.services.ai`
  미참조. 본체는 services/ai/* 단일 원천.
- **AI 예약 흐름 비-목표 표기** — INTENT_NAMES_TODO + AI_RESERVATION_FLOW_MODULES_TODO
  마커로 19-x 후속 검토 명시.

## compatibility wrapper / 라우터 무수정

- `app/routers/ai.py` 본체 *완전 무수정* — 13 endpoint 그대로 동작.
- `app/services/ai/action_leave.py` 본체 *완전 무수정* — parse / preview / execute /
  HMAC 토큰 / TOCTOU 그대로.
- `app/services/ai/sms_draft.py` 본체 *완전 무수정* — make_draft / PII 가드 /
  환각 가드 그대로.
- `app/services/ai/manual_qa.py` 본체 *완전 무수정* — manual_search /
  ask_manual_question / validate_answer 그대로.
- `app/services/ai/{provider,pii,prompts,validators,ai_logging,health,date_resolver,
  openai_client,anthropic_client}.py` 본체 무수정.
- `app/services/ai/{rag,knowledge,vector}/` 패키지 무수정.
- `app/routers/__init__.py` 무수정.
- 본 helper 패키지는 *전적으로 추가* — 기존 import 경로 / 함수 시그니처 / 응답
  dict / 응답 key / 정책 상수 *어느 것도 변경 ⊥*.
- 라우터 시그니처 검증 13 케이스 + 서비스 본체 검증 12 케이스 통과.

## 수정 금지 범위 준수

| 금지 항목 | 준수 |
|---|---|
| AI 가 사용자 승인 없이 예약/휴무/문자 실행 | ✅ REASON_CODES_APPROVAL_REQUIRED 셋 + Preview/Execute 경계 |
| AI 가 DB 근거 없이 환자/예약/휴무 정보 생성 | ✅ services/ai/action_leave.py:_match_therapist + _check_conflict 본체 무수정 |
| AI 가 실제 외부 문자 발송 직접 수행 | ✅ sms_draft 본체 무수정 + needs_user_confirm 가드 + httpx/requests/urllib 부재 |
| 외부 LLM/Embedding API 실제 호출 추가 | ✅ 8 파일 × import 부재 + provider.generate 패턴 부재 |
| 예약/휴무/문자 핵심 로직 대규모 변경 | ✅ 19-1~19-12 무수정 |
| 예약 API 응답 key 변경 | ✅ schemas.py contract |
| AI/RAG 기존 API 응답 key 변경 | ✅ AI commands schemas.py contract 14 셋 |
| DB schema 변경 | ✅ 무수정 |
| migration 생성 | ✅ 무수정 |
| UI 디자인 변경 | ✅ main.html 무수정 |
| 하네스/테스트 약화 | ✅ conftest.py / pyproject.toml 무수정 |
| 운영 DB 접근 | ✅ urllib/sqlite3/shutil import 부재 |
| 실제 외부 API 호출 | ✅ openai/anthropic/httpx import 부재 |
| requirements.txt / PyInstaller spec 불필요 수정 | ✅ spec 은 8 신규 모듈 hidden import 등록만 |
| 기존 SMS AI / 휴무 AI 동작 변경 | ✅ 회귀 테스트 통과 (action_leave + sms_draft + manual_qa) |

## 자동 수정 루프 횟수

**1 회차 코드 수정** — 1회차에서 1 fail (`test_services_sms_draft_no_direct_send` —
docstring 의 정책 문구가 매칭), 1회차 정정에서 통과. 2회차에서 ruff 자동 보정.
**5회 한도 내**.

## 5회 실패 여부

**미해당** — 1회차 통과.

## 위반 / 우회 없음

- `pyproject.toml` per-file-ignores 무수정.
- 운영 DB 직접 open 없음.
- 외부 API 호출 없음.
- LLM provider 호출 없음.
- `app.routers.ai` / `app.services.ai.*` 본체 무수정.
- DB schema / migration 무수정.
- API key / 문자나라 계정 / sync_secret / 환자 PII 원문 노출 없음.
- AI 가 사용자 승인 없이 DB 변경 ⊥.
- AI 가 실제 외부 SMS 발송 ⊥.
