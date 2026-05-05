# RE_VERIFICATION_LOG.md

> Phase 1~11 1차 구현 완료 후 사용자 지시로 진행하는 **재검증 루프 10회 기록**.
> 각 회차마다: 전체 pytest 실제 작동 + 발견 사항 / 수정 / 자만 없는 판단.

## 사용자 지시 (2026-05-05)

- "혼자서 페이즈끝까지 진행하고 끝나면 다시한번 페이즈1~끝까지 재검증루프 10회반복"
- "하면서 매 검증루프1회마다 기능 실제 작동하는지도 확인"

## 재검증 회차

각 회차는 다음을 수행:
1. 전체 pytest 실제 실행 (실제 작동 확인)
2. Ruff 전체
3. DB 경로 안전 검사
4. SSOT § 9 / § 11 / § 18 정합 점검
5. 새로 발견한 실수 / 누락 → `AI_MISTAKES_LOG.md` 추가
6. 자만 없는 판단

---

## 재검증 1/10 (2026-05-05)

### 실제 작동

- pytest tests -q → **2114 passed, 1 skipped, 10 xfailed, 0 failed** (17.40s)
- ruff check app tests → **All checks passed!**
- DB 경로 안전: in-memory 만 사용, conftest.py 가 격리 강제

### SSOT 정합 (§ 9 / § 11 / § 18)

§ 9 모듈 — 10/10 ✅:
- ai_command_schema / ai_provider / ai_parser / ai_resolver / ai_validator
- ai_preview / ai_executor / ai_audit / ai_safety / ai_harness — 모두 존재

§ 11 API — 8/8 중 1 구현, 7 미구현 (실수 #004 — Phase 명시 외 임의 추가 ⊥):
- ✅ POST /api/ai/harness/run (Phase 6)
- ⊘ commands/parse, select-patient, select-treatment, approve, reject, GET, logs (Phase 명시 외)

§ 18 13 필드 — 모든 1~5차 intent 모듈 + 단위 테스트 ✅:
- create_appointment (Phase 1~5) / update / cancel (Phase 7) / create_leave (Phase 8) / prepare_sms (Phase 9) / summarize_today / summarize_tomorrow / analyze_stats (Phase 10) / data_quality_check / ops_assistant (Phase 11)

### 모듈 / 테스트 카운트

- app/ai/*.py 16 modules + __init__.py
- tests/test_phase*.py 13 (phase01 ~ phase11 + harness_router + safety)

### 발견 / 수정

- 없음. 1차 진행 시 발견된 실수 #001~#004 모두 적용 / 보강.

### 자만 없는 판단

- ✅ 1차 통과 보장 — 모든 단위 테스트 + lint + DB 가드 정합
- ❌ 다음 회차에서 추가로 점검할 영역:
  - SSOT § 11 의 미구현 endpoint 7건의 향후 진행 결정
  - 실제 운영 service 시그니처와 Protocol 정합 (Phase 7 의 update / cancel service / Phase 8 의 leave service)
  - Phase 2 parser 의 update intent 변경 사항 추출 (시간 / 치료사 / 치료항목) 미구현
  - ai_harness 와 ai_safety 의 중복 구현 (privacy / hallucination 함수가 양쪽에 정의)

## 재검증 2/10

### 발견 + 수정

- ai_harness 의 자체 `_PRIVACY_FORBIDDEN_KEYS` / `_FORBIDDEN_PHRASES` / `check_privacy_payload` / `check_hallucination` 와 ai_safety 의 동일 구현 → **DRY 위반** 발견.
- ai_harness.py 가 이제 `ai_safety` 를 single source of truth 로 re-export — 중복 제거.
- 기존 import 호환성 유지 (`from app.ai.ai_harness import check_privacy_payload` 그대로 동작).

### 실제 작동

- pytest tests -q → **2114 passed / 0 failed** (변동 없음)
- ruff → 0 error

### 자만 없는 판단

- 회차 1 의 미점검 영역 4건 중 1건 (DRY) 해결.
- 남은 3건은 SSOT § 11 endpoint / Phase 2 parser update / 실제 service 시그니처 — 다음 회차 점검.

## 재검증 3/10

### 검증

- pytest → 2114 passed / 0 failed
- ruff → 0
- Phase 2 parser 가 update / cancel intent 의 *변경 후* 인자 추출 점검:

| 입력 | intent | time_text | 변경 후 시간 추출? |
|---|---|---|---|
| "박환자 내일 9시 예약을 10시로 변경" | UPDATE_APPOINTMENT | "9시" (변경 전) | ❌ "10시로" 미추출 |
| "차트번호 12345 5월 10일 박치료사 → 김치료사로 변경" | UPDATE_APPOINTMENT | None | ❌ "→ 김치료사" 미추출 |
| "박환자 4월30일 예약 취소" | CANCEL_APPOINTMENT | None | (cancel 은 변경 후 인자 없음) |

### 결정

- Phase 2 parser 의 update intent 변경 후 인자 추출은 **명시 구현 대상이 아님** (Phase 7 명시 대상은 모듈 + diff + service callable).
- Phase 7 의 ai_appointment_change 모듈은 caller (router / 향후 UI) 가 new_target_date / new_start_hour / new_therapist_id 를 *명시 인자* 로 전달하는 패턴 유지.
- 자연어에서 변경 후 인자 추출은 향후 별도 보강 작업으로 분리.

### 자만 없는 판단

- 본 회차에서 Parser 한계를 명시적으로 확인 — 모듈 자체는 의도된 분리 (parser=intent 추출, update 인자=caller 책임).
- "마음대로 만들지 않음" 정책 정합 — Phase 7 명시 대상 외 추가 변경 없음.

## 재검증 4/10

### 검증

- pytest → 2114 passed / 0 failed
- ruff → 0
- 16 AI 모듈 (Phase 1~11) public API 검사 — 금지 함수 (delete_patient / merge_patients / auto_create_appointment / auto_register_leave / auto_send / dispatch_sms) 미노출 ✅

### 안전 게이트 종합 정합

| 정책 | 게이트 모듈 |
|---|---|
| AI 직접 DB 수정 ⊥ | ai_executor (callable 만) / ai_validator / ai_resolver / ai_summary / ai_ops 모두 read-only 또는 callable 패턴 |
| 승인 없이 예약 / 취소 / 변경 / 휴무 / 신환 ⊥ | Gate 1 (preview approval_disabled) + Gate 2 (executor revalidation) |
| 자동 발송 ⊥ | ai_sms_prepare 가 send 함수 미노출 |
| 자동 수정 / 병합 / 삭제 ⊥ | ai_ops 가 자동 수정 함수 미노출 |
| 외부 AI API 에 PII ⊥ | ai_safety.check_privacy_payload (12 키 차단) |
| 할루시네이션 ⊥ | ai_safety.check_hallucination (4 표현 / 치료항목 정합) |

### 자만 없는 판단

- 정책 게이트가 모듈 단위로 자체 가드 (`test_module_does_not_expose_*` 회귀 방지) — 강력한 보장
- 단, 게이트는 *함수명* 기준 — 다른 이름으로 우회 가능. 회귀 방지 강도 한정 인정.

## 재검증 5/10

### 검증

- pytest → 2114 passed / 0 failed (변동 없음)
- ruff → 0

### SSOT § 11 매핑 표 (실수 #004 후속)

| Endpoint | Phase 명시? | 현재 |
|---|---|---|
| POST /api/ai/commands/parse | ❌ 어느 Phase 도 명시 안 함 | 미구현 |
| POST /api/ai/commands/{id}/select-patient | ❌ | 미구현 |
| POST /api/ai/commands/{id}/select-treatment | ❌ | 미구현 |
| POST /api/ai/commands/{id}/approve | ❌ | 미구현 |
| POST /api/ai/commands/{id}/reject | ❌ | 미구현 |
| GET /api/ai/commands/{id} | ❌ | 미구현 |
| GET /api/ai/commands/logs | ❌ | 미구현 |
| **POST /api/ai/harness/run** | ✅ Phase 6 | ✅ 구현 + 10 Runtime |

### 결정

- 7 endpoint 미구현은 SSOT 와 PHASES 의 **정합 부족** 으로 사용자 결정 영역.
- Phase 1~11 진행 중에는 *임의 추가 ⊥* 정책 유지 (실수 #001 재발 방지).
- 본 회차에서 추가 구현하지 않음. 사용자가 명시 지시 시 별도 PR / Phase 로 진행.

### 자만 없는 판단

- 7 endpoint 미구현이 SSOT 정합 위반이지만, *명시 구현 대상이 아니면 추가 ⊥* 가 사용자 명시 정책 (실수 #001 재발 방지 회차 10 격상 기준).
- 후속 작업 시 사용자가 결정 — SSOT 갱신 또는 별도 Phase 신설.

## 재검증 6/10

### 검증

- pytest → 2114 passed / 0 failed
- ruff → 0
- spec hidden imports — `app.ai.ai_*` 16 모듈 모두 등록 ✅
- `app/ai/__init__.py` exports — 65 개 (모든 Phase 1~11 공개 API)
- 신규 `app/routers/ai_harness_router.py` 도 spec 등록 ✅

### 자만 없는 판단

- 빌드 누락 위험 0 — PyInstaller spec 이 모든 신규 모듈을 인지

## 재검증 7/10

### 검증

- pytest → 2114 passed / 0 failed
- ruff → 0
- 검증 문서 카운트 (`docs/ai/verification/`):
  - 37 .md 파일
  - 11 PHASE_*_CLAUDE_SELF_CHECK.md (Phase 0~11)
  - 11 PHASE_*_RUNTIME_TEST_REPORT.md (Phase 0 은 코드 변경 없으므로 면제, 그 외 Phase 1~11)
  - 11 PHASE_*_TO_PHASE_*_AUTO_PROCEED.md
- 마이그레이션: 20 개 (m001 ~ m020) — m019 (ai_command_logs) / m020 (treatment_aliases) 포함

### 자만 없는 판단

- 검증 문서 누적 충실 — 회귀 검증 시 Phase 별 추적 가능
- Phase 11 의 AUTO_PROCEED 는 더 이상 다음 Phase 가 없으므로 별도 작성 ⊥ — 본 RE_VERIFICATION_LOG 가 후속 추적 역할

## 재검증 8/10

### 검증 — Phase 별 격리 실행

| Phase 테스트 | 결과 |
|---|---|
| test_phase01_ai_command.py | 20/20 ✅ |
| test_phase02_ai_parser_resolver.py | 49/49 ✅ |
| test_phase03_ai_validator_preview.py | 33/33 ✅ |
| test_phase04_ai_new_patient_flow.py | 16/16 ✅ |
| test_phase05_ai_executor.py | 11/11 ✅ |
| test_phase06_ai_harness.py | 29/29 ✅ |
| test_phase06_ai_harness_router.py | 10/10 ✅ |
| test_phase06_ai_safety.py | 14/14 ✅ |
| test_phase07_ai_update_cancel.py | 26/26 ✅ |
| test_phase08_ai_leave.py | 27/27 ✅ |
| test_phase09_ai_sms_prepare.py | 14/14 ✅ |
| test_phase10_ai_summary.py | 19/19 ✅ |
| test_phase11_ai_ops.py | 20/20 ✅ |

**합계: 288 Phase 1~11 단위 + 1826 기존 회귀 = 2114 passed.**

### 자만 없는 판단

- 격리 실행에서도 모두 통과 — Phase 간 의존성 / 부작용 ⊥ 입증

## 재검증 9/10

### DB 안전 종합

- pytest → 2114 passed
- conftest.py 가 APPDATA + DOSU_DB_PATH 환경변수 격리 → in-memory DB 만 사용
- scripts/check_db_path.py 단독 실행 시 운영 DB 경로 INFO 안내 (정상)
- **운영 DB `%APPDATA%\도수치료예약\clinic.db` 미접근** ✅ (CLAUDE.md 절대 금지 정합)

### 자만 없는 판단

- DB 경로 격리는 conftest.py + assert_safe_db_path() 이중 가드
- 모든 Phase 1~11 단위 테스트가 자체 in-memory SQLAlchemy session 사용 — 운영 DB 우발 접근 위험 0

## 재검증 10/10 — 최종 종합

### 최종 실제 작동

- **pytest tests -q → 2114 passed, 1 skipped, 10 xfailed, 0 failed (17.12s)**
- **ruff check app tests → All checks passed!**
- DB 경로 안전 검사 — 격리 정상

### Phase 1~11 산출 종합

| 항목 | 수량 |
|---|---|
| AI 모듈 | 16 (`app/ai/ai_*.py`) + `__init__.py` |
| Router | 1 (`app/routers/ai_harness_router.py`) |
| 마이그레이션 | 2 (m019 / m020) |
| Phase 단위 테스트 | 13 파일 / **288 테스트** |
| 검증 문서 | 37 (`docs/ai/verification/*.md`) |
| 실수 기록 | 4 (#001~#004) + 운영 원칙 |
| 전체 회귀 | **2114 passed / 0 failed** |
| Ruff | 0 error |
| CI workflow | 1 (`.github/workflows/ai-harness-ci.yml`) |
| PyInstaller spec 등록 | 16 + 1 router |
| `__init__.py` exports | 65 |

### Phase 매핑

| Phase | intent | 신규 단위 | 모듈 |
|---|---|---|---|
| 1 | (스키마/provider/audit) | 27 (20+7 ai_safety) | command_schema / provider / audit |
| 2 | create_appointment 일부 | 49 | parser / resolver |
| 3 | create_appointment 일부 | 33 | validator / preview |
| 4 | 신환 흐름 | 16 | new_patient_flow |
| 5 | create_appointment 실행 | 11 | executor |
| 6 | (하네스 풀세트) | 53 | safety / harness / harness_router |
| 7 | update / cancel | 26 | appointment_change |
| 8 | create_leave | 27 | leave |
| 9 | prepare_sms | 14 | sms_prepare |
| 10 | summarize / analyze | 19 | summary |
| 11 | data_quality / ops | 20 | ops |

### 안전 정책 종합 (재검증 4/10 결과 인용)

| 정책 | 상태 |
|---|---|
| AI 직접 DB 수정 ⊥ | ✅ executor / validator / resolver / summary / ops 모두 read-only or callable |
| 승인 없이 예약 / 취소 / 변경 / 휴무 / 신환 ⊥ | ✅ Gate 1 + Gate 2 |
| 자동 발송 ⊥ | ✅ ai_sms_prepare 가 send 함수 미노출 |
| 자동 수정 / 병합 / 삭제 ⊥ | ✅ ai_ops 가 자동 수정 함수 미노출 |
| 외부 AI API PII ⊥ | ✅ ai_safety.check_privacy_payload (12 키 차단) |
| 할루시네이션 ⊥ | ✅ ai_safety.check_hallucination |
| manual60 = 1 정책 | ✅ test_treatment_count_uses_simple_row_count 가드 |
| 운영 DB 미접근 | ✅ conftest 격리 + assert_safe_db_path |

### 자만 없는 최종 판단

| 자문 | 답변 |
|---|---|
| 자체 검증 그대로 신뢰? | ❌ 1차 진행 시 router endpoint / CI / ai_safety 누락이 자체 검증을 통과했음. 사용자 지적 후 보강. 현재도 다른 누락 가능성 인정 |
| 자기만족? | ❌ 1) SSOT § 11 의 7 endpoint 미구현 (실수 #004) — 사용자 결정 필요 / 2) parser 의 update intent 변경 인자 추출 미구현 / 3) 외부 LLM provider 실제 페이로드 검증 미수행 / 4) 운영 DB 에서 endpoint 호출 미수행 |
| 미점검 영역? | ✅ 위 4건 + 의사명 / 메모 / 한자·영문 환자명 parser false positive 가능성 / 외부 LLM 자동 발송 / 자동 수정 우회 (다른 함수명) |
| 성과 과장? | ❌ "2114 passed / 0 failed / 16 모듈 + 1 router + 288 단위" 사실. 명시 구현 대상 외 임의 추가 ⊥ 정책 정합 |
| Codex 사용량 제약? | ✅ 생략 (사용자 추가수정사항 5) |

### 결론

**Phase 1~11 1차 구현 + 재검증 10회 완료.**

- 모든 Phase 명시 구현 대상 충족
- 회귀 0 fail / Ruff 0 / DB 안전 / 정책 게이트 16/16 모듈
- 발견된 실수 4건 모두 `AI_MISTAKES_LOG.md` 기록 + 재발 방지 체크리스트 반영
- 사용자 결정 필요 영역 (SSOT § 11 7 endpoint / parser update / 외부 service 시그니처) 은 명시 구현 대상이 아니므로 *임의 추가 ⊥*

**남은 작업 (사용자 결정 시 진행):**
1. SSOT § 11 의 7 endpoint 구현 — Phase 명시 구현 대상으로 격상 또는 별도 Phase 신설
2. 외부 LLM provider (OpenAI / Anthropic) 실제 호출 시 페이로드 / Privacy 게이트 검증
3. 실제 운영 service (`app.modules.appointments.service`, `app.modules.leaves.service`) 와 Protocol 시그니처 정합
4. UI / 디자인 적용 (사용자 § 16 정책 — Phase 1~5 완료 후 적용 — 현재는 시점 도달이지만 별도 작업)
