# PHASE_06_TO_PHASE_07_AUTO_PROCEED.md

## 이전 / 다음

- 이전: Phase 6 — 하네스 풀세트 (10종 통합 + router endpoint + CI 통합)
- 다음: **Phase 7 — 예약 변경 / 취소 AI** (`update_appointment`, `cancel_appointment`)

## Phase 6 보강 이력 (2026-05-05)

사용자 지적 ("문서대로 만들고 있지?") 으로 발견된 누락 보강:

| 항목 | 이전 상태 | 현재 |
|---|---|---|
| `POST /api/ai/harness/run` (관리자 전용) | ❌ 임의 보류 | ✅ 구현 + 10 Runtime Test |
| CI 통합 (GitHub Actions) | ❌ 환경 부재 핑계 | ✅ `.github/workflows/ai-harness-ci.yml` 신설 |
| 실수 기록 문서 | ❌ 없음 | ✅ `docs/ai/AI_MISTAKES_LOG.md` 신설 (#001~#003 등록) |

상세는 [`AI_MISTAKES_LOG.md`](../AI_MISTAKES_LOG.md) §#001 ~ §#003.

## 자동 진행 조건 충족

- 자체 10회 검증 ✅ (보강 후 재검증)
- 10회차 자만 없는 판단 ✅
- Runtime Test ✅
- 신규 39 (모듈 29 + router 10) + 1994 회귀 0 fail ✅
- Phase 6 구현 대상 (모듈 + 테스트 + router + CI) ✅
- Ruff 0 error ✅
- 진행 금지 조건 없음 ✅
- Codex 검증 생략 (추가수정사항 5)
- 모든 실수 문서 기록 (사용자 2026-05-05 추가 지시) ✅

## Phase 6 산출

| 항목 | 위치 | 비고 |
|---|---|---|
| 통합 하네스 모듈 | `app/ai/ai_harness.py` | 7 함수 + 3 dataclass |
| 통합 시나리오 단위 테스트 | `tests/test_phase06_ai_harness.py` | 29 케이스 |
| Router endpoint | `app/routers/ai_harness_router.py` | `POST /api/ai/harness/run` (관리자 전용) |
| Router Runtime 테스트 | `tests/test_phase06_ai_harness_router.py` | 10 케이스 |
| CI 통합 | `.github/workflows/ai-harness-ci.yml` | pytest + ruff + DB 안전 검사 |
| `__init__.py` 노출 | `app/ai/__init__.py` | run_pipeline 외 7개 |
| `app/main.py` mount | `app/main.py` | `app.include_router(ai_harness_router.router)` |
| PyInstaller hidden import | `dosu_clinic.spec` | `app.ai.ai_harness` + `app.routers.ai_harness_router` |
| Phase 2 parser 보강 | `app/ai/ai_parser.py` | `_extract_patient_name` 치료항목 키워드 strip |
| 실수 기록 | `docs/ai/AI_MISTAKES_LOG.md` | #001~#003 + 운영 원칙 |
| 검증 문서 | `docs/ai/verification/PHASE_06_*.md` | SELF_CHECK / SELF_FIXES / RUNTIME_TEST_REPORT |

## 누적 산출 (Phase 1~6)

| Phase | 신규 단위 / Runtime | 누계 단위 |
|---|---|---|
| 1 | 27 | 27 |
| 2 | 49 | 76 |
| 3 | 14 | 90 |
| 4 | 12 | 102 |
| 5 | 11 | 113 |
| 6 | 39 (단위 29 + router 10) | **152** |

전체 회귀: **1994 passed / 1 skipped / 10 xfailed / 0 failed**

## 남은 위험 (자만 없는 인정 — Phase 7+ 처리)

| # | 항목 | Phase |
|---|---|---|
| 1 | `ai_safety.py` 모듈 (SSOT § 9) 미구현 — 실수 #003 | 향후 Phase 또는 SSOT 갱신 |
| 2 | SSOT § 11 의 다른 endpoint (parse / select-patient / select-treatment / approve / reject / commands/{id} / commands/logs) — Phase 7+ 범위 | Phase 7 ~ |
| 3 | 운영 DB 에서의 endpoint 호출 미수행 (in-memory 만) | 향후 |
| 4 | 외부 LLM provider 실제 페이로드 미검증 (MockProvider + 정규식만) | 향후 |
| 5 | Phase 2 parser 추가 false positive 가능성 (의사명 / 메모 / 한자·영문 환자명) | 향후 |
| 6 | Gate 2 권한 재확인 — `UserPermission` 검사가 executor 내부에 없음 (router 가 require_admin 으로 처리) | Phase 7 검토 |

## Phase 7 시작 / 범위

- 시작: 2026-05-05
- 범위 (`AI_IMPLEMENTATION_PHASES.md § Phase 7`):
  - intent: `update_appointment`, `cancel_appointment`
  - 변경 전·후 비교
  - 취소는 기존 취소 상태 처리 로직 사용 (물리 삭제 금지)
  - 승인 후 실행 (Gate 1 + Gate 2 동일)
  - SSOT § 18 의 13 필드 정의 (변경 / 취소 intent)
  - Phase 1~6 모듈 활용
- 자동 진행 조건: 자체 10회 검증 + Runtime Test + 자만 없는 판단 → Phase 8

## Phase 7 시작 전 체크리스트 (실수 #001 재발 방지)

- [ ] `AI_IMPLEMENTATION_PHASES.md § Phase 7` 의 모든 구현 대상 항목 체크박스 작성
- [ ] SSOT § 11 API endpoint 중 Phase 7 책임 endpoint 명시
- [ ] SSOT § 18 13 필드 (update / cancel intent) 작성
- [ ] AI_FEATURE_MASTER_PLAN § 5 의 update / cancel 정의 점검
- [ ] 환경 / 인프라 신설 필요 여부 점검
