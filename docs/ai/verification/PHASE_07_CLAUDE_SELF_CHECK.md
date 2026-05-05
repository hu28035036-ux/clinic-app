# PHASE_07_CLAUDE_SELF_CHECK.md

Phase 7 (update_appointment / cancel_appointment intent) 자체 10회 검증.

## Phase 7 시작 전 체크리스트 (실수 #001 재발 방지)

- [x] AI_IMPLEMENTATION_PHASES § Phase 7 구현 대상: intent 2개 / 변경 전·후 비교 / 물리 삭제 금지 / 승인 후 실행
- [x] AI_FEATURE_MASTER_PLAN § 5.2 13 필드 (update_appointment / cancel_appointment) 모두 점검
- [x] SSOT § 11 의 commands router endpoint 들은 어느 Phase 명시 구현 대상도 아님 — 실수 #004 로 사전 기록 / 임의 추가 금지
- [x] 환경 / 인프라 신설 필요 여부 점검 — 없음

## 회차별

### 1 — 요구사항 + 단위화

- ✅ `app/ai/ai_appointment_change.py` 신규 — 7 함수 + 4 dataclass + 2 Protocol
- ✅ 단일 책임 분리:
  - `resolve_target_appointment` — 환자+날짜+시간 → Appointment 단일 식별 (canceled 자동 제외)
  - `build_appointment_diff` — 변경 전·후 비교 (changed_fields)
  - `validate_update_appointment` — 변경 후 검증 (자기 자신 exclude_appointment_id)
  - `validate_cancel_appointment` — 취소 검증 (이미 취소 차단)
  - `execute_approved_update_appointment` — Gate 2 + service callable
  - `execute_approved_cancel_appointment` — Gate 2 + service callable (물리 삭제 0)
  - `build_update_preview` / `build_cancel_preview` — 승인 카드
- ✅ Phase 5 의 `validate_appointment_candidate` 를 `exclude_appointment_id` 옵션으로 확장 (회귀 0 — 기본 None)
- ✅ Phase 7 단위 테스트 26 신규

### 2 — AI 안전정책

- ✅ DB 직접 수정 0 — INSERT / UPDATE / DELETE 모두 service callable
- ✅ 외부 AI API 호출 0 (provider 미사용)
- ✅ Gate 1 (preview/approval_disabled) + Gate 2 (executor 의 validator 재호출) 모두 강제
- ✅ 물리 삭제 금지 — `execute_approved_cancel_appointment` 자체는 service callable 만 호출. 테스트 `test_execute_cancel_does_not_physically_delete` 가 row count 동일 확인.

### 3 — 개인정보 / API 키 / 외부 전송

- ✅ 외부 AI API 미사용
- ✅ diff 응답에 patient_id / treatment_codes 포함 — 내부 화면 표시용 (외부 전송 ⊥)
- ✅ ai_safety.check_privacy_payload 통합 가능 (페이로드 기준)

### 4 — 기존 기능 영향

- ✅ **2034 passed** (Phase 6 까지 1994 + ai_safety 14 + Phase 7 26 = 2034), 0 failed
- ✅ Ruff 0 error
- ✅ DB 경로 안전 검사 통과
- ✅ Phase 5 validator 확장은 후방 호환 (exclude_appointment_id default=None) — 기존 130+ 테스트 모두 통과

### 5 — 하네스 / 로그 / 문서 / Runtime Test

- ✅ 26 단위 테스트
- ✅ Runtime Test Report 별도 작성 (`PHASE_07_RUNTIME_TEST_REPORT.md`)
- ⚠ audit 통합은 미수행 — Phase 5 의 `finalize_audit` 패턴을 재사용 가능하나 update / cancel 의 audit 호출은 caller (router / 향후 Phase) 책임으로 유지

### 6 — 단위화 / 모듈화 깊이

- ✅ Protocol 기반 의존성 역전 (AppointmentUpdateServiceCallable / AppointmentCancelServiceCallable)
- ✅ 거대 함수 없음
- ✅ Phase 5 의 ai_executor 와 동일한 의존성 역전 패턴
- ✅ 본 모듈 = ai_validator (재호출) + ai_resolver 의 새 도메인 (target appointment) 의 통합

### 7 — Cross-doc 정합성 (강화)

| AI_FEATURE_MASTER_PLAN § 5.2 13 필드 | 구현 / 정합 |
|---|---|
| intent 이름 | `AiIntent.UPDATE_APPOINTMENT` / `CANCEL_APPOINTMENT` (Phase 1 schema) ✅ |
| 명령 예시 | parser intent 추출 (Phase 2) — "변경" / "취소" 키워드 ✅ |
| 필수 입력값 | resolve_target_appointment 가 patient_id + target_date 필수 ✅ |
| 선택 입력값 | reason / 변경 항목 ✅ |
| DB 조회 | resolve_target_appointment / validator 가 read-only ✅ |
| 승인 필요 | `approval_disabled` 게이트 + Gate 2 ✅ |
| 실행 가능 조건 | validation.can_approve + diff.changed_fields ✅ |
| 실행 금지 조건 | 시간 겹침 / 휴무 / 이미 취소 / 변경 사항 없음 ✅ |
| 호출 service | UpdateServiceCallable / CancelServiceCallable Protocol (직접 SQL ⊥) ✅ |
| 하네스 케이스 | parser / resolver / validator / approval / executor / regression / runtime — 26 단위 ✅ |
| 실제 동작 확인 | service mock 호출 인자 검증 + DB row 변화 0 검증 ✅ |
| 정상 케이스 | test_execute_update_calls_service / test_execute_cancel_calls_service ✅ |
| 실패 / 예외 케이스 | overlap / leave / canceled / no_change / service_exception ✅ |

- ✅ AI_SAFETY_POLICY § 1.1 (승인 없는 변경 / 취소 금지 / 물리 삭제 금지) 모두 반영
- ✅ AiCommandStatus.EXECUTED / VALIDATION_FAILED / FAILED 사용

### 8 — 표현 / 명명 / 헤더 일관성

- ✅ resolve_* / build_* / validate_* / execute_approved_* / build_*_preview 일관
- ✅ TargetAppointment / TargetResolution / ChangeExecutionResult / AppointmentDiff dataclass 명명 일관

### 9 — 추가수정사항 반영 / SSOT

- ✅ 추가수정사항 1 (단위화)
- ✅ 추가수정사항 3 (Runtime Test)
- ✅ 추가수정사항 4 (10회 검증)
- ✅ 추가수정사항 5 (Codex 생략)
- ✅ 모든 실수 문서 기록 — Phase 7 시작 전 체크리스트로 #001 재발 방지

### 10 — 자만 없는 냉정한 최종 판단

| 자문 | 답변 |
|---|---|
| 자체 검증 그대로 신뢰? | ❌ resolve_target_appointment 의 fallback 동작 (시간 명시 시 미매칭 → 자동 다른 시간 fallback) 을 단위 테스트로 발견 — 다른 fallback 위험 가능성 인정 |
| 자기만족? | ❌ 1) audit 통합 미수행 — caller 책임으로 유지했으나 향후 router 통합 시 Phase 5 의 `finalize_audit` 와 동일 패턴 재사용 필요 / 2) router endpoint 는 Phase 7 명시 구현 대상이 아니므로 추가 안 함 (실수 #001 재발 방지) |
| 미점검 영역? | ✅ 1) 실제 운영 service (`app.modules.appointments.service`) 의 update / cancel 호출 시그니처와의 정합 미검증 — Protocol 만 정의, 실제 시그니처 매핑은 향후 router 통합 / 2) parser 의 update intent 추출 시 변경 항목 (시간 / 치료사 / 치료항목) 추출은 미구현 — Phase 2 parser 가 단순 "변경" 키워드로 intent 만 추출, 변경 사항 자체는 caller 가 명시 / 3) cancel intent 의 reason 추출 미구현 / 4) 과거 완료 예약 차단은 is_past_date 옵션으로만 처리 — caller 가 결정 |
| 성과 과장? | ❌ "26/26 + 2034 회귀 0 fail" 사실. parser 변경 사항 추출 / audit 통합 / 실제 service 시그니처 정합 미수행 인정 |
| Codex 사용량 제약? | ✅ 생략 |

**결론**: Phase 7 의 명시 구현 대상 (intent 2개 + 변경 전·후 비교 + 물리 삭제 금지 + 승인 후 실행) 모두 충족. 단위 테스트로 fallback 위험 1건 발견 후 수정. router 통합 / parser 변경 사항 추출 / audit 통합은 향후 Phase. Phase 8 자동 진행.

## 자동 진행 조건 충족

| 조건 | 상태 |
|---|---|
| 자체 10회 검증 | ✅ |
| 10회차 자만 없는 판단 | ✅ |
| Runtime Test | ✅ |
| 26/26 신규 + 2034 회귀 0 fail | ✅ |
| Ruff 0 error | ✅ |
| Phase 7 구현 대상 | ✅ |
| 진행 금지 조건 없음 | ✅ |
| 실수 기록 (`AI_MISTAKES_LOG.md`) | ✅ #001 재발 방지 체크리스트 적용 |

→ **Phase 8 자동 진행 가능**.
