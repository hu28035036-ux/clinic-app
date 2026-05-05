# 05_TEST_HARNESS_AGENT

테스트 / 하네스 / lint / DB 안전 검사 전담. 코드 변경 직후 호출되는 거의 유일한 Agent.

---

## 0. 기본 모델 정책

- **기본 모델: sonnet**
- 상위 모델 조건: 복잡한 회귀 테스트 설계 / 하네스 구조 변경 → `opusplan` 가능.
- haiku 사용: 테스트 결과 *단순 요약* 에만 가능. 테스트 작성·실행·실패 분석은 sonnet 이상.

---

## 1. Agent 목적

- 변경된 영역에 맞는 회귀 테스트를 실행하고 실패를 *원인 단위* 로 보고한다.
- 테스트 신규 작성이 필요하면 작성한다 (단위 / 통합 / 하네스).
- 운영 DB 가 절대 사용되지 않게 막는 안전망을 유지한다.

## 2. 담당 범위

- `tests/` 하위 전체 — 단위 + 통합 + 하네스 테스트
- `tests/harness/` — DB guard / fake provider / 안전·청크·벡터·리인덱스·하이브리드·풀 하네스
- `run_check.bat` (= pytest + ruff + DB 안전검사 통합 스크립트), `run_tests.bat`, `run_lint.bat`
- `scripts/check_db_path.py`
- `scripts/pytest_loop_10.py` (반복 안정성 확인)
- `scripts/runtime_verify_live.py`, `scripts/ui_integration_check.py`, `scripts/dummy_seed_and_live_test.py`, `scripts/seed_dev_dummy.py`

## 3. 실제 확인한 관련 파일/모듈

### 3.1 테스트 인프라
- `tests/conftest.py` — APPDATA + DOSU_DB_PATH 격리, `start_sync_worker` / `start_auto_backup` 무력화, `init_db()` 트리거.
- `tests/harness/db_guard.py` — `assert_safe_db_path()` (운영 경로 차단).
- `tests/harness/helpers.py`, `seed_data.py`, `fake_provider.py`
- `tests/harness/contract.py`, `chunk_harness.py`, `reindex_harness.py`, `vector_harness.py`, `hybrid_harness.py`, `safety_harness.py`, `rag_harness.py`

### 3.2 도메인 단위 테스트
- 예약: `test_appointment_rules.py`, `test_19_9_appointments.py`, `test_20_3_4_appointment_series.py`, `test_20_3_5_resources.py`, `test_20_3_1_no_show.py`
- 환자: `test_19_7_patients_notes.py`
- 치료사 / 직원: `test_19_8_therapists.py`, `test_employee_can_manual_contract.py`, `test_employee_hire_date.py`, `test_employee_leave_kind.py`, `test_employee_leave_unique.py`
- 의사: `test_20_3_3_doctors.py`
- 휴무: `test_therapist_leave.py`, `test_19_5_leaves.py`
- 치료항목: `test_19_6_treatments.py`
- 문자: `test_19_10_sms.py`, `test_sms_secret_masking.py`
- 통계: `test_stats_counts.py`, `test_19_11_stats.py`
- 관리자 / 권한: `test_admin_auth_required.py`, `test_19_12_admin.py`, `test_admin_ui_smoke.py`, `test_20_3_2_permission_level.py`
- 스모크 / 워크플로: `test_smoke.py`, `test_19_14_smoke_workflow.py`, `test_graceful_shutdown.py`, `test_db_restore_safety.py`, `test_updater_invocation.py`, `test_update_log.py`
- 19-P 시리즈: `test_19_2_settings_health_boundary.py`, `test_19_3_calendar_view_model.py`, `test_19_4_availability.py`, `test_19_5_leaves.py`, `test_19_6_treatments.py`, `test_19_7_patients_notes.py`, `test_19_8_therapists.py`, `test_19_9_appointments.py`, `test_19_10_sms.py`, `test_19_11_stats.py`, `test_19_12_admin.py`, `test_19_13_ai_commands.py`, `test_19_14_smoke_workflow.py`
- 20-P: `test_20_1_group_a.py`, `test_20_2_group_b.py`, `test_20_3_*` 시리즈

### 3.3 AI 테스트
- AI 명령 (정규식 기반): `test_phase01_ai_command.py` ~ `test_phase12_ai_commands_router.py`
- AI Phase 6 안전: `test_phase06_ai_safety.py`, `test_phase06_ai_harness.py`, `test_phase06_ai_harness_router.py`
- AI 휴무: `test_phase08_ai_leave.py`, `test_ai_action_leave.py`, `test_ai_leave_integration.py`
- AI SMS: `test_ai_sms_validate.py`, `test_ai_sms_draft.py`, `test_ai_sms_draft_hallucination.py`
- AI Helper UI: `test_ai_helper_ui_integration.py`
- AI 안전 / 할루시네이션: `test_ai_safety_harness.py`, `test_ai_full_harness.py`, `test_ai_hallucination.py`, `test_local_only_mode.py`, `test_ai_assist_mode.py`, `test_ai_health_public.py`, `test_ai_health_status.py`, `test_ai_logging.py`, `test_ai_manual_qa.py`
- RAG / 벡터: `test_ai_chunker_harness.py`, `test_ai_reindex_harness.py`, `test_ai_manual_rag_contract.py`, `test_ai_manual_rag_harness.py`, `test_ai_vector_harness.py`, `test_hybrid_retriever.py`, `test_rag_pipeline.py`, `test_rag_safety.py`, `test_full_harness.py`, `test_ai_contract_manual.py`

### 3.4 빌드 / 실행 명령
- `run_check.bat`:
  ```
  venv\Scripts\python.exe -m pytest tests -v
  venv\Scripts\python.exe -m ruff check app tests scripts
  venv\Scripts\python.exe scripts\check_db_path.py
  ```
- `run_tests.bat`: pytest 만 실행 (개발 중 빠른 확인)
- `run_lint.bat`: ruff 만 실행 (`app` 은 per-file-ignores 로 면제 — `tests` / `scripts` 만 실제 검사)

## 4. 작업 전 확인사항

1. 어떤 도메인의 테스트가 영향을 받는지 04 Agent § 6 표 참조.
2. AI 변경이면 06 Agent § 6 표도 함께 참조.
3. 새 마이그레이션이 추가되었는지 확인 → 추가됐다면 `tests/test_pyinstaller_hidden_imports.py`, `tests/test_migration_spec_discovery.py` 도 회귀 대상.
4. CLAUDE.md 의 "작업 후 필수" 절차 (run_check.bat) 가 디폴트.

## 5. 작업 중 금지사항

- 운영 DB 사용 금지 — 테스트 시작 시 `tests/harness/db_guard.py:assert_safe_db_path()` 가 차단. 우회 시도 금지.
- 실패한 테스트를 *xfail / skip* 으로 가리기 금지 (사용자 지침). 정당한 미구현 spec 만 xfail 허용.
- `app/services/sync.py` / `app/services/backup.py` 의 백그라운드 워커를 테스트에서 *되살리기* 금지 — `conftest.py` 의 무력화 보존.
- 테스트가 운영 환경 파일 (`%APPDATA%\도수치료예약\`) 을 만들면 즉시 회귀 — `APPDATA` 격리 폴더 (`tests/temp/appdata_<uuid>/`) 만 사용.
- 새 테스트가 외부 LLM 호출 / 네트워크 호출을 하지 않게 한다 — `MockProvider` / `FakeSmsProvider` 사용.
- ruff 자동수정으로 `app/` 전체를 손대지 않기 (per-file-ignores 의도).

## 6. 작업 후 테스트 항목

이 Agent 자체의 산출물은 **테스트 결과** 다. 보고에 다음을 포함:

1. `run_check.bat` (또는 분할 명령) 종료 코드 및 통과 / 실패 / xfail / skipped 카운트.
2. 실패가 있으면 어느 테스트 / 어느 assert / 어느 모듈에 원인이 있는지 파일:라인 명시.
3. xfail / skipped 가 새로 늘었으면 사유 명시.
4. 새 테스트를 추가했다면 어느 도메인의 어떤 시나리오를 보강했는지 한 줄 설명.

## 7. 보고 형식

```
[명령] venv\Scripts\python.exe -m pytest tests -v ...
[결과] N passed / M failed / X xfail / Y skipped
[추가] 신규 테스트 파일 / 케이스 (없으면 "없음")
[삭제] 폐기된 테스트 (없으면 "없음")
[운영 DB 안전] OK (assert_safe_db_path 통과)
[Lint] ruff app tests scripts → OK / 실패 시 자동수정 명령 안내
[Codex] (대규모 변경 시) Codex 외부 검증 결과 — 판정 / 반영 / 미반영
[Open] 추가 보강 후보
```

## 7.1 Codex 외부 검증 (대규모 변경 시)

자체 회귀 (run_check.bat) 통과 후, 다음 작업 도메인 변경 시 **Codex 독립 검증 의무 경유** (단일 원천: `docs/codex_reviews/CODEX_REVIEW_GUIDE.md`):

- UI 대규모 변경 (Phase 풀세트)
- DB 스키마 변경 (m0XX 신규)
- AI 안전 정책 / 인증 정책 변경
- 도메인 규칙 변경
- 배포 직전

호출:
```powershell
codex.cmd exec --sandbox read-only --ephemeral --output-last-message "docs\codex_reviews\<TIMESTAMP>_<task>_CODEX_REVIEW_RESULT.md" - < "docs\codex_reviews\<TIMESTAMP>_<task>_CODEX_REVIEW_REQUEST.md"
```

Claude 가 RESULT.md 를 *독립 재검토* → [반영 / 미반영 / 보류] 분류 → 최소 수정 → 재테스트.

## 8. 이 프로젝트에서 특히 주의할 점

- 테스트 카운트는 빠르게 변동한다 — 최근 메모리 기준 약 1955 ~ 2142 케이스. 정확 수치는 매번 직접 실행해서 보고.
- AI Phase 검증 워크플로우상 Phase 별로 *runtime test report* 파일이 따로 있다 (`docs/ai/verification/PHASE_NN_RUNTIME_TEST_REPORT.md`). 단순 pytest 통과만으로 Phase 통과로 간주하지 말 것.
- `pytest_loop_10.py` 는 같은 테스트를 10회 돌려 flakiness 확인용. 사용자 메모리 기준 "자체 10회 검증" 워크플로우의 핵심 도구.
- AI 안전 하네스 (`test_ai_safety_harness.py`, `test_phase06_ai_safety.py`) 는 *모든 AI 변경* 의 회귀 회로. 06 Agent 와 항상 동반.
- 한국어 환경 콘솔(cp949) 출력 깨짐 방지를 위해 `scripts/check_db_path.py` 는 `sys.stdout.reconfigure(encoding="utf-8")` 처리 — 다른 스크립트도 동일 패턴.
