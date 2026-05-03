# 19-0 단위화 리팩토링 — 기준 테스트 결과 (19_refactor_baseline_test_result)

> 19-P-1 ~ 19-P-10 (준비 단계 10개 문서) 완료 후 **19-x 실제 코드 리팩토링 세션 진입 직전 baseline 확보** 세션의 결과 요약.
> 본 19-0 = read-only 검증 세션 (코드 / 테스트 / migration / spec / UI / requirements 무수정).
>
> **검증 결과: 18-8 baseline 정확 일치 (529 passed, 1 skipped, 7 xfailed) — 회귀 0**.

## 0. 메타

- 세션 이름: **19-0 단위화 리팩토링 전 기준 테스트/하네스 재확인**
- 검증일: 2026-05-03
- 기준 브랜치: `ai-rag-v1-integration`
- 기준 커밋 (HEAD): `bcd74a7aabc9de8d735425863254cfc393bda580` (release v1.3.3)
- 18-8 baseline: **529 passed, 1 skipped, 7 xfailed** ([reports/ai_dev_loop/18-8_test_report.md](../../reports/ai_dev_loop/18-8_test_report.md))
- 19-P-1 r2 / 19-P-2 r3 / 19-P-3 r1 / 19-P-4 r2 / 19-P-5 r3 / 19-P-6 r1+r2 / 19-P-7 r3 / 19-P-8 r1 / 19-P-9 r1 / 19-P-10 r1+r2+r3+r4+r5 Codex 판정: **모두 pass / pass with caveat (yes 19-1 진입 가능)**.
- 본 세션 정책: **읽기 전용** — 코드 / 테스트 / 마이그레이션 / spec / UI / requirements 1바이트도 수정 금지.

---

## 1. 실행한 테스트 명령

| # | 명령 | 의미 |
|---|---|---|
| C-1 | `venv/Scripts/python.exe -m pytest tests -v --tb=short` | 전체 회귀 테스트 (verbose) |
| C-2 | `venv/Scripts/python.exe -m ruff check app tests scripts` | lint 검사 (per-file-ignores 보존) |
| C-3 | `venv/Scripts/python.exe scripts/check_db_path.py` | 운영 DB 경로 안전 검사 |
| C-4 | `venv/Scripts/python.exe -m pytest tests/test_pyinstaller_hidden_imports.py -q` | PyInstaller 53 hidden imports 검증 |
| C-5 | (카테고리별) `pytest tests/test_<category>*.py --tb=no -q` | 도메인별 분리 카운트 |

---

## 2. 테스트 결과 요약

### 2-1. 종합 (C-1 결과)

| 결과 | 카운트 |
|---|---|
| **passed** | **529** ✓ |
| **skipped** | **1** ✓ |
| **xfailed** | **7** ✓ |
| failed | 0 |
| errors | 0 |
| warnings | 27 (PytestReturnNotNoneWarning — `test_ai_sms_validate.py` / `test_ai_sms_draft.py` tuple return 패턴, 기존 알려진 warning) |
| 실행 시간 | 11.74초 |

> **18-8 baseline 100% 일치 — 회귀 0**.

### 2-2. lint / 운영 DB / PyInstaller (C-2 ~ C-4)

| 명령 | 결과 |
|---|---|
| `ruff check app tests scripts` | **All checks passed!** (exit 0) |
| `scripts/check_db_path.py` | **exit 0** (운영 DB 경로 감지 메시지 = 직접 실행 시 정상, 테스트 중 ⊥) |
| PyInstaller 53 hidden imports tests | **53 passed** (0.39초) |

---

## 3. 통과한 테스트 (카테고리별)

| 카테고리 | 파일 | 결과 |
|---|---|---|
| **AI/RAG 핵심** | | |
| RAG | test_ai_manual_rag_contract.py + test_ai_manual_rag_harness.py + test_rag_pipeline.py + test_ai_full_harness.py + test_full_harness.py | **49 passed** |
| Safety | test_rag_safety.py + test_ai_safety_harness.py + test_ai_hallucination.py + test_ai_sms_draft_hallucination.py + test_db_restore_safety.py | **36 passed** |
| Chunker | test_ai_chunker_harness.py | **35 passed** |
| Reindex | test_ai_reindex_harness.py | **24 passed** |
| Vector | test_ai_vector_harness.py | **36 passed** |
| Hybrid | test_hybrid_retriever.py | **46 passed** |
| Health/Admin | test_ai_health_status.py + test_ai_health_public.py + test_admin_ui_smoke.py + test_admin_auth_required.py | **82 passed** |
| ManualQA/Contract | test_ai_manual_qa.py + test_ai_contract_manual.py | **19 passed** |
| AI-Mode (local-first) | test_ai_assist_mode.py + test_local_only_mode.py | **19 passed** |
| **기존 기능 회귀** | | |
| Appointment (예약) | test_appointment_rules.py | **6 passed, 1 skipped, 3 xfailed** |
| Leaves (휴무) | test_therapist_leave.py + test_employee_leave_kind.py + test_employee_leave_unique.py | **10 passed, 4 xfailed** |
| SMS validation | test_sms_secret_masking.py | **6 passed** |
| Stats (통계) | test_stats_counts.py | **6 passed** |
| Employee (직원) | test_employee_can_manual_contract.py + test_employee_hire_date.py | **4 passed** |
| **기존 AI 회귀** | | |
| AI-SMS | test_ai_sms_draft.py + test_ai_sms_draft_hallucination.py + test_ai_sms_validate.py | **27 passed** (warnings 21) |
| AI-ActionLeave (휴무 AI) | test_ai_action_leave.py | **44 passed** |
| AI-Logging | test_ai_logging.py | **6 passed** |
| **PyInstaller / 마이그레이션** | | |
| PyInstaller hidden imports | test_pyinstaller_hidden_imports.py | **53 passed** |
| Migration spec discovery | test_migration_spec_discovery.py | (PyInstaller 묶음 57 passed 안에 포함) |

---

## 4. 실패한 테스트

**failed = 0 / errors = 0**.

### 4-1. xfail 분류 (7건 — 백엔드 차단 미구현 명시 + 19-4 / 19-5 분리 직전 정방향 전환 예정)

| 파일 | 테스트 | xfail 이유 | 정방향 전환 시점 |
|---|---|---|---|
| test_appointment_rules.py | test_two_manual30_same_slot_blocked | 도수 중복 차단 백엔드 미구현 | 19-4 availability |
| test_appointment_rules.py | test_two_manual60_same_slot_blocked | 도수 중복 차단 백엔드 미구현 | 19-4 availability |
| test_appointment_rules.py | test_eswt_then_manual30_same_slot_blocked | 도수 중복 차단 백엔드 미구현 | 19-4 availability |
| test_therapist_leave.py | test_full_day_leave_blocks_morning | 휴무 차단 백엔드 미구현 (full 종일) | 19-4 / 19-5 |
| test_therapist_leave.py | test_full_day_leave_blocks_afternoon | 휴무 차단 백엔드 미구현 (full 종일) | 19-4 / 19-5 |
| test_therapist_leave.py | test_morning_leave_blocks_before_noon | 휴무 차단 백엔드 미구현 (am 오전반차) | 19-4 / 19-5 |
| test_therapist_leave.py | test_afternoon_leave_blocks_after_noon | 휴무 차단 백엔드 미구현 (pm 오후반차) | 19-4 / 19-5 |

### 4-2. skip 분류 (1건)

| 파일 | 테스트 | skip 이유 | 활성화 시점 |
|---|---|---|---|
| test_appointment_rules.py | test_canceled_manual_excluded_from_duplicate_check | "차단 코드 추가 후 활성화" 명시 | 19-4 availability |

---

## 5. 실패 원인 추정

본 19-0 시점 **failed = 0** — 실패 없음. xfail 7건 + skip 1건은 19-P-7 §2-A R-APPT-02 / R-APPT-03 / R-APPT-04 위험 등록에 명시된 *백엔드 차단 미구현* 항목으로, 19-4 (availability 분리) / 19-5 (leaves 분리) 시점에 백엔드 차단 코드 추가 후 정방향 전환 예정.

### 5-1. 27 warnings 원인 (PytestReturnNotNoneWarning)

`test_ai_sms_validate.py` 11 warnings + `test_ai_sms_draft.py` 8 warnings + 기타 = 27. 모두 테스트 함수가 `assert` 대신 `return tuple(...)` 패턴을 사용하는 *기존 알려진 warning* — 동작에는 영향 없음. 본 19-0 시점에 회귀 0.

---

## 6. 리팩토링 전 반드시 해결해야 할 문제

| # | 문제 | 해결 시점 |
|---|---|---|
| (해당 없음) | failed / errors 0 — 본 19-0 시점에 즉시 해결할 *필수* 문제 0건 | — |

> **기준 baseline 확보 완료**. 19-1 진입 가능.

### 6-1. 19-x 분리 직전 보강 필수 9개 항목 (19-P-5 §4-1 정합)

| # | 보강 항목 | 보강 시점 |
|---|---|---|
| 1 | 비-AI 86 endpoint contract 테스트 (C-1, 19-P-1 §22) | 각 19-x 분리 직전 (도메인별) |
| 2 | 예약 점심창 차단 contract | 19-4 / 19-9 |
| 3 | 예약 PUT / DELETE / 409 contract | 19-9 |
| 4 | xfail 3건 + skip 1건 → 정방향 전환 (도수 중복) | 19-4 |
| 5 | xfail 4건 → 정방향 전환 (휴무 차단) | 19-4 / 19-5 |
| 6 | approve / revert / done_count 0 미만 contract | 19-6 |
| 7 | 8 endpoint stats 응답 키 contract | 19-11 |
| 8 | tomorrow-targets contract + 외부 HTTP mock | 19-10 |
| 9 | 환자 검색 / 메모 / counts dict contract | 19-7 |

---

## 7. 리팩토링 중 계속 유지해야 할 기준

> 모든 19-x 코드 세션이 매 세션 본 기준을 검증.

### 7-1. 절대 원칙 (DEC-A ~ DEC-T 정합)

| 기준 | 본 19-0 결과 |
|---|---|
| 18-8 baseline (529 passed, 1 skipped, 7 xfailed) 회귀 0 | ✓ 정확 일치 |
| API URL 보존 | ✓ 변경 0 |
| 응답 dict 키 보존 (33+ 키 셋) | ✓ 변경 0 |
| DB schema 보존 (m001~m013 diff 0) | ✓ 변경 0 |
| 운영 DB 미접근 | ✓ S-1 ~ S-5 자동 통과 |
| 외부 API 호출 0 | ✓ `_block_sdk_modules` 활성 |
| `local_only` 모드 LLM/Embedding 호출 0 | ✓ AI-Mode 19 passed |
| sources 없음 / low_confidence / PII / unknown_feature provider 호출 0 | ✓ AI-Mode + Safety 통과 |
| manual60 = 1 카운트 정책 | ✓ Stats / Employee 통과 |
| per-file-ignores 보존 | ✓ ruff All checks passed |
| PyInstaller 53 hidden imports | ✓ 53 passed |
| 부재 항목 단정 ⊥ | ✓ Doctor / doctor_id / no_show / `/api/health` grep 0 |

---

## 8. 운영 DB 보호 결과

| # | 검사 | 결과 |
|---|---|---|
| S-1 | `scripts/check_db_path.py` exit 0 | ✓ pass (운영 DB 경로 감지 = 직접 실행 시 정상, 테스트 중 ⊥) |
| S-2 | `tests/conftest.py` 4단계 격리 (APPDATA + DOSU_DB_PATH + 워커 no-op + SDK block) | ✓ pass (529 passed 자동 검증) |
| S-3 | `tests/harness/db_guard.py` `assert_safe_db_path()` (import-time 1회 + session-scope fixture 1회) | ✓ pass |
| S-4 | `_block_sdk_modules` (openai / anthropic SDK 차단) | ✓ pass (import-time 자동) |
| S-5 | `test_*_does_not_use_operational_db` 다수 | ✓ pass (529 passed 자동 검증) |

> **결과: 운영 DB `%APPDATA%\도수치료예약\clinic.db` 미접근 100% 정합**.

---

## 9. 외부 API 호출 차단 결과

| # | 검사 | 결과 |
|---|---|---|
| `_block_sdk_modules` 활성 | ✓ pass — openai / anthropic SDK 클래스 RuntimeError 로 교체 |
| FakeProvider / FakeEmbeddingProvider 만 사용 | ✓ pass — `tests/harness/fake_provider.py` 정의 |
| `local_only` 모드 `len(provider.calls) == 0` 단언 | ✓ pass — test_local_only_mode.py 19 passed (AI-Mode) |
| `local_only` 모드 `len(embedding_provider.calls) == 0` 단언 | ✓ pass — Vector 36 passed |
| 실제 OpenAI / Anthropic / 문자나라 API 호출 | ✓ 0 (전체 테스트 통과 시 외부 호출 부재) |
| API key 원문 응답 / 로그 / audit 부재 | ✓ pass — Safety 36 passed (sha256 해시 / 마스킹) |

> **결과: 외부 API 호출 0건 100% 정합**.

---

## 10. AI/RAG 하네스 결과

| 하네스 | 파일 | 결과 |
|---|---|---|
| RAG (18-1) | test_ai_manual_rag_contract.py + test_ai_manual_rag_harness.py + test_rag_pipeline.py + test_ai_full_harness.py + test_full_harness.py | **49 passed** ✓ |
| Safety (18-1, PII / 할루시네이션 가드) | test_rag_safety.py + test_ai_safety_harness.py + test_ai_hallucination.py + test_ai_sms_draft_hallucination.py + test_db_restore_safety.py | **36 passed** ✓ |
| Chunker (18-3) | test_ai_chunker_harness.py | **35 passed** ✓ |
| Reindex (18-4) | test_ai_reindex_harness.py | **24 passed** ✓ |
| Vector (18-5) | test_ai_vector_harness.py | **36 passed** ✓ |
| Hybrid (18-6) | test_hybrid_retriever.py | **46 passed** ✓ |
| 관리자 상태 (18-7) | test_ai_health_status.py + test_ai_health_public.py + test_admin_ui_smoke.py | **76 passed** (Health/Admin 82 passed 중 admin_auth 6 제외) ✓ |
| API contract | test_ai_manual_rag_contract.py + test_ai_contract_manual.py + test_ai_manual_qa.py | **포함됨 (RAG 49 + ManualQA 19)** ✓ |

### 10-1. 핵심 응답 키 보존 검증

| 응답 | 키 셋 | 보존 |
|---|---|---|
| `/api/ai/manual/search` (3 키) | `sources / masked_question / top_score` | ✓ pass (RAG / ManualQA 통과) |
| `/api/ai/manual/ask` (9 키) | `answer / sources / confidence / not_found / blocked / blocked_reason / guard_hits / top_score / masked_question` | ✓ pass (ManualQA 19 passed) |
| `sources[]` (3 키) | `title / path / snippet` | ✓ pass |
| `/api/ai/health` (admin 9 키) | `enabled / provider / model / api_key_set / sdk_installed / sdk_errors / knowledge_doc_count / ready / version` | ✓ pass (Health 82) |
| `/api/ai/health/public` (4 키) | (인증 불필요) | ✓ pass |
| `/api/ai/status` (18-7 admin 9 top-level) | (18-7 정합) | ✓ pass |

> **결과: 33+ 응답 키 셋 100% 보존**.

---

## 11. 기존 기능 회귀 결과

| 영역 | 결과 |
|---|---|
| **예약 (Appointment)** | 6 passed, 1 skipped, 3 xfailed (xfail/skip 4건 = 19-4 정방향 전환 예정) |
| **휴무 (Leaves)** | 10 passed, 4 xfailed (xfail 4건 = 19-4/19-5 정방향 전환 예정) |
| **문자/SMS** | SMS validation 6 passed + AI-SMS 27 passed (warnings 21) |
| **통계** | 6 passed |
| **환자/치료사 (Employee)** | 4 passed (can_manual_contract + hire_date) |
| **관리자/백업** | Admin auth 6 passed (Health/Admin 82 안에 포함) |
| **기존 SMS AI** | 27 passed (3 파일) |
| **기존 휴무 AI** | 44 passed |

> **결과: 기존 기능 회귀 0**.

---

## 12. 19-1 로 넘어가도 되는지 판단

### 12-1. 진입 게이트 (BG-1 ~ BG-10)

| # | 게이트 | 본 19-0 결과 |
|---|---|---|
| BG-1 | 코드 무수정 (read-only) | ✓ pass — 본 19-0 추가 코드 변경 0 |
| BG-2 | 18-8 baseline 회귀 0 | ✓ pass — 529 / 1 / 7 정확 일치 |
| BG-3 | ruff lint 통과 | ✓ pass — All checks passed |
| BG-4 | 운영 DB 보호 (S-1 ~ S-5) | ✓ pass |
| BG-5 | 외부 API 차단 (`_block_sdk_modules` + FakeProvider) | ✓ pass |
| BG-6 | PyInstaller 53 tests | ✓ pass — 53 passed |
| BG-7 | baseline 측정값 drift 0 (api.py 5127 / endpoint 86 / ORM 19 등) | ✓ pass |
| BG-8 | 부재 항목 단정 ⊥ (Doctor / doctor_id / no_show / `/api/health` grep 0) | ✓ pass |
| BG-9 | AI/RAG 하네스 6+ (Full / RAG / Safety / Chunker / Reindex / Vector / Hybrid / Health) | ✓ pass — 모두 통과 |
| BG-10 | 사용자 결정 1건 (dirty worktree 처리) | **사용자 결정 필요 (19-1 진입 직전)** |

### 12-2. 19-1 진입 권고

**yes — 19-1 core 공통 유틸 정리 진입 가능** (사용자 dirty worktree 처리 결정 답변 후).

근거:
1. 18-8 baseline (529 / 1 / 7) 100% 정확 일치 — 회귀 0.
2. ruff / check_db_path / PyInstaller 53 tests 모두 통과.
3. 9 AI/RAG 하네스 카테고리 모두 통과.
4. 8 기존 기능 회귀 카테고리 모두 통과.
5. 운영 DB 미접근 + 외부 API 호출 0 + API key 원문 / PII 비노출 모두 정합.
6. 본 19-0 코드 / 테스트 / spec / UI / migrations / requirements 변경 0 (read-only 정책 100% 준수).
7. 부재 항목 단정 ⊥ (doctors / EMR / no_show 등) 100% 정합.

남은 위험 / 사용자 결정 필요:
- 18-0 ~ 18-8 dirty/untracked 변경분 (6 modified + 50 untracked) 처리 결정 (머지 / commit / 유지) — 19-1 진입 직전.
- xfail 7건 + skip 1건 (도수 중복 차단 + 휴무 차단) 정방향 전환 — 19-4 / 19-5 시점.
- 비-AI 86 endpoint contract 보강 — 각 19-x 분리 직전.

다음 세션:
- **19-1 core 공통 유틸 정리** — `app/core/` 신설 (config / database / errors / responses / time_utils / security / feature_flags) — [docs/refactor/19_refactor_rollout_plan.md §3-1](19_refactor_rollout_plan.md).
