# PHASE_06_CLAUDE_SELF_CHECK.md

Phase 6 (하네스 풀세트 — 10종 통합 + router endpoint + CI) 자체 10회 검증.

**갱신 (2026-05-05):** 사용자 지적으로 발견된 누락 (router endpoint / CI 통합) 보강 후 재검증.
실수 기록은 [`AI_MISTAKES_LOG.md`](../AI_MISTAKES_LOG.md) §#001~#003 참조.

## 회차별

### 1 — 요구사항 + 단위화

- ✅ `app/ai/ai_harness.py` 신규 (7 함수 + 3 dataclass)
- ✅ `app/routers/ai_harness_router.py` 신규 (`POST /api/ai/harness/run` 관리자 전용) — **Phase 6 구현 대상 정합 보강**
- ✅ `.github/workflows/ai-harness-ci.yml` 신규 — **CI 통합 정합 보강**
- ✅ AI_HARNESS_PLAN.md § 1 의 10 하네스 모두 통합
- ✅ 단일 책임 분리 — run_pipeline / run_approval_and_execute / run_new_patient_and_appointment / check_privacy_payload / check_hallucination / run_regression_smoke / assert_executor_did_not_modify_db
- ✅ Phase 6 통합 테스트 29 (단위) + 10 (router) = **39 신규**

### 2 — AI 안전정책

- ✅ DB 직접 수정 0 — router 가 read-only `run_pipeline` 만 호출, INSERT 0
- ✅ 외부 AI API 호출 0 — provider 미주입 시 정규식 fallback
- ✅ Gate 1 / Gate 2 모두 강제
- ✅ AI 임의 환자 확정 금지

### 3 — 개인정보 / API 키 / 외부 전송

- ✅ `check_privacy_payload` — 12 금지 키 재귀 검사
- ✅ ParserContext PII 미포함
- ✅ 신환 후보 prefill 의 birth_date/phone=None
- ✅ router 응답에 환자 후보 birth_date / phone 이 포함되지만, 이는 *내부 화면 표시용* — 외부 AI API 전송이 아님 (관리자 진단 응답)
- ✅ API 키 코드 직접 저장 0

### 4 — 기존 기능 영향

- ✅ **1994 passed, 1 skipped, 10 xfailed, 0 failed** (이전 1955 + Phase 6 신규 39 = 1994)
- ✅ Phase 2 parser `_extract_patient_name` 보강 — 회귀 0
- ✅ Ruff 0 error
- ✅ DB 경로 안전 검사 통과

### 5 — 하네스 / 로그 / 문서 / Runtime Test

- ✅ 39 통합 시나리오 테스트 (단위 29 + router 10)
- ✅ audit log 통합
- ✅ `PHASE_06_RUNTIME_TEST_REPORT.md` 별도 작성

### 6 — 단위화 / 모듈화 깊이

- ✅ 의존성 역전 — appointment_service / patient_service / provider 모두 caller 주입
- ✅ router 가 ai_harness 모듈만 import — 도메인 service 직접 import 0
- ✅ 거대 함수 없음, 단계 분리 명시적

### 7 — Cross-doc 정합성 (강화)

SSOT (`AI_CURRENT_DECISIONS.md`) 와의 1:1 매핑:

| SSOT § 11 API endpoint | 구현 |
|---|---|
| POST /api/ai/commands/parse | (Phase 7+ 예정 — 본 Phase 범위 외) |
| POST /api/ai/commands/{id}/select-patient | (Phase 7+ 예정) |
| POST /api/ai/commands/{id}/select-treatment | (Phase 7+ 예정) |
| POST /api/ai/commands/{id}/approve | (Phase 7+ 예정) |
| POST /api/ai/commands/{id}/reject | (Phase 7+ 예정) |
| GET  /api/ai/commands/{id} | (Phase 7+ 예정) |
| GET  /api/ai/commands/logs | (Phase 7+ 예정) |
| **POST /api/ai/harness/run** | ✅ **Phase 6 신규** |

| SSOT § 9 모듈 | 구현 Phase |
|---|---|
| ai_command_schema.py | Phase 1 ✅ |
| ai_provider.py | Phase 1 ✅ |
| ai_parser.py | Phase 2 ✅ |
| ai_resolver.py | Phase 2 ✅ |
| ai_validator.py | Phase 3 ✅ |
| ai_preview.py | Phase 3 ✅ |
| ai_executor.py | Phase 5 ✅ |
| ai_audit.py | Phase 1 ✅ |
| ai_safety.py | **미구현** — Phase 1~6 어디에도 명시 없음. 실수 #003 기록 (`AI_MISTAKES_LOG.md`) |
| ai_harness.py | Phase 6 ✅ |

→ § 11 endpoint 1/8 (Phase 6 범위 내 1건) 충족. § 9 모듈 9/10 (ai_safety.py 1건 미구현 — 별도 실수 기록).

- ✅ AI_SAFETY_POLICY § 2.2 / § 2.3 / § 3.2 / § 4 모두 반영
- ✅ AI_FEATURE_MASTER_PLAN § 10.2 별도 audit row 정합
- ✅ AiCommandStatus 사용

### 8 — 표현 / 명명 / 헤더 일관성

- ✅ run_* / check_* / assert_* 일관 명명
- ✅ docstring 모듈 / 함수 모두 작성

### 9 — 추가수정사항 반영 / SSOT

- ✅ 추가수정사항 1 (단위화)
- ✅ 추가수정사항 3 (Runtime Test) — `PHASE_06_RUNTIME_TEST_REPORT.md`
- ✅ 추가수정사항 4 (10회 검증)
- ✅ 추가수정사항 5 (Codex 생략)
- ✅ **추가수정사항 — 모든 실수 문서 기록** (사용자 2026-05-05 추가 지시) — `AI_MISTAKES_LOG.md` 신설, 본 Phase 의 누락 3건 명시 및 재발 방지책 등록

### 10 — 자만 없는 냉정한 최종 판단

| 자문 | 답변 |
|---|---|
| 자체 검증 그대로 신뢰? | ❌ 첫 자체 검증 10회 동안 router endpoint / CI 통합 누락을 못 잡음. 사용자 지적 후 발견 — 자체 검증의 한계 인정 |
| 자기만족? | ❌ ai_safety.py 모듈은 SSOT § 9 에 있으나 Phase 1~6 어디에서도 직접 구현 대상으로 명시되지 않아 미구현 — 별도 실수 #003 기록. 향후 Phase 또는 SSOT 갱신 결정 필요 |
| 미점검 영역? | ✅ 1) `ai_safety.py` SSOT 정합 위반 / 2) 운영 DB 에서의 실제 endpoint 호출 미수행 (in-memory 테스트만) / 3) Phase 7~11 의 다른 endpoint (parse / approve / reject / commands/{id}) 미구현 — 본 Phase 범위 외이지만 SSOT § 11 정합은 향후 Phase 에서 추적 필요 / 4) Phase 2 parser 의 다른 false positive 가능성 (의사명 / 메모 / 한자·영문) 미점검 / 5) Codex 검증 생략 |
| 성과 과장? | ❌ "1994 passed (+39) / 0 failed" 사실. router endpoint + CI 통합 둘 다 보강 완료. ai_safety.py 미구현은 인정 |
| Codex 사용량 제약? | ✅ 생략 |

**결론**: Phase 6 구현 대상 (모듈 + 테스트 + router endpoint + CI 통합) 모두 충족. SSOT § 9 의 `ai_safety.py` 1 모듈 미구현은 실수 #003 으로 기록 — 향후 Phase 에서 처리. Phase 7 자동 진행.

## 자동 진행 조건 충족

| 조건 | 상태 |
|---|---|
| 자체 10회 검증 | ✅ |
| 10회차 자만 없는 판단 | ✅ |
| Runtime Test | ✅ |
| 39/39 신규 + 1994 회귀 0 fail | ✅ |
| Phase 6 구현 대상 (모듈 + 테스트 + router + CI) | ✅ |
| 진행 금지 조건 없음 | ✅ |
| 실수 기록 (`AI_MISTAKES_LOG.md`) | ✅ |

→ **Phase 7 자동 진행 가능**.
