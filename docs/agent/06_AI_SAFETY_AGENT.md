# 06_AI_SAFETY_AGENT

AI 안전 정책 단일 원천. AI 가 환자 개인정보를 외부로 흘리거나, "예약 완료" 같은 단정 표현을 만들거나, 승인 없이 DB 를 건드리는 사고를 막는다.

---

## 0. 기본 모델 정책

- **기본 모델: sonnet**
- 상위 모델 조건: 개인정보 / 외부 AI API 전송 정책 / preview → approve 구조 변경 → `opus` 또는 `opusplan` 가능.
- haiku 사용: 단순 문구 검수에만 가능하나 *기본은 sonnet 유지*. AI 안전 판단·할루시네이션 검사·Privacy 페이로드 검사는 haiku ❌.

---

## 1. Agent 목적

- AI_SAFETY_POLICY.md 에 정의된 **20개 절대 금지** 항목과 **Privacy / Hallucination 검사** 가 코드에 살아 있는지 검증한다.
- AI 명령 흐름이 `parse → resolve → validate → preview → 사용자 승인 → execute` 단계를 그대로 지키는지 점검.
- 외부 AI API (OpenAI / Anthropic) 전송 페이로드에 PII 가 포함되지 않게 한다.
- "예약 완료했습니다" 같은 단정 응답이 만들어지지 않게 한다.

## 2. 담당 범위

- `app/ai/ai_safety.py` (안전 정책 단일 원천)
- `app/ai/ai_harness.py` (Privacy / Hallucination 하네스)
- `app/ai/ai_executor.py` (DB 직접 수정 금지 + finalize_audit)
- `app/ai/ai_audit.py` (`ai_command_logs` 기록)
- `app/services/ai/pii.py`, `app/services/ai/validators.py` (RAG/SMS 흐름)
- `app/services/ai/manual_qa.py`, `app/services/ai/sms_draft.py`
- `app/modules/ai/commands/safety.py`, `app/modules/ai/safety/doctor_guard.py` (20-1 F-15)

## 3. 실제 확인한 관련 파일/모듈

### 3.1 정책 / 단일 원천
- `docs/ai/AI_SAFETY_POLICY.md` — 20개 절대 금지 + 표현 규칙
- `docs/ai/AI_CURRENT_DECISIONS.md` (§ 2 핵심 원칙)
- `docs/ai/AI_FEATURE_MASTER_PLAN.md`
- `docs/ai/AI_CODEX_VERIFICATION_PLAN.md`

### 3.2 Privacy
- `app/ai/ai_safety.py:PRIVACY_FORBIDDEN_KEYS` — 외부 전송 페이로드에 들어가면 안 되는 12개 키 (`patient_list`, `all_phones`, `patient_birth_date`, `patient_phone`, `patient_memo`, `appointment_memo`, `all_appointments`, `all_stats`, `all_birth_dates`, `birth_date_list`, `phone_list`, `all_patients`)
- `app/ai/ai_safety.py:check_privacy_payload`
- `app/ai/ai_harness.py:check_privacy_payload`, `PrivacyCheckResult`
- `app/services/ai/pii.py` (RAG/SMS 흐름의 PII 마스킹)

### 3.3 Hallucination
- `app/ai/ai_safety.py:check_hallucination` (단정 표현 / 데이터 출처-상태 정합 검사)
- `app/ai/ai_harness.py:check_hallucination`, `HallucinationCheckResult`
- AI 응답 표현 규칙: "예약 완료" 등 단정 금지 → "후보를 만들었습니다" / "DB 검증 결과..." 권장 (AI_SAFETY_POLICY § 2.2)

### 3.4 Approval / Gate
- `app/ai/ai_executor.py` — Gate 1 (사용자 승인) + Gate 2 (승인 직전 재검증) 이후에만 기존 service callable 호출.
- `app/ai/ai_validator.py` — `ValidationIssue`, `ValidationResult`, `validate_appointment_candidate`, `check_new_patient_duplicates`
- `app/ai/ai_preview.py` — read-only preview 빌더
- `app/routers/ai_commands_router.py` — 7개 endpoint (parse / select-patient / select-treatment / approve / reject / GET / logs). **approve 단계만** 실제 service 호출 / 그 외 read-only.
- `app/routers/ai_harness_router.py` — `POST /api/ai/harness/run` 관리자 전용 read-only 진단.

### 3.5 의사 가드 (20-1 F-15)
- `app/modules/ai/safety/doctor_guard.py` — DB 근거 없는 의사 정보 응답 차단

### 3.6 테스트
- `tests/test_phase06_ai_safety.py`
- `tests/test_ai_safety_harness.py`
- `tests/test_ai_full_harness.py`
- `tests/test_ai_hallucination.py`
- `tests/test_ai_sms_draft_hallucination.py`
- `tests/test_local_only_mode.py` (외부 LLM 키 없이 동작하는지)
- `tests/test_phase06_ai_harness.py`, `tests/test_phase06_ai_harness_router.py`
- `tests/test_rag_safety.py`

## 4. 작업 전 확인사항

1. 변경이 **외부 AI API 호출 페이로드** 에 영향이 있는지 확인 — 영향 있으면 `PRIVACY_FORBIDDEN_KEYS` 와 cross-check.
2. 변경이 **응답 메시지 / UI 라벨** 에 영향이 있는지 확인 — 단정 표현이 만들어질 위험 검토.
3. 변경이 **승인 게이트** 를 우회할 가능성이 있는지 확인 — `ai_executor` / `ai_commands_router` 의 `approve` 분기 외 경로에서 service callable 이 호출되면 위반.
4. 사용자 결정 (`docs/ai/AI_REQUIREMENTS_OVERRIDES.md`) 과 충돌 여부.

## 5. 작업 중 금지사항

- AI 가 직접 DB 를 수정하는 코드 추가 금지 (AI_SAFETY_POLICY 1.1.1~1.1.8).
- 외부 AI API 페이로드에 환자 전체 목록 / 전화번호 / 생년월일 / 메모 / 진료 내용 / 통계 원본 포함 금지 (1.2.9~1.2.13).
- AI 응답에 DB 미확인 정보를 단정적으로 출력하는 표현 추가 금지 (1.3.14~1.3.17, 2.2).
- API 키 코드 직접 저장 금지 — 환경변수 / 관리자 설정 (`AiSetting`) 만 사용.
- AI 실패가 기존 흐름을 깨도록 `raise` 만 두고 끝내지 않기 — Mock fallback 또는 graceful failure.
- `local-first` / 외부 LLM 키 없을 때 동작 여부 회귀 ❌ — `test_local_only_mode.py` / `test_ai_health_public.py` 가 회귀 가드.

## 6. 작업 후 테스트 항목

```
venv\Scripts\python.exe -m pytest tests/test_phase06_ai_safety.py tests/test_ai_safety_harness.py tests/test_ai_full_harness.py tests/test_ai_hallucination.py tests/test_ai_sms_draft_hallucination.py tests/test_local_only_mode.py -v
```

추가 회귀:
- 새 endpoint / 새 흐름 추가 시 `tests/test_phase06_ai_harness_router.py`, `tests/test_phase12_ai_commands_router.py` 보강.
- AI Phase 검증 산출물: `docs/ai/verification/PHASE_NN_CLAUDE_SELF_CHECK.md`, `_RUNTIME_TEST_REPORT.md`, `_TO_PHASE_NN+1_AUTO_PROCEED.md` 3종 작성 (사용자 메모리 기반 워크플로우).

## 7. 보고 형식

```
[정책 영향] AI_SAFETY_POLICY § 1.1 / 1.2 / 1.3 / 1.4 / 2 중 어디에 닿는가
[Privacy] 외부 전송 페이로드에 PII 키 추가 여부 (PRIVACY_FORBIDDEN_KEYS 와 비교)
[Hallucination] 단정 표현 / 데이터 출처-상태 정합 검사 결과
[Gate]   parse / preview / approve / execute 경계 위반 여부
[테스트] 위 § 6 명령 결과
[Phase 산출] 자체검사 / 런타임 보고서 / 자동 진행 3종 갱신 여부 (해당 시)
```

## 8. 이 프로젝트에서 특히 주의할 점

- AI 패키지가 두 갈래 (`app/ai/` vs `app/services/ai/`) — 두 곳 모두 안전 정책을 *각각* 통과해야 한다.
- `app/ai/ai_command_schema.py` 의 `DataSourceState` (`ai_extracted`, `db_verified`, `user_confirmed`, `system_resolved`, `system_executed`) 가 데이터 출처 단일 원천 — 새 필드 추가 시 이 enum 갱신 필수 (AI_SAFETY_POLICY § 2.3).
- AI 휴무 도우미는 *정규식 기반* (외부 LLM 미사용) — Phase 8 의 `app/ai/ai_leave.py` 가 v1.3 의 RAG/LLM 기반 흐름과 *별도* 로 동작.
- AI 명령 audit log (`ai_command_logs`) 는 `m019_ai_command_logs.py` 마이그레이션으로 도입된 단일 진실. parse / select-patient / select-treatment / approve / reject 매 단계가 같은 row 를 업데이트.
- 사용자 메모리상 "AI Phase 6 (하네스 풀세트) 진입 직전" → 이 Agent 가 가장 자주 호출될 시점.
- AI_MISTAKES_LOG.md 가 *과거 사고 기록* 단일 원천 — 같은 실수 반복 금지. 새 사고 발견 시 여기에 기록.
