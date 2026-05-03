# 19-P-5 단위화 리팩토링 — 테스트 전략 (19_refactor_test_strategy, r2 보정본)

> 19-P-1 [현재 구조](19_refactor_current_state.md), 19-P-2 [목표 아키텍처](19_refactor_target_architecture.md),
> 19-P-3 [모듈 매핑](19_refactor_module_map.md), 19-P-4 [의존성 맵](19_refactor_dependency_map.md) 의 후속 문서.
> **단위화 리팩토링을 시작하기 전에**, 기존 기능이 깨지지 않도록 모듈별 테스트 전략과 필수 회귀 테스트 기준을 문서화한다.
> 본 문서는 *전략* 문서 — 테스트 코드를 직접 작성하거나 변경하지 않는다.

## 0. 메타

- 작성일: 2026-05-02
- 기준 브랜치: `ai-rag-v1-integration`
- 기준 커밋 (HEAD): `bcd74a7aabc9de8d735425863254cfc393bda580` (release v1.3.3)
- 18-8 baseline: **529 passed, 1 skipped, 7 xfailed** ([reports/ai_dev_loop/18-8_test_report.md](../../reports/ai_dev_loop/18-8_test_report.md))
- 19-P-1 r2 / 19-P-2 r3 / 19-P-3 r1 / 19-P-4 r2 Codex 판정: **pass / pass / pass with caveat / pass with caveat** ([reports/refactor/19-P-4_codex_review.md](../../reports/refactor/19-P-4_codex_review.md))
- 본 세션 정책: **읽기 전용** — `app/`, `tests/`, `app/migrations/`, `requirements*.txt`, `dosu_clinic.spec`, `app/templates/`, `app/static/`, `pyproject.toml` 1바이트도 수정 금지.
- 본 문서는 *전략* 문서 — 새 테스트 / 하네스 / fixture / mock 을 실제로 만들지 않는다.
- **r1 Codex 검증 (2026-05-02 fail)** 후 본 r2 보정 — 보정 이력:
  - **r2 보정** (Codex r1 G-2 fail + 추가 발견 5개 항목):
    - §3-1 appointments — "예약 생성/수정/삭제/낙관적 락/충돌/점심창 = 있음" 과장 표현 수정. 실제 [tests/test_appointment_rules.py](../../tests/test_appointment_rules.py) 는 필수값/외래키 + 비도수 중복 허용만 정방향, 도수 중복 차단 3건 `xfail`, 취소-후-중복 1건 `skip`, 점심창/PUT/DELETE/409 전용 테스트 부재.
    - §3-5 leaves — full/am/pm 차단 "있음" 과장 표현 수정. 실제 [tests/test_therapist_leave.py](../../tests/test_therapist_leave.py) 는 4건 모두 `xfail` (백엔드 미구현 명시), 등록 측면 (`(employee_id, leave_date)` UNIQUE, `leave_kind`) 만 정방향.
    - §4 / §9 종합 — 20개 항목 분류 숫자 9/7/4 → **6/9/5** 로 정정 (Codex 실측 기준).
    - §2-5 db_guard 표현 — "모든 테스트 자동 (2회)" → "import-time 1회 + session fixture 1회" 로 정확히 표기.
    - §0-1 캐비엇 표 보강.

### 0-1. 19-P-4 Codex r2 caveat 본 19-P-5 반영

| caveat | 19-P-5 반영 |
|---|---|
| `leave_type=am/pm/full` 백엔드 차단 로직 위치 미확인 | §3-1 / §3-5 / §4 / §6-A / §7-2-C 에서 **분리 직전 grep + 백엔드 차단 검증 contract 테스트 보강** 으로 명시. 19-P-4 Codex 가 "분리 직전 contract/rules 테스트로 명확히 잠가야 함" 을 권고함. **r2 보정**: 현재 [test_therapist_leave.py](../../tests/test_therapist_leave.py) 의 full/am/pm 차단 4건이 모두 `xfail` 상태 — 백엔드 차단 코드 추가 후 marker 제거 + 정방향 전환 필요. |
| dependency_map.md 줄수 표기 "620 vs 622" minor | 본 19-P-5 에서는 줄수 메타보다 실제 테스트 대상 우선 — 19-P-4 Codex 결론과 정합. |
| pytest 미실행 (문서 검증만) | 본 19-P-5 도 read-only 문서 세션 — pytest 실행은 19-P-6 이후 실제 코드 이동 단계에서 수행. |

### 0-2. 19-P-5 r1 Codex 검증 (2026-05-02 fail) 본 r2 반영

| 지적 | r2 보정 |
|---|---|
| §3-1 "예약 생성/점심창/충돌 차단 = 있음" 과장 | §3-1 표를 실제 테스트 상태에 맞게 재분류 — `xfail` 3건 / `skip` 1건 / 부재 다수 명시 |
| §3-5 "종일 휴무 등록+차단 있음" 부정확 | §3-5 표 — full/am/pm 차단 4건 모두 `xfail` (백엔드 미구현) 명시. 등록 측면 (`UNIQUE`, `leave_kind`) 만 정방향 |
| §4/§9 분류 숫자 9/7/4 vs 실제 표 6/9/5 불일치 | §4 종합 + §9 종합 모두 **6 existing / 9 needed / 5 follow-up** 으로 정정 |
| §2-5 `db_guard` 표현 부정확 | "import-time 1회 + session fixture 1회" 명시 |
| pytest 미실행 (read-only 검증) | 본 r2 도 read-only — 19-P-6 이후 코드 이동 단계에서 pytest 실행 |

---

## 1. 테스트 전략 원칙

| # | 원칙 | 본문 |
|---|---|---|
| T-1 | 리팩토링 = 구조 변경, 기능 변경 X | 단위화의 목적은 **구조 안정화**. 예약/휴무/문자/통계/AI 결과는 변경 전후 동일해야 한다. |
| T-2 | 이동 전후 결과 동치 | 같은 입력 → 같은 응답. dict 단위 비교가 가능한 경우 그대로 보존. |
| T-3 | 기존 API URL / 응답 key 보존 | [19_refactor_current_state.md §21](19_refactor_current_state.md) 의 33+ 키 셋 (manual/search 3 + manual/ask 9 + sources 3 + health 9 + health/public 4 + status 9 + 비-AI alias) 보존. **추가만** 허용. |
| T-4 | 프론트 동작 보존 | [main.html](../../app/templates/main.html) 7331줄 + JS / FullCalendar / Alpine 의존 키 보존. UI 분리는 19-P 비-목표. |
| T-5 | DB schema 보존 | m001~m013 diff 0. 컬럼 rename 금지. 신규 마이그레이션은 m014 부터 — 19-P 기간 내 가능하면 미도입. |
| T-6 | 한 세션 = 한 모듈 (또는 작은 범위) | 한 번에 모든 도메인 분리 X. 모듈 1개씩 wrapper/adaptor → 내부 위임 → wrapper 제거 순서. |
| T-7 | 5회 루프 정책 | [docs/AI_WORKING_RULES.md §3](../AI_WORKING_RULES.md). 1회차 = 테스트 + 분석 + 수정. 5회 안에 통과 → 성공 리포트. |
| T-8 | 5회 실패 시 rollback / 재작성 | 땜질식 수정 금지. `latest_failure_report.md` + 사용자 결정. 5회 후에는 rollback 우선 검토. |
| T-9 | Codex 검증 게이트 | Claude Code 자체 통과 = 최종 완료 X. Codex 가 실제 diff·파일·결과·로그 독립 확인 후에만 다음 세션 진입. |
| T-10 | 하네스 / 테스트 약화 금지 | `tests/conftest.py` 4단계 격리, `_block_sdk_modules`, `tests/harness/db_guard.assert_safe_db_path()` 우회/약화 금지. 실패 테스트를 `xfail`/`skip` 으로 덮지 않는다 (원인 수정). |
| T-11 | 운영 DB 미접근 | `%APPDATA%\도수치료예약\clinic.db` 미접근. 모든 테스트는 `tests/conftest.py` 격리 경로. `scripts/check_db_path.py` 머지 게이트. |
| T-12 | 외부 API 호출 0 | conftest `_block_sdk_modules` 가 openai/anthropic SDK 클래스를 RuntimeError 로 교체. FakeProvider / FakeEmbeddingProvider 만 사용. |
| T-13 | local-first 보존 | `local_only` 모드에서 `len(provider.calls) == 0` + `len(embedding_provider.calls) == 0` 단언 유지. |
| T-14 | per-file-ignores 보존 | `pyproject.toml` `app/**/*.py` per-file-ignores 풀지 않는다 (CLAUDE.md 명시). 대량 포맷 변경 발생 방지. |
| T-15 | manual60 = 1 보존 | [app/models/constants.py:20](../../app/models/constants.py:20) `manual60` `count_increment=1`. CLAUDE.md 명시 — 절대 2로 되돌리지 않을 것. |

---

## 2. 전체 공통 테스트 (모든 19-P 세션 공통)

> 어느 모듈을 분리하더라도 **세션 시작 + 세션 종료 시점에 공통으로 실행**해야 하는 기준.

### 2-1. 공통 검증 명령

| # | 명령 | 검증 대상 | 시점 |
|---|---|---|---|
| C-1 | `run_check.bat` | pytest + ruff + check_db_path 통합 | 세션 시작 + 종료 |
| C-2 | `venv\Scripts\python.exe -m pytest tests -v` | 전체 회귀 (529 passed baseline) | 세션 종료 (큰 모듈 이동 후) |
| C-3 | `venv\Scripts\python.exe -m ruff check app tests scripts` | lint (per-file-ignores 보존) | 세션 종료 |
| C-4 | `venv\Scripts\python.exe scripts/check_db_path.py` | 운영 DB 경로 안전 검사 | 세션 시작 + 종료 |

### 2-2. 18 시리즈 하네스 (AI/RAG)

| # | 하네스 | 테스트 파일 | 검증 대상 |
|---|---|---|---|
| H-1 | 18-0 RAG / Safety / Full | [test_full_harness.py](../../tests/test_full_harness.py), [test_ai_full_harness.py](../../tests/test_ai_full_harness.py), [test_rag_pipeline.py](../../tests/test_rag_pipeline.py), [test_rag_safety.py](../../tests/test_rag_safety.py), [test_ai_safety_harness.py](../../tests/test_ai_safety_harness.py) | RAG 파이프라인 + PII / 할루시네이션 가드 + LLM/Embedding 호출 카운트 |
| H-2 | 18-3 Chunker | [test_ai_chunker_harness.py](../../tests/test_ai_chunker_harness.py) | 결정적 chunker 메타데이터 / 경계 |
| H-3 | 18-4 Reindex | [test_ai_reindex_harness.py](../../tests/test_ai_reindex_harness.py) | reindex skip / upsert / 실패 보존 / lock |
| H-4 | 18-5 Vector | [test_ai_vector_harness.py](../../tests/test_ai_vector_harness.py) | embeddings / store / `local_only` 시 호출 0 |
| H-5 | 18-6 Hybrid | [test_hybrid_retriever.py](../../tests/test_hybrid_retriever.py) | keyword + vector 결합 |
| H-6 | 18-7 관리자 상태 | [test_ai_health_status.py](../../tests/test_ai_health_status.py), [test_admin_ui_smoke.py](../../tests/test_admin_ui_smoke.py) | `/api/ai/status` 9 top-level 키 |

### 2-3. 기존 AI (v1.3.3 이전) 회귀 테스트

| # | 영역 | 테스트 파일 |
|---|---|---|
| A-1 | SMS AI | [test_ai_sms_validate.py](../../tests/test_ai_sms_validate.py), [test_ai_sms_draft.py](../../tests/test_ai_sms_draft.py), [test_ai_sms_draft_hallucination.py](../../tests/test_ai_sms_draft_hallucination.py) |
| A-2 | 휴무 AI | [test_ai_action_leave.py](../../tests/test_ai_action_leave.py) |
| A-3 | 매뉴얼 Q&A wrapper | [test_ai_manual_qa.py](../../tests/test_ai_manual_qa.py) |
| A-4 | AI 로깅 | [test_ai_logging.py](../../tests/test_ai_logging.py) |
| A-5 | AI 할루시네이션 | [test_ai_hallucination.py](../../tests/test_ai_hallucination.py) |
| A-6 | AI 모드 (local_only / local_first / ai_assist) | [test_ai_assist_mode.py](../../tests/test_ai_assist_mode.py), [test_local_only_mode.py](../../tests/test_local_only_mode.py) |
| A-7 | health public | [test_ai_health_public.py](../../tests/test_ai_health_public.py) |

### 2-4. API contract 테스트

| # | 영역 | 테스트 파일 / 보강 후보 |
|---|---|---|
| API-1 | manual_qa contract (search/ask) | [test_ai_manual_rag_contract.py](../../tests/test_ai_manual_rag_contract.py), [test_ai_contract_manual.py](../../tests/test_ai_contract_manual.py), [test_ai_manual_rag_harness.py](../../tests/test_ai_manual_rag_harness.py) — **있음** |
| API-2 | health (admin/public) contract | [test_ai_health_public.py](../../tests/test_ai_health_public.py), [test_ai_health_status.py](../../tests/test_ai_health_status.py) — **있음** |
| API-3 | 비-AI 86 endpoint contract | **부재** (19-P-1 §22 C-1) — **각 모듈 분리 직전 보강 필수** |

### 2-5. 운영 DB 보호 / 외부 API 차단 검사

> **r2 보정**: S-3 표현을 "모든 테스트 자동 (2회)" → "import-time 1회 + session fixture 1회" 로 정확히 표기 (Codex r1 G-2 추가 발견 항목 정합).

| # | 검사 | 위치 | 시점 |
|---|---|---|---|
| S-1 | `scripts/check_db_path.py` | 운영 DB 경로 차단 | 세션 시작 + 종료 (머지 게이트) |
| S-2 | `tests/conftest.py` 4단계 격리 (APPDATA + DOSU_DB_PATH + 워커 no-op + SDK block) | conftest import-time | 모든 테스트가 conftest 를 거치므로 자동 |
| S-3 | `tests/harness/db_guard.assert_safe_db_path()` | (1) `tests/conftest.py` import-time 1회 + (2) session-scope fixture 호출 시 1회 = 총 2회 호출 지점 | conftest 가 사용되는 모든 pytest 실행에서 자동 |
| S-4 | `_block_sdk_modules` (openai / anthropic SDK 차단) | conftest import-time | 모든 테스트 자동 |
| S-5 | `test_*_does_not_use_operational_db` 다수 | 운영 경로 미접근 단언 | 회귀에서 자동 |

### 2-6. PyInstaller 검증 시점

| # | 검사 | 시점 |
|---|---|---|
| P-1 | `tests/test_pyinstaller_hidden_imports.py` (53 tests) | **각 모듈 분리 후 spec hidden imports 갱신과 동시에** |
| P-2 | `tests/test_migration_spec_discovery.py` | 새 마이그레이션 / 폴더 구조 변경 시 |
| P-3 | 실제 `pyinstaller --noconfirm dosu_clinic.spec` 빌드 | **주요 리팩토링 묶음 완료 후** (예: core 분리 + audit 분리 + settings 분리 묶음, 또는 19-P 종료 시점). 매 세션마다 실행하지 않음 (시간 소요). |
| P-4 | exe smoke (5 엔드포인트, 18-8 시점에 입증) | 19-P 종료 시점 + v1.4.0 배포 직전 |

> **PyInstaller 빌드 정책** (CLAUDE.md "배포 규칙"): 빌드는 사용자 명시 승인 시에만 수행. 19-P 세션이 자동으로 빌드를 트리거하지 않는다. `test_pyinstaller_hidden_imports.py` 53 tests 는 빌드 *없이도* 사전 검증 가능하므로 매 세션에서 실행.

---

## 3. 모듈별 필수 테스트 전략

> 19-P-3 [모듈 매핑](19_refactor_module_map.md) 30 모듈 + 사용자 §3 항목별 정리.
> 각 항목은 **현재 테스트 / 필수 보강 / 후속 검토** 3분류로 표기.

### 3-1. appointments

> **r2 보정**: r1 에서 "있음" 으로 표기했던 항목들의 실제 [test_appointment_rules.py](../../tests/test_appointment_rules.py) 상태를 확인 결과, 정방향 통과 테스트는 필수값/외래키 + 비도수 중복 허용만이고, 도수 중복 차단 3건 `xfail`, 취소-후-중복 1건 `skip`, 점심창/PUT/DELETE/409 전용 테스트 부재. Codex r1 G-2 fail 지적 정합.

| 영역 | 테스트 / 보강 항목 | 분류 |
|---|---|---|
| 예약 생성 — 필수값 / 외래키 / 빈 코드 / 잘못된 코드 / range 누락 | `POST /api/appointments` 400/422 | **있음** ([test_appointment_rules.py](../../tests/test_appointment_rules.py) `test_empty_treatment_codes_rejected` / `test_invalid_treatment_code_filtered_out` / `test_missing_required_fields_rejected` / `test_list_appointments_requires_range`) |
| 예약 생성 — 비도수 (eswt/injection) 같은 슬롯 중복 허용 | spec 01 §1 의도된 정책 | **있음** (`test_two_eswt_same_slot_allowed` / `test_injection_and_eswt_same_slot_allowed`) |
| 예약 생성 — 점심창 차단 (`_check_lunch_block`) | 점심 시간대 예약 차단 | **부재** → **분리 직전 보강 필수** ([api.py:64-107](../../app/routers/api.py:64) 점심창 헬퍼는 존재하지만 전용 테스트 없음) |
| 예약 생성 — 도수 중복 차단 (manual30/60) | spec 01 §1 — 같은 슬롯 도수 중복 시 두 번째 차단 | **xfail** (3건: `test_two_manual30_same_slot_blocked` / `test_two_manual60_same_slot_blocked` / `test_eswt_then_manual30_same_slot_blocked` — 백엔드 미구현 명시) → **분리 직전 백엔드 차단 코드 + 정방향 테스트 전환 필요** |
| 예약 생성 — 취소된 예약은 중복 판단에서 제외 | spec 01 §1 | **skip** (`test_canceled_manual_excluded_from_duplicate_check` — "차단 코드 추가 후 활성화" 명시) → **분리 직전 보강** |
| 예약 수정 — `PUT /api/appointments/{aid}` 정상 / 응답 키 | 수정 흐름 | **부재** (`test_appointment_rules.py` 에 PUT 전용 테스트 없음) → **분리 직전 보강 필수** |
| 예약 수정 — 낙관적 락 409 (`version` 충돌) | [api.py:1664-1679](../../app/routers/api.py:1664) `_check_version` / `_bump_version` 코드 자체는 존재 | **부재** (전용 테스트 없음) → **분리 직전 보강 필수** |
| 예약 삭제 — `DELETE /api/appointments/{aid}` + sync 위임 | 삭제 흐름 | **부재** → **분리 직전 보강 필수** |
| 예약 조회 — `GET /api/appointments` range 누락 422 | 입력 검증 | **있음** (`test_list_appointments_requires_range`) — 응답 키 contract 는 부재 → 분리 직전 보강 |
| 예약 조회 — 응답 키 / 직렬화 (FullCalendar event 형식) | `_serialize_appointment` ([api.py:186](../../app/routers/api.py:186)) | **부재** (C-1) → **분리 직전 보강 필수** |
| approve / revert-approve 흐름 | done_count ±N | **간접** ([test_stats_counts.py](../../tests/test_stats_counts.py) 의 manual 카운트 집계로 부분 보장) — 응답 키 contract 부재 |
| 휴무일 예약 차단 — 종일 (`leave_type="full"`) | full 종일 차단 | **xfail** ([test_therapist_leave.py](../../tests/test_therapist_leave.py) `test_full_day_leave_blocks_morning` / `test_full_day_leave_blocks_afternoon` — 백엔드 미구현 명시) → **분리 직전 백엔드 차단 코드 + 정방향 전환 필요** |
| 오전반차 예약 차단 (`leave_type="am"`) | < 12:00 차단 | **xfail** (`test_morning_leave_blocks_before_noon`) → 동상 |
| 오후반차 예약 차단 (`leave_type="pm"`) | >= 12:00 차단 | **xfail** (`test_afternoon_leave_blocks_after_noon`) → 동상 |
| 반차 허용 시간대 (오전반차의 오후 / 오후반차의 오전) | 반대 시간대 200 허용 | **있음** (`test_morning_leave_allows_after_noon` / `test_afternoon_leave_allows_before_noon` / `test_normal_day_for_full_day_leave_therapist_works`) |
| 기존 API 응답 key 유지 | 86 endpoint 중 예약 도메인 (10 endpoint) | **부재** (C-1) → **분리 직전 보강 필수** |
| 프론트 캘린더 표시 영향 | FullCalendar event ID / status / version 필드 보존 | **간접** (UI 자동 검증 부재 — 분리 후 수동 smoke) |
| DevTools / manual POST 우회 방지 | 점심창 / 충돌 / 락 백엔드 검증 | **부분** (백엔드 검증 코드는 존재 — 점심창 헬퍼 / 낙관적 락 / 충돌 검증 / 휴무 차단 모두 코드 차원에서 wrapper 보존 필요. 단, 휴무 차단은 현재 백엔드 미구현 — `xfail` 다수) |
| 주석 필요 위험 지점 | `# COMPAT:` (응답 키 + version) / `# NOTE:` (점심창 / 충돌 / 휴무 차단 정책) / `# RISK:` (낙관적 락 TOCTOU) / `# TODO(19-P-?):` (wrapper 제거 + xfail → 정방향 전환) | 표기 필요 |

### 3-2. patients

| 영역 | 테스트 / 보강 항목 | 분류 |
|---|---|---|
| 환자 생성/수정/조회 | `POST/PUT/GET /api/patients[/{pid}]` | **부분** ([test_employee_can_manual_contract.py](../../tests/test_employee_can_manual_contract.py) 일부 + 환자 전용 부재) → **분리 직전 보강 필수** |
| 신환 체크 유지 | `Appointment.is_new_patient` 카운트 (통계) | **있음** ([test_stats_counts.py](../../tests/test_stats_counts.py)) |
| 환자 검색 | `GET /api/patients/search` (이름/연락처/차트번호 인덱스) | **부재** → **분리 직전 보강 필수** |
| 환자별 메모 경계 | `PATCH /api/patients/{pid}/memo` 응답 + 다른 환자 영향 X | **부재** → **분리 직전 보강 필수** |
| 개인정보 로그 노출 금지 | PII 원문이 audit_log / AiUsageLog / 응답에 부재 | **있음** ([test_ai_logging.py](../../tests/test_ai_logging.py), [test_ai_safety_harness.py](../../tests/test_ai_safety_harness.py)) — 비-AI 도메인 로그는 **부재 → 분리 직전 보강** |
| 중복 검사 | `_check_patient_duplicate` (이름+연락처) | **부재** → **분리 직전 보강** |
| 환자 history / counts 응답 | `GET /api/patients/{pid}/history`, `manual-history-summary` | **부재** (C-1) → **분리 직전 보강** |
| 주석 필요 위험 지점 | `# COMPAT:` (counts dict 키) / `# SAFETY:` (PII 비노출) / `# NOTE:` (중복 검사 정책) | 표기 필요 |

### 3-3. therapists

| 영역 | 테스트 / 보강 항목 | 분류 |
|---|---|---|
| 치료사 생성/수정/조회 | `Employee.role="therapist"` | **있음** ([test_employee_*.py](../../tests/) 4 파일) |
| 활성/비활성 | `Employee.active` | **있음** |
| 치료 가능 항목 | `can_eswt`, `can_manual` | **있음** ([test_employee_can_manual_contract.py](../../tests/test_employee_can_manual_contract.py)) |
| 색상 표시 | `Employee.color` (UI 바인딩) | **간접** (UI 자동 검증 부재) |
| 휴무 모듈과 연결 | alias `therapist_id` ↔ `employee_id` 이중 키 | **있음** ([test_therapist_leave.py](../../tests/test_therapist_leave.py)) |
| `/api/therapists` alias 응답 | `_serialize_employee` 통합 | **부분** → **분리 직전 보강 권장** (alias 키 보존) |
| 입사일 (`hire_date`, m010) | 응답 키 유지 | **있음** ([test_employee_hire_date.py](../../tests/test_employee_hire_date.py)) |
| 주석 필요 위험 지점 | `# COMPAT:` (therapist alias 이중 키) / `# NOTE:` (role 분기 정책) | 표기 필요 |

### 3-4. doctors / medical_staff

> **부분 존재** (Employee `role="doctor"` + Treatment `role="doctor"` 분기) + **후속 검토** (담당의/진료과/진료실/오더/처방/EMR).
> **현재 기능이 부재한 항목을 실제 구현된 것처럼 단정하지 않음** (19-P-2 §3-3-4 정합).

| 영역 | 현재 / 후속 | 테스트 분류 |
|---|---|---|
| `_doctor_codes_set()` (의사 항목 코드) | **현재** ([api.py:153](../../app/routers/api.py:153)) | **분리 직전 보강 필수** (assignment 의 role=doctor 강제 회귀) |
| 의사 필터 통계 (`is_doctor_filter`) | **현재** ([api.py:3491-3527](../../app/routers/api.py:3491)) | **분리 직전 보강 필수** ([test_stats_counts.py](../../tests/test_stats_counts.py) 의 의사 분기 회귀) |
| 엑셀 export 의 의사 항목 suffix | **현재** ([api.py:4339-4465](../../app/routers/api.py:4339)) | **분리 직전 보강** |
| 진료과 (`department`) | **부재** | 후속 검토 (m014+ 컬럼 + 응답 키 추가 동반) |
| 진료실 / 자원 (`Room` / `Resource`) | **부재** | 후속 검토 (M-33) |
| 환자별 담당의 (`Patient.doctor_id`) | **부재** | 후속 검토 (m014+ + AI sms_draft 가드 동반) |
| 의사별 진료 일정 (`DoctorSchedule`) | **부재** | 후속 검토 |
| 오더 / 처방 (`Order` / `Prescription`) | **부재** | 후속 검토 |
| EMR 연동 | **부재** | 후속 검토 |
| AI 가 의사/진료진 정보 임의 생성 차단 | **현재 부분** (RAG hallucination guard) | **후속 보강** (의사 단정 표현 차단 패턴 추가 후보) |
| 주석 필요 위험 지점 | `# NOTE:` (role=doctor 분기 정책) / `# SAFETY:` (의사 가드 후속) / `# TODO:` (`Patient.doctor_id` / EMR 도입 시점) | 표기 필요 |

### 3-5. leaves

> **r2 보정**: r1 에서 "종일 휴무 등록 + 차단 = 있음" 으로 표기했던 항목의 실제 [test_therapist_leave.py](../../tests/test_therapist_leave.py) 상태를 확인 결과, full/am/pm 차단 4건이 모두 `xfail` (백엔드 미구현 명시). 등록 측면 (`(employee_id, leave_date)` UNIQUE, `leave_kind` annual/monthly) 만 정방향 통과. 반차 허용 시간대 (반대 시간대 200) 는 정방향 있음. Codex r1 G-2 fail 지적 정합.

| 영역 | 테스트 / 보강 항목 | 분류 |
|---|---|---|
| 휴무 등록 — `(employee_id, leave_date)` UNIQUE (m011) | 중복 등록 차단 | **있음** ([test_employee_leave_unique.py](../../tests/test_employee_leave_unique.py)) |
| 휴무 등록 — 종류 (annual / monthly / 일반, m009 `leave_kind`) | DB 컬럼 + 응답 키 | **있음** ([test_employee_leave_kind.py](../../tests/test_employee_leave_kind.py)) |
| 휴무 등록 — alias 이중 키 (`therapist_id` ↔ `employee_id`) | `/api/therapist-leaves[/bulk-set]` | **부분** (등록 흐름은 [test_employee_leave_*.py](../../tests/) 에서 간접 보장 — alias 응답 키 contract 는 분리 직전 보강 권장) |
| 휴무일 예약 차단 — 종일 (`leave_type="full"`) 오전 / 오후 | 백엔드 차단 | **xfail** ([test_therapist_leave.py](../../tests/test_therapist_leave.py) `test_full_day_leave_blocks_morning` / `test_full_day_leave_blocks_afternoon` — 2건 모두 백엔드 미구현 명시) → **분리 직전 백엔드 차단 코드 + 정방향 전환 필요** |
| 휴무일 예약 차단 — 오전반차 (`leave_type="am"`) < 12:00 | 백엔드 차단 | **xfail** (`test_morning_leave_blocks_before_noon`) → 동상 |
| 휴무일 예약 차단 — 오후반차 (`leave_type="pm"`) >= 12:00 | 백엔드 차단 | **xfail** (`test_afternoon_leave_blocks_after_noon`) → 동상 |
| 반차 허용 시간대 — 오전반차의 오후 / 오후반차의 오전 / 휴무일 외 다른 날짜 | 반대 시간대 200 허용 | **있음** (`test_morning_leave_allows_after_noon` / `test_afternoon_leave_allows_before_noon` / `test_normal_day_for_full_day_leave_therapist_works`) |
| 미니캘린더 / 예약 화면 표시 영향 | 프론트 캘린더가 휴무 표시 | **간접** (UI 자동 검증 부재) |
| devtools / manual POST 우회 방지 | 백엔드에서 휴무일 예약 차단 | **부재** (현재 백엔드 차단 미구현 → §3-1 의 `xfail` 4건 보강과 동시 처리) |
| AI 자연어 휴무 (`action_leave`) parse / preview / execute + HMAC + TOCTOU | LLM 호출 + 매칭 + 토큰 + 락 | **있음** ([test_ai_action_leave.py](../../tests/test_ai_action_leave.py) 1232줄) |
| `_upsert_employee_leave_core` 단일 진실원천 | leaves API + AI action_leave 가 같이 호출 ([api.py:1098](../../app/routers/api.py:1098)) | **있음** (같은 헬퍼 사용 — 코드 차원) → 분리 후에도 단일 진실원천 보존 검증 contract 필요 |
| 주석 필요 위험 지점 | `# NOTE:` (`leave_type` DB 표준 — `am`/`pm`/`full`) / `# RISK:` (HMAC + TOCTOU) / `# COMPAT:` (alias 이중 키) / `# TODO:` (xfail 4건 → 정방향 전환 + devtools 우회 보강) | 표기 필요 |

### 3-6. treatments

| 영역 | 테스트 / 보강 항목 | 분류 |
|---|---|---|
| 치료항목 조회 | `GET /api/treatments` + `treatment-meta` | **부분** → 분리 직전 보강 |
| 도수치료 시간별 항목 (`manual30` / `manual60`) | `count_increment=1` 정책 | **간접** ([test_stats_counts.py](../../tests/test_stats_counts.py) 의 manual 카운트 집계로 유지) |
| 체외충격파 (`eswt`) | `Treatment.code="eswt"` (M006 manual_counts 와 결합) | **있음** ([test_stats_counts.py](../../tests/test_stats_counts.py) 일부) |
| 확장 치료항목 (CRUD) | `POST/PUT/DELETE /api/treatments` | **부재** → 분리 직전 보강 |
| 완료체크 | `approve` / `revert-approve` (done_count ±N) | **있음** ([test_appointment_rules.py](../../tests/test_appointment_rules.py)) |
| 치료항목별 개별 카운트 | `PatientTreatmentCount.(patient_id, treatment_id)` UNIQUE | **있음** ([test_stats_counts.py](../../tests/test_stats_counts.py)) |
| 시간 가중치 방식으로 되돌아가지 않는지 | `manual60` `count_increment=1` 보존 (CLAUDE.md 명시) | **있음** ([app/models/constants.py:20](../../app/models/constants.py:20) 직접 단언 추가 권장) |
| 주석 필요 위험 지점 | `# NOTE:` (`manual60=1` 정책 — CLAUDE.md 명시) / `# COMPAT:` (응답 키) | 표기 필요 |

### 3-7. stats

| 영역 | 테스트 / 보강 항목 | 분류 |
|---|---|---|
| 총 예약 / 총 완료 | `summary` 응답 | **있음** ([test_stats_counts.py](../../tests/test_stats_counts.py)) |
| 도수 예약/완료 | manual 분류 | **있음** |
| 치료사별 통계 | `by-therapist` / `manual-by-therapist` / `daily-by-therapist` | **부분** (응답 키 contract 보강 필요 — C-7) |
| 치료항목별 통계 | `by-treatment` | **부분** → 분리 직전 보강 |
| 시간대 / 요일별 | `by-hour` / `by-weekday` | **부재** → 분리 직전 보강 (C-7) |
| 신환 수 (`is_new_patient`) | summary 카운트 | **있음** |
| 의사별 통계 분기 (`is_doctor_filter`) | `_doctor_codes_set` + role=doctor 필터 | **부분** → 분리 직전 보강 (현재 부분 구현) |
| ManualCount upsert | `POST /api/manual-counts` (`(count_date, therapist_id, treatment_code)` UNIQUE) | **있음** ([test_stats_counts.py](../../tests/test_stats_counts.py)) |
| 엑셀 export | `manual-schedule.xlsx` / `stats.xlsx` | **부재** → 분리 직전 보강 (C-7) |
| 취소 / 노쇼 | 현재 `status="canceled"` 만, 노쇼 별도 필드 부재 | 후속 검토 (m014+ 컬럼 도입 시) |
| 주석 필요 위험 지점 | `# COMPAT:` (8 endpoint 응답 키) / `# NOTE:` (`_get_manual_treatment_rows` / `_get_manual_therapy_codes` 정책) | 표기 필요 |

### 3-8. sms

| 영역 | 테스트 / 보강 항목 | 분류 |
|---|---|---|
| 예약문자 대상 추출 | `tomorrow-targets` (read-only) | **부재** → 분리 직전 보강 (C-2) |
| 문자 템플릿 CRUD | `GET/POST/PUT/DELETE /api/sms/templates` | **부재** → 분리 직전 보강 |
| 문자나라 연동 경계 | `_smart_decode_response` + 외부 HTTP client | **있음** (sanitize) — 외부 호출 자체는 mock 필요 |
| API key / 계정 정보 노출 금지 | `_sms_sanitize` + `_mask_phone_for_log` | **있음** ([test_sms_secret_masking.py](../../tests/test_sms_secret_masking.py)) |
| 실제 외부 발송 호출 금지 | 테스트는 외부 HTTP mock + `_block_sdk_modules` (SDK 차단은 무관) | **부재** → 분리 직전 보강 (HTTP client mock — `urllib.request` / `requests`) |
| 기존 예약문자 흐름 유지 | `POST /api/sms/send` 응답 키 (C-2) | **부재** → 분리 직전 보강 |
| AI SMS 검증 / 초안 | `/api/ai/sms/validate`, `/api/ai/sms/draft` | **있음** ([test_ai_sms_*.py](../../tests/) 3 파일) |
| 자동 발송 트리거 ⊥ | appointments → sms 호출 ⊥ (의존성 D-8) | **간접** (직접 단언 부재 — 분리 시 보강 후보) |
| 주석 필요 위험 지점 | `# SAFETY:` (API key 마스킹 / 전화번호 마스킹) / `# COMPAT:` (응답 키 — C-2/C-3) / `# RISK:` (외부 HTTP timeout / retry) | 표기 필요 |

### 3-9. admin / settings

| 영역 | 테스트 / 보강 항목 | 분류 |
|---|---|---|
| 관리자 설정 조회/저장 | `/api/system-settings` GET/POST | **부재** → 분리 직전 보강 |
| AI 모드 설정 (`ai_mode`) | `local_only` / `local_first` / `ai_assist` | **있음** ([test_ai_assist_mode.py](../../tests/test_ai_assist_mode.py), [test_local_only_mode.py](../../tests/test_local_only_mode.py)) |
| API key 등록 여부 표시 | `api_key_set` boolean 만 | **있음** ([test_ai_health_public.py](../../tests/test_ai_health_public.py), [test_ai_health_status.py](../../tests/test_ai_health_status.py)) |
| API key 원문 노출 금지 | 모든 응답에 `api_key` 평문 / 마스킹 부재 (boolean 만) | **있음** ([test_ai_contract_manual.py](../../tests/test_ai_contract_manual.py), [test_admin_ui_smoke.py](../../tests/test_admin_ui_smoke.py)) |
| feature flag (`AI_RAG_*` 환경 변수) | `AiSetting.enabled` + 환경 변수 파생 | **부분** ([test_ai_assist_mode.py](../../tests/test_ai_assist_mode.py)) |
| 권한성 설정 후보 (직원/관리자 분리) | 현재 admin 단일 등급만 | 후속 검토 |
| 인증 / 5회 잠금 | PBKDF2 + `MAX_FAILURES=5` + `LOCK_DURATION_SEC=300` | **있음** ([test_admin_auth_required.py](../../tests/test_admin_auth_required.py)) |
| 업데이트 흐름 (`/api/about/*`) | check-update / download / apply / log | **부분** ([test_update_log.py](../../tests/test_update_log.py), [test_updater_invocation.py](../../tests/test_updater_invocation.py)) → 응답 키 contract 보강 (C-5) |
| 주석 필요 위험 지점 | `# SAFETY:` (PBKDF2 + 세션 + 잠금 + DEFAULT_PASSWORD) / `# COMPAT:` (응답 키) | 표기 필요 |

### 3-10. backup

| 영역 | 테스트 / 보강 항목 | 분류 |
|---|---|---|
| 백업 목록 | `GET /api/backup/list` | **부재** → 분리 직전 보강 |
| 백업 생성 | `POST /api/backup/now` | **부재** → 분리 직전 보강 |
| 복구 후보 | `restore-latest` / `restore-by-name` / `POST /api/restore` (UploadFile + integrity_check + atomic rename) | **있음** ([test_db_restore_safety.py](../../tests/test_db_restore_safety.py)) |
| 백업 경로 표시 | `GET /api/backup/dir` | **부재** → 분리 직전 보강 |
| 운영 DB 보호 | `make_backup` / `restore_*` 가 격리 경로만 사용 | **있음** ([test_db_restore_safety.py](../../tests/test_db_restore_safety.py)) |
| 복구 후 재시작 / 새로고침 안내 | 프론트 메시지 | **간접** (UI 자동 검증 부재) |
| 자동 백업 타이머 | `start_auto_backup` daemon thread (conftest 람다 교체) | **있음** ([test_graceful_shutdown.py](../../tests/test_graceful_shutdown.py)) |
| 주석 필요 위험 지점 | `# RISK:` (백그라운드 스레드 + atomic rename + integrity_check) / `# SAFETY:` (운영 DB 격리) | 표기 필요 |

### 3-11. ai / rag

| 영역 | 테스트 / 보강 항목 | 분류 |
|---|---|---|
| local_first 유지 | `should_call_llm()` 다층 게이트 (provider_disabled / pii / local_only / no_sources / low_confidence) | **있음** ([test_full_harness.py](../../tests/test_full_harness.py), [test_ai_full_harness.py](../../tests/test_ai_full_harness.py)) |
| `local_only` 에서 LLM/Embedding 호출 0 | `len(provider.calls) == 0` + `len(embedding_provider.calls) == 0` | **있음** ([test_local_only_mode.py](../../tests/test_local_only_mode.py)) |
| sources 없음 → provider 호출 0 | reason_code `no_sources` | **있음** ([test_full_harness.py](../../tests/test_full_harness.py)) |
| low_confidence → provider 호출 0 | `LOW_SCORE_THRESHOLD=2`, `HIGH_THRESHOLD=0.7`, `LOW_THRESHOLD=0.3`, `LLM_CALL_THRESHOLD=0.3` | **있음** ([test_rag_pipeline.py](../../tests/test_rag_pipeline.py)) |
| PII detected → provider 호출 0 | `pii.scan().has_blocking` | **있음** ([test_rag_safety.py](../../tests/test_rag_safety.py), [test_ai_safety_harness.py](../../tests/test_ai_safety_harness.py)) |
| unknown_feature → provider 호출 0 | reason_code `unknown_feature` | **있음** ([test_ai_full_harness.py](../../tests/test_ai_full_harness.py)) |
| API key 없어도 local 기능 동작 | `manual/search` 200 + `manual/ask` 503 | **있음** ([test_full_harness.py](../../tests/test_full_harness.py)) |
| RAG / Safety / Chunk / Reindex / Vector / Hybrid 하네스 유지 | §2-2 H-1 ~ H-5 | **있음** |
| AI 가 환자/예약 DB 임의 생성 ⊥ | RAG → 도메인 ⊥ (D-6 / F-5) | **간접** (의존성 정책 — 분리 시 단언 추가 후보) |
| AI 의사 정보 임의 생성 차단 (후속) | 의사 단정 표현 차단 패턴 | 후속 검토 (M-36) |
| 주석 필요 위험 지점 | `# SAFETY:` (PII 마스킹 + sha256 + 200자 cap + `_block_sdk_modules`) / `# NOTE:` (임계치 상수 — 변경은 별도 결정 + eval 후) | 표기 필요 |

### 3-12. calendar / schedule_view

> 후속 검토 (post-19-P, M-26). UI 분리는 19-P 비-목표.

| 영역 | 분류 |
|---|---|
| 금일 예약 환자 표시 | 후속 검토 (현재 view-model 부재 — main.html JS 인라인) |
| 미니캘린더 표시 | 후속 검토 |
| 휴무자 표시 | 후속 검토 |
| 치료사 색상 표시 | 후속 검토 |
| 예약 저장 로직과 표시용 view-model 분리 | 후속 검토 (post-19-P 신설 후보) |
| 주석 필요 | (해당 없음 — 본 19-P 미진행) |

### 3-13. notes

| 영역 | 테스트 / 보강 항목 | 분류 |
|---|---|---|
| 당일메모 (`Appointment.memo`) | 응답 키 보존 | **부재** → 분리 직전 보강 |
| 지속 메모 (`Patient.memo`) | `PATCH /api/patients/{pid}/memo` | **부재** → 분리 직전 보강 |
| 환자별 메모 경계 | 다른 환자 영향 X | **부재** → 보강 |
| 예약별 메모 후보 | (현재 별도 `Appointment.memo` 컬럼 존재) | 분리 직전 보강 |
| 개인정보 로그 저장 금지 | 메모는 PII 포함 가능 — AI 응답 / 로그 마스킹 대상 | **있음** ([test_ai_logging.py](../../tests/test_ai_logging.py) 의 PII 마스킹) — 비-AI 도메인 로그는 보강 |
| 통합 `modules/notes/` 분리 | post-19-P (지속 메모 vs 당일 메모 정책 결정 후) | 후속 검토 |
| 주석 필요 위험 지점 | `# SAFETY:` (메모는 PII 포함 가능) / `# NOTE:` (`Patient.memo` vs `Appointment.memo` 의미 차이) | 표기 필요 |

### 3-14. health / diagnostics

> 후속 검토 (post-19-P, M-28). `/api/health` 신규 — 현재 부재.

| 영역 | 분류 |
|---|---|
| 서버 상태 | 후속 검토 (`/api/admin/status` 가 인증 상태만 — DB / 백업 / sync 상태 부재) |
| DB 상태 | 후속 검토 |
| 백업 상태 | 후속 검토 |
| AI/RAG 상태 | **있음** (`/api/ai/status` 9 top-level 키 — `modules/ai/` 가 그대로 보유) |
| main / sub 주소 표시 | **부분** (main.html 상단 모드 / 노드 ID 표시) — UI 자동 검증 부재 |
| 외부 API 호출 없이 상태 조회 | local-first 정책 보존 | **있음** (의존성 D-12) |
| 주석 필요 | (해당 없음 — 본 19-P 미진행) |

### 3-15. audit / logs

| 영역 | 테스트 / 보강 항목 | 분류 |
|---|---|---|
| 개인정보 원문 저장 금지 | `audit_log.detail` 200자 cap + AiUsageLog `prompt_hash`/`response_hash` 만 저장 | **있음** ([test_ai_logging.py](../../tests/test_ai_logging.py), [test_ai_safety_harness.py](../../tests/test_ai_safety_harness.py)) |
| API key 저장 금지 | 모든 로그 / traceback 에 부재 | **있음** ([test_sms_secret_masking.py](../../tests/test_sms_secret_masking.py), AI 로그 테스트 다수) |
| 예약/휴무/문자/AI 명령 로그 | `audit()` 호출지 + `AuditLog` insert | **부분** (AI 로그만 — 비-AI 도메인 audit 호출 회귀 부재) → 분리 직전 보강 |
| AI 로그 Outcome / reason_code | success / warning / blocked / error | **있음** ([test_ai_logging.py](../../tests/test_ai_logging.py)) |
| 보존 정책 / 오래된 로그 삭제 | 현재 무한 보존 | 후속 검토 |
| 주석 필요 위험 지점 | `# SAFETY:` (PII 원문 ⊥ / 200자 cap / API key ⊥) / `# NOTE:` (`audit()` 시그니처 변경 ⊥ — 모든 CUD 가 호출) | 표기 필요 |

### 3-16. export_import

| 영역 | 테스트 / 보강 항목 | 분류 |
|---|---|---|
| 엑셀 다운로드 (`/api/export/{manual-schedule,stats}.xlsx`) | 응답 200 + Content-Type | **부재** → 분리 직전 보강 (C-6/C-7) |
| 통계 export | 동상 (stats.xlsx) | **부재** → 분리 직전 보강 |
| CSV / 엑셀 import (`data-convert/preview`/`apply`) | `_dc_*` 헬퍼 ~600줄 | **부재** → 분리 직전 보강 (C-6) |
| 비트U차트 / 외부 EMR import | 후속 검토 |
| 대량 import 시 트랜잭션 / 중복 검사 | (정규화 정책 — gender / SSN / phone) | **부재** → 분리 직전 보강 |
| 주석 필요 위험 지점 | `# COMPAT:` (응답 키) / `# NOTE:` (`_dc_*` 정규화 정책) / `# RISK:` (대량 import 트랜잭션) | 표기 필요 |

---

## 4. 리팩토링 전 보강해야 할 테스트

> 사용자 §4 분류표. **분리 직전** 보강이 필수인 테스트와 기존 테스트가 있는 항목, 후속 검토 항목으로 나눈다.
>
> **r2 보정** (Codex r1 G-2 fail 정합): 항목 1 (예약 핵심) 의 "기존 테스트 있음" 표기를 실제 [test_appointment_rules.py](../../tests/test_appointment_rules.py) 상태에 맞춰 "**일부 있음 + 보강 다수 필요**" 로 정밀화. §3-1 표 참조. 항목 2 (휴무 차단) 도 동상.

| # | 항목 | 분류 | 보강 시점 |
|---|---|---|---|
| 1 | 예약 핵심 테스트 (생성/수정/낙관적 락/충돌/점심창) | **기존 일부 있음 + 보강 다수 필요** ([test_appointment_rules.py](../../tests/test_appointment_rules.py) — 필수값/외래키 + 비도수 중복 허용만 정방향. 도수 중복 차단 3건 `xfail`, 취소-후-중복 1건 `skip`, 점심창/PUT/DELETE/409 전용 테스트 부재) | appointments 분리 직전: 백엔드 차단 코드 추가 → `xfail` → 정방향 전환 + PUT/DELETE/409/응답 키 contract 추가 |
| 2 | 휴무 차단 테스트 (오전/오후/종일 백엔드 차단) | **보강 필요** ([test_therapist_leave.py](../../tests/test_therapist_leave.py) full/am/pm 차단 4건 모두 `xfail` — 백엔드 미구현 명시. 반차 허용 시간대만 정방향) | **appointments / leaves 분리 직전 필수** — 백엔드 차단 코드 + `xfail` → 정방향 전환 |
| 3 | 치료항목별 완료체크 테스트 | **기존 테스트 있음** ([test_appointment_rules.py](../../tests/test_appointment_rules.py), [test_stats_counts.py](../../tests/test_stats_counts.py)) | 분리 직전 `manual60=1` 단언 추가 권장 |
| 4 | 통계 집계 테스트 (8 endpoint + 엑셀 export) | **보강 필요** (응답 키 contract — C-7) | stats 분리 직전 필수 |
| 5 | 문자 대상 추출 / 발송 / 템플릿 테스트 | **보강 필요** (응답 키 contract — C-2) | sms 분리 직전 필수 |
| 6 | API contract 테스트 (비-AI 86 endpoint) | **보강 필요** (C-1 — 86 endpoint 중 contract 없는 부분 다수) | 각 모듈 분리 직전 도메인별로 보강 |
| 7 | 프론트 응답 key 테스트 (manual_qa 5키 등) | **기존 테스트 있음** ([test_ai_manual_rag_contract.py](../../tests/test_ai_manual_rag_contract.py), [test_admin_ui_smoke.py](../../tests/test_admin_ui_smoke.py)) | AI 라우터 분리 직전 키 추가 보강 |
| 8 | AI / RAG 하네스 (Chunk/Reindex/Vector/Hybrid/Full/Safety) | **기존 테스트 있음** (§2-2 H-1~H-6) | AI 라우터 분리 직전 회귀 |
| 9 | 운영 DB 보호 테스트 | **기존 테스트 있음** (`tests/conftest.py` 4단계 격리 + [test_db_restore_safety.py](../../tests/test_db_restore_safety.py)) | 매 세션 자동 |
| 10 | PyInstaller 빌드 테스트 (53 hidden imports) | **기존 테스트 있음** ([test_pyinstaller_hidden_imports.py](../../tests/test_pyinstaller_hidden_imports.py)) | 매 모듈 분리 후 spec 갱신과 동시 |
| 11 | 환자 검색 / 메모 / 중복 검사 | **보강 필요** (전용 부재) | patients 분리 직전 필수 |
| 12 | 의사 분기 회귀 (`_doctor_codes_set` / `is_doctor_filter`) | **보강 필요** (전용 부재) | staff (doctor) 분리 직전 필수 |
| 13 | `/api/about/check-update` 응답 키 | **보강 필요** (C-5) | admin 분리 직전 필수 |
| 14 | `data-convert/preview/apply` 응답 키 | **보강 필요** (C-6) | export_import 분리 직전 필수 |
| 15 | `/api/ai/action/{parse,preview,execute}` 응답 키 | **보강 필요** (C-4) | AI 라우터 분리 직전 필수 |
| 16 | 노쇼 / 반복예약 / 치료실 / 자원 | 후속 검토 (현재 부재) | post-19-P |
| 17 | 출력물 / 알림 | 후속 검토 (현재 부재) | post-19-P |
| 18 | export/import 확장 (CSV / EMR import) | 후속 검토 (현재 부재) | post-19-P |
| 19 | 권한 다중 등급 (직원 / 관리자 분리) | 후속 검토 (현재 admin 단일) | post-19-P |
| 20 | AI 의사 정보 임의 생성 차단 (의사 가드) | 후속 검토 (M-36) | post-19-P |

### 4-1. 종합 분류 (r2 보정)

| 분류 | 항목 # | 개수 |
|---|---|---|
| **기존 테스트 있음** (분리 직전 응답 키 contract / 단언만 추가) | 3 / 7 / 8 / 9 / 10 | **5** |
| **기존 일부 있음 + 보강 다수 필요** (`xfail` / `skip` / 부재 다수 — 분리 직전 백엔드 코드 + 정방향 전환) | 1 | **1** |
| **보강 필요** (전용 부재 — 분리 직전 신규 테스트 작성) | 2 / 4 / 5 / 6 / 11 / 12 / 13 / 14 / 15 | **9** |
| **후속 검토** (현재 부재 — post-19-P) | 16 / 17 / 18 / 19 / 20 | **5** |
| 합계 |  | **20** |

> r1 에서 표기한 "9 existing / 7 needed / 4 follow-up" 은 부정확 — Codex r1 G-2 추가 발견 항목 정합. r2 정정: existing 6 (1+5, 단 1번은 일부) / needed 9 / follow-up 5.

---

## 5. 테스트 우선순위

> 사용자 §5 분류 기준. 각 우선순위 그룹 안의 테스트는 **분리 직전에 반드시 통과 / 분리 직후에 회귀 0** 이어야 한다.

### 5-1. 최우선 (분리 직전 필수, 분리 직후 회귀 0 필수)

1. **예약** — `test_appointment_rules.py` + 응답 키 contract 보강.
2. **휴무 차단** — `test_employee_leave_*` + `test_therapist_leave.py` + **`am`/`pm`/`full` 백엔드 차단 보강** (19-P-4 caveat).
3. **완료체크** — `test_appointment_rules.py` + `test_stats_counts.py` + `manual60=1` 단언 추가.
4. **API contract** — manual_qa 5키 + AI status 9키 + health 9/4키 + 비-AI 응답 키 도메인별 보강.
5. **운영 DB 보호** — `scripts/check_db_path.py` + `tests/conftest.py` 4단계 격리 + `tests/harness/db_guard.assert_safe_db_path()`.
6. **AI/RAG local-first 하네스** — Full / RAG / Safety / Chunk / Reindex / Vector / Hybrid + `local_only` / `local_first` / `ai_assist` 모드 분리.

### 5-2. 중요 (분리 직전 보강 권장, 분리 직후 회귀 0)

1. **통계** — 8 endpoint 응답 키 contract (C-7) + 엑셀 export.
2. **문자** — 대상 추출 + 템플릿 + 발송 응답 키 (C-2/C-3) + 외부 HTTP mock.
3. **환자 / 치료사** — CRUD + 검색 + 메모 + alias 이중 키 (C-1).
4. **관리자 설정** — system-settings + `/api/about/check-update` (C-5) + 5회 잠금 + AI 모드.
5. **백업** — 자동/수동 백업 + 복구 + atomic rename.

### 5-3. 후속 (현재 부재 또는 post-19-P)

1. **의사 / 진료진** — `Patient.doctor_id` / `Department` / `Room` / `DoctorSchedule` / `Order` / `Prescription` (M-31~M-35).
2. **반복예약 / recurring_appointments** — 현재 부재.
3. **치료실 / 장비 / 자원** — 현재 부재 (M-33).
4. **알림 (notifications)** — 현재 부재.
5. **출력물 / 인쇄** — 현재 부재.
6. **export / import 확장** (CSV / EMR import) — 현재 부재.
7. **AI 의사 정보 가드** (M-36) — 후속 보강.
8. **권한 다중 등급** — 현재 admin 단일.
9. **`modules/notes/` 통합** — 지속 메모 vs 당일 메모 정책 결정 후 post-19-P.
10. **`/api/health` 신설** — 현재 부재 (M-28).

---

## 6. 테스트 실행 정책

### 6-A. 각 리팩토링 세션 시작 전 (최소 관련 테스트)

| # | 명령 | 목적 |
|---|---|---|
| 1 | `scripts/check_db_path.py` | 운영 DB 경로 안전 검사 (베이스라인 확인) |
| 2 | 해당 모듈 관련 회귀 (예: appointments 분리 시 `test_appointment_rules.py`) | 분리 전 baseline 통과 확인 |
| 3 | 분리 직전 보강 contract 테스트 (§4 / §5-1 항목) | 응답 키 잠금 |
| 4 | (해당 시) 19-P-4 caveat 검증 — `leave_type=am/pm/full` 백엔드 차단 위치 grep + 단언 보강 | 휴무 / 예약 분리 직전 필수 |

### 6-B. 각 리팩토링 세션 종료 후 (관련 테스트 + 핵심 하네스)

| # | 명령 | 목적 |
|---|---|---|
| 1 | `run_check.bat` | pytest + ruff + check_db_path 통합 |
| 2 | 해당 모듈 회귀 + 핵심 AI/RAG 하네스 (§2-2 H-1 ~ H-6) | 회귀 0 확인 |
| 3 | API contract 회귀 (manual_qa / health / 분리 도메인) | 응답 키 후방호환 100% |
| 4 | (해당 시) `tests/test_pyinstaller_hidden_imports.py` 53 tests | spec 갱신과 동시 |

### 6-C. 큰 모듈 이동 후

| # | 명령 | 시점 |
|---|---|---|
| 1 | `venv\Scripts\python.exe -m pytest tests -v` (전체) | 큰 모듈 1개 이동 완료 직후 |
| 2 | 18-8 baseline 비교 (529 passed, 1 skipped, 7 xfailed — 회귀 0) | 동상 |

### 6-D. PyInstaller 검증 시점

| # | 검증 | 시점 |
|---|---|---|
| 1 | `tests/test_pyinstaller_hidden_imports.py` 53 tests | 매 모듈 분리 후 spec 갱신 즉시 |
| 2 | `tests/test_migration_spec_discovery.py` | 새 폴더 / 마이그레이션 추가 시 |
| 3 | 실제 PyInstaller 빌드 (`pyinstaller --noconfirm dosu_clinic.spec`) | **주요 리팩토링 묶음 완료 후** (예: core 분리 + audit + settings 묶음 / 19-P 종료 시점). 매 세션마다 실행 X. |
| 4 | exe smoke (5 엔드포인트) | 19-P 종료 시점 + v1.4.0 배포 직전 |

> **CLAUDE.md "배포 규칙"**: 빌드는 사용자 명시 승인 시에만 수행. 19-P 세션이 자동으로 빌드 트리거하지 않는다. 53 hidden imports 단위 테스트는 빌드 *없이도* 사전 검증 가능하므로 매 세션에서 실행.

### 6-E. 테스트 실패 시 5회 루프 정책

| 회차 | 단계 | 조치 |
|---|---|---|
| 1 | 테스트 + 분석 + 수정 | 가설 1 |
| 2 | 다시 테스트 + 분석 + 수정 | 가설 2 |
| 3 | 동상 | 가설 3 |
| 4 | 동상 | 가설 4 |
| 5 | **마지막** | 통과 → 성공 리포트 / 실패 → 다음 단계로 |
| 5회 실패 후 | **부분 수정 즉시 중단** | `reports/ai_dev_loop/latest_failure_report.md` 작성 + 사용자 결정 (rollback / 재작성). **땜질식 수정 금지**. |

> 5회 루프는 [docs/AI_WORKING_RULES.md §3](../AI_WORKING_RULES.md) 와 [ai_code_session_protocol.md §4](../ai_code_session_protocol.md) 의 14단계 절차에 정합.

---

## 7. 주석 / 문서화 기준 (테스트 / 위험 지점)

> **본 19-P-5 세션은 코드 수정 X — 실제 코드 주석은 작성하지 않는다**.
> 대신 **테스트와 함께 주석이 필요한 위험 지점** 을 본 문서 / 19-P-3 모듈 매핑 / 19-P-4 의존성 맵 에 표시한다.
> 후속 19-P-6+ 세션이 코드를 이동할 때 본 표를 참조해 주석을 추가한다.

### 7-1. 주석 카테고리

| 카테고리 | 의미 | 적용 대상 |
|---|---|---|
| `# COMPAT:` | 기존 응답 키 / URL / 시그니처 후방호환 보존 사유 | wrapper 함수, 호환 alias, response dict 빌더 |
| `# SAFETY:` | PII 마스킹 / 운영 DB 차단 / 외부 API 차단 / API key 비노출 / 개인정보 마스킹 | `pii.scan`, `audit`, `AiUsageLog`, masking 함수 |
| `# NOTE:` | 업무 규칙 / 정책 / 의존성 (제거 시 회귀 발생) | 점심창, 휴무 차단, 반차, 완료체크, 카운트 정책, 통계 집계, 문자 대상 추출 |
| `# RISK:` | 동시성 / TOCTOU / 외부 노드 호환 / 마이그레이션 의존 | 낙관적 락, ENTITY_MAP, indexer lock, restore atomic, HMAC |
| `# TODO(19-x):` | 후속 세션 번호 + 제거 조건 | wrapper 일시 보유 (제거 후 본 라인 삭제), 후속 테스트 보강 |

### 7-2. 반드시 표시해야 하는 주석 지점

#### A. `# COMPAT:` — 기존 API 응답 key 유지 wrapper

| 위치 (현재) | 사유 |
|---|---|
| [app/services/ai/manual_qa.py](../../app/services/ai/manual_qa.py) | wrapper 시그니처 + 공개 상수 보존 (manual_qa wrapper) |
| [app/routers/ai.py:179-184](../../app/routers/ai.py:179) `/api/ai/health/public` | 4키 응답 |
| [app/routers/ai.py:154-164](../../app/routers/ai.py:154) `/api/ai/health` admin | 9키 응답 |
| [app/services/ai/health.py](../../app/services/ai/health.py) `build_admin_status` | 9 top-level 키 응답 |
| [app/services/ai/rag/pipeline.py](../../app/services/ai/rag/pipeline.py) | manual/search 3키 + manual/ask 9키 + sources 3키 |
| [app/routers/api.py:1175-1208](../../app/routers/api.py:1175) therapist alias | `therapist_id` 이중 키 |
| [app/routers/api.py:1158](../../app/routers/api.py:1158) leaves bulk-set alias | `item.therapist_id` → `employee_id` 변환 |
| [app/services/sync.py](../../app/services/sync.py) `ENTITY_MAP` | 외부 노드 호환 9개 도메인 문자열 키 |

#### B. `# SAFETY:` — 운영 DB 보호 / 외부 API 차단 / 개인정보 마스킹

| 위치 (현재) | 사유 |
|---|---|
| [tests/conftest.py:32-75](../../tests/conftest.py:32) 4단계 격리 | 운영 DB 사고 방지 |
| [tests/conftest.py:_block_sdk_modules](../../tests/conftest.py:140) | 외부 LLM 호출 차단 (비용 / PII 사고 방지) |
| [tests/harness/db_guard.py](../../tests/harness/db_guard.py) `assert_safe_db_path` | 운영 DB 경로 차단 (2회) |
| [scripts/check_db_path.py](../../scripts/check_db_path.py) | 머지 게이트 |
| [app/services/ai/pii.py](../../app/services/ai/pii.py) `scan(text)` | PII 마스킹 (cleaned / found / has_blocking) |
| [app/services/ai/health.py](../../app/services/ai/health.py) `_safe_error_detail` | 200자 cap + PII 마스킹 |
| [app/services/ai/ai_logging.py](../../app/services/ai/ai_logging.py) | sha256 해시 only — 원문 미저장 |
| [app/routers/api.py:3115-3160](../../app/routers/api.py:3115) `_normalize_phone_for_sms` / `_mask_phone_for_log` / `_sms_sanitize` | 전화번호 / API key 마스킹 |
| [app/services/auth.py:8](../../app/services/auth.py:8) PBKDF2 + `SESSION_TTL_SEC=28800` + `MAX_FAILURES=5` | 인증 보호 |
| [app/routers/api.py:34-61](../../app/routers/api.py:34) `require_admin` / `require_admin_or_sync_token` | 권한 보호 |
| `AiUsageLog` `prompt_hash` / `response_hash` | 원문 부재 (sha256 only) |
| 모든 응답에 `api_key` 평문 / 마스킹 부재 (boolean 만) | API key 비노출 |
| AI/RAG → 도메인 DB 임의 생성 ⊥ (의존성 D-6) | RAG 가 환자/예약 데이터 임의 생성 금지 |

#### C. `# NOTE:` 또는 `# RISK:` — 업무 규칙 / 정책 / 동시성

| 위치 (현재) | 카테고리 | 사유 |
|---|---|---|
| [app/routers/api.py:64-107](../../app/routers/api.py:64) 점심창 헬퍼 | `# NOTE:` | 점심창 차단 정책 (예약 가능 시간) |
| [app/routers/api.py:1664-1679](../../app/routers/api.py:1664) `_check_version` / `_bump_version` | `# RISK:` | 낙관적 락 TOCTOU |
| [app/routers/api.py:1934-1953](../../app/routers/api.py:1934) `_bump_patient_count` | `# NOTE:` | 환자 카운트 0 미만 방지 + Lazy 생성 |
| [app/models/constants.py:20](../../app/models/constants.py:20) `manual60` `count_increment=1` | `# NOTE:` | CLAUDE.md 명시 — 절대 2로 되돌리지 않음 |
| (`leave_type="am"` / `"pm"` / `"full"` 백엔드 차단 위치) | `# NOTE:` + `# RISK:` | 19-P-4 caveat — 분리 직전 grep 후 위치 확정 + 주석 |
| [app/routers/api.py:1098](../../app/routers/api.py:1098) `_upsert_employee_leave_core` | `# NOTE:` | 휴무 단일 진실원천 (AI action_leave 도 같이 호출) |
| [app/routers/api.py:3732-3757](../../app/routers/api.py:3732) `_get_manual_treatment_rows` / `_get_manual_therapy_codes` | `# NOTE:` | 통계 / 예약 / 엑셀 export 다중 의존 |
| [app/services/ai/rag/pipeline.py](../../app/services/ai/rag/pipeline.py) `LOW_SCORE_THRESHOLD=2` | `# NOTE:` | 임계치 — 변경은 별도 결정 + eval 후 |
| [app/services/ai/rag/confidence.py](../../app/services/ai/rag/confidence.py) `HIGH=0.7` / `LOW=0.3` / `LLM_CALL=0.3` | `# NOTE:` | 동상 |
| [app/services/ai/vector/embeddings.py](../../app/services/ai/vector/embeddings.py) `QUERY_MIN_CHARS=2` | `# NOTE:` | 동상 |
| [app/services/ai/knowledge/indexer.py](../../app/services/ai/knowledge/indexer.py) reindex lock | `# RISK:` | 동시성 |
| [app/routers/api.py:2168-2256](../../app/routers/api.py:2168) `/api/restore` atomic rename + integrity_check | `# RISK:` | DB 엔진 lifecycle |
| [app/services/sync.py:21](../../app/services/sync.py:21) `ENTITY_MAP` | `# RISK:` | 외부 노드 호환 — 분리 시 문자열 키 보존 |
| [app/services/ai/action_leave.py](../../app/services/ai/action_leave.py) HMAC 토큰 + TOCTOU | `# RISK:` | parse / preview / execute 흐름 |
| [dosu_clinic.spec](../../dosu_clinic.spec) hidden imports + collect_submodules + migrations 글롭 | `# RISK:` | 분리 시 누락 위험 |
| [app/services/backup.py](../../app/services/backup.py) `start_auto_backup` daemon thread | `# RISK:` | 백그라운드 스레드 — 테스트는 람다 교체 |
| [pyproject.toml](../../pyproject.toml) `app/**` per-file-ignores | `# NOTE:` | CLAUDE.md 명시 — 풀면 대량 포맷 변경 |

#### D. `# NOTE:` — 테스트 fixture / mock provider

| 위치 (현재) | 사유 |
|---|---|
| [tests/conftest.py:112](../../tests/conftest.py:112) `class FakeProvider` | `len(provider.calls)` 컨벤션 — `call_count` 속성 부재 |
| [tests/harness/fake_provider.py](../../tests/harness/fake_provider.py) | conftest 외 추가 stub |
| [tests/harness/seed_data.py](../../tests/harness/seed_data.py) | 세션 스코프 시드 (직원/환자/휴무) |
| [tests/harness/db_guard.py](../../tests/harness/db_guard.py) `assert_safe_db_path` | 2회 호출 (import-time + session fixture) |
| [tests/harness/contract.py](../../tests/harness/contract.py) | 응답 키 계약 단언 (manual/search/ask) |

#### E. `# TODO(19-x):` — 후속 테스트 보강 필요

| 항목 | 후속 세션 후보 |
|---|---|
| 비-AI 86 endpoint contract (C-1) | 각 모듈 분리 직전 (19-P-6+) |
| `/api/sms/send` 응답 키 (C-2) | sms 분리 직전 |
| `/api/sms/draft` 응답 키 (C-3) | AI 라우터 분리 직전 |
| `/api/ai/action/{parse,preview,execute}` 응답 키 (C-4) | AI 라우터 분리 직전 |
| `/api/about/check-update` 응답 키 (C-5) | admin 분리 직전 |
| `data-convert/preview/apply` 응답 키 (C-6) | export_import 분리 직전 |
| 8 stats endpoint 응답 키 (C-7) | stats 분리 직전 |
| `leave_type=am/pm/full` 백엔드 차단 단언 | appointments / leaves 분리 직전 (19-P-4 caveat) |
| 의사 분기 회귀 (`_doctor_codes_set` / `is_doctor_filter`) | staff (doctor) 분리 직전 |
| AI 의사 정보 임의 생성 차단 (M-36) | post-19-P |
| `manual60` `count_increment=1` 직접 단언 | treatments 분리 직전 |

### 7-3. 주의

- 모든 줄 주석을 요구하지 않는다.
- **역할 / 경계 / 주의사항 중심** 주석 기준을 유지한다.
- 주석 작성 때문에 **기능 동작을 바꾸지 않는다**.
- 본 19-P-5 세션은 코드 수정이 없으므로 실제 코드 주석은 추가하지 않으며, 본 표는 후속 19-P-6+ 단계의 가이드.

---

## 8. Codex 검증 결과 기록 위치

본 19-P-5 산출물의 Codex 검증 결과는 다음 위치에 기록된다:

- [reports/refactor/19-P-5_codex_review.md](../../reports/refactor/19-P-5_codex_review.md) (영구 보존본)
- [reports/refactor/latest_codex_review.md](../../reports/refactor/latest_codex_review.md) (덮어쓰기 — 다음 세션 진입점)

### 사용자가 Codex 에게 전달할 최소 문구

> "reports/refactor/latest_codex_review_request.md 문서 확인하고 검증 시작해줘. Claude Code 요약만 믿지 말고 실제 파일 구조와 문서 내용을 직접 비교해서 검증해줘. 검증 결과는 reports/refactor/latest_codex_review.md와 세션별 review 문서로 남겨줘."

---

## 9. 종합

- **테스트 전략 원칙 T-1 ~ T-15** = 리팩토링은 구조 변경, 기능 변경 X. 응답 키 / URL / DB schema 보존. 한 세션 = 한 모듈. 5회 루프 정책. Codex 게이트.
- **공통 테스트** = run_check.bat + pytest + ruff + check_db_path + 18 시리즈 하네스 6개 + AI 회귀 7개 + API contract + 운영 DB 보호 5단계.
- **모듈별 전략** = appointments / patients / staff / doctors(부분) / leaves / treatments / stats / sms / admin / backup / ai / rag / calendar / notes / health / audit / export_import 17 영역. 의사 / 진료실 / 담당의 / EMR 등 부재 항목은 후속 검토 분류 (실제 구현된 것처럼 단정 X).
- **보강 필요 테스트** (r2 정정) = §4 의 20개 항목 중:
  - **5 existing** (3 완료체크 / 7 manual_qa 키 / 8 AI/RAG 하네스 / 9 운영 DB / 10 PyInstaller)
  - **1 일부 있음 + 보강 다수 필요** (1 예약 핵심 — `xfail`/`skip`/부재 다수)
  - **9 needed** (2 휴무 차단 — `xfail` 4건 / 4 통계 / 5 문자 / 6 비-AI contract / 11 환자 / 12 의사 분기 / 13 about/check-update / 14 data-convert / 15 ai/action)
  - **5 follow-up** (16 노쇼 등 / 17 출력물·알림 / 18 export 확장 / 19 권한 등급 / 20 AI 의사 가드)
- **테스트 우선순위** = 최우선 6개 (예약 / 휴무 / 완료체크 / API contract / 운영 DB / AI local-first) + 중요 5개 (통계 / 문자 / 환자/치료사 / 관리자 / 백업) + 후속 10개 (의사 / 반복예약 / 자원 / 알림 / 출력물 / export 확장 / AI 가드 / 권한 등급 / notes 통합 / health 신설).
- **PyInstaller 검증 시점** = 53 hidden imports 단위 테스트는 매 모듈 분리 직후 / 실제 빌드는 주요 묶음 완료 후 또는 19-P 종료 시점 + v1.4.0 배포 직전 (사용자 명시 승인 시).
- **주석 지점** = COMPAT 8 / SAFETY 12 / NOTE+RISK 14 / 테스트 fixture 5 / TODO 11 — 본 세션은 코드 미수정, 후속 19-P-6+ 가이드.
- **r2 보정 핵심** = §3-1 appointments 표 + §3-5 leaves 표 + §4 종합 분류 + §2-5 db_guard 표현 모두 실제 테스트 파일 (`xfail` / `skip` / 부재) 상태에 맞게 정정. Codex r1 G-2 fail 지적 정합.
- **다음 단계** = Codex r2 재검증 후 → 19-P-6 롤아웃 계획 문서 (`docs/refactor/19_refactor_rollout_plan.md`) — 모듈별 분리 순서 + 세션별 작업 패키지 + Codex 게이트 일정.
