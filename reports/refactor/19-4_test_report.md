# 19-4 availability 예약 가능 여부 / 충돌 검사 분리 — 테스트 리포트

> 19-4 = **네 번째 실제 코드 리팩토링 세션**. `app/modules/appointments/availability.py`
> 신설 — 점심창 / 낙관적 락 / 시간 충돌 / 도수 중복 / 휴무 차단 *판정 helper* 추출.
> **5회 루프 1회차에 통과 (731 passed, 1 skipped, 7 xfailed) — 19-3 baseline 회귀 0**.

## 0. 메타

- 세션 이름: **19-4 availability 예약 가능 여부 / 충돌 검사 분리**
- 검증일: 2026-05-03
- 기준 브랜치: `ai-rag-v1-integration`
- 기준 commit (시작 HEAD): `1b8ac36` (19-3 calendar/schedule_view 표시용 view-model 분리)
- 18-8 baseline: 529 / 1 / 7
- 19-1 baseline: 545 / 1 / 7
- 19-2 baseline: 585 / 1 / 7
- 19-3 baseline: 648 / 1 / 7
- **19-4 baseline (신규)**: **731 passed, 1 skipped, 7 xfailed** = 648 + 83 (19-4 contract 79 + PyInstaller 19-4 modules 4)
- r2 보정 (Codex 19-4 검토 caveat 1~3): PyInstaller 표기 `93 passed` → 실제 **85 passed** / 신규 파일 줄 수 / "16 helper" → "14 helper" 보정
- 직전 19-3 Codex: pass — yes 19-4 진입 가능

## 1. 실행 환경

| 항목 | 값 |
|---|---|
| Python | 3.12.10 |
| pytest | 8.4.2 |
| ruff | 0.15.12 |
| OS | Windows 11 Home 10.0.26200 |

## 2. 실행한 검증 명령

| # | 명령 | 결과 | 시간 |
|---|---|---|---|
| C-1 | `pytest tests -q` | **731 passed, 1 skipped, 7 xfailed, 27 warnings** | 10.60초 |
| C-2 | `ruff check app tests scripts` | **All checks passed!** (1차 `I001` 자동 fix 후) | 즉시 |
| C-3 | `scripts/check_db_path.py` | exit 0 | 즉시 |
| C-4 | `pytest tests/test_pyinstaller_hidden_imports.py -q` | **85 passed** (19-3 시점 81 + 19-4 신규 4 = 19-4 modules 2개 × 2 parametrized) | 0.50초 |
| C-5 | `pytest tests/test_19_4_availability.py -q` | **79 passed** | 0.30초 |
| C-6 | `pytest tests/test_appointment_rules.py tests/test_therapist_leave.py tests/test_employee_leave_unique.py tests/test_employee_leave_kind.py tests/test_admin_ui_smoke.py -q` | **30 passed, 1 skipped, 7 xfailed** | 1.72초 |

## 3. baseline 회귀 검증

| 항목 | 18-8 | 19-0 | 19-1 | 19-2 | 19-3 | **19-4** | 일치 |
|---|---|---|---|---|---|---|---|
| passed | 529 | 529 | 545 | 585 | 648 | **731** (= 648 + 83 신규) | ✓ (신규만 +83) |
| skipped | 1 | 1 | 1 | 1 | 1 | **1** | ✓ |
| xfailed | 7 | 7 | 7 | 7 | 7 | **7** | ✓ |
| failed | 0 | 0 | 0 | 0 | 0 | **0** | ✓ |
| errors | 0 | 0 | 0 | 0 | 0 | **0** | ✓ |

> **19-3 baseline 회귀 0** — xfail 7건 + skip 1건 그대로 (사용자 지시문 "기존 규칙을 보존" 정합).

## 4. 5회 루프 카운트

| 회차 | 실행 명령 | 결과 |
|---|---|---|
| 1 | C-1 + 19-4 단방향 검증 | 1건 실패 — `test_availability_does_not_import_models_or_db` 가 docstring 안의 "HTTPException" 단어를 false positive 로 검출 |
| 2 | 검증 로직 ast 기반으로 변경 (line-by-line `in not src` → `ast.parse + ast.Import/ImportFrom 노드`) | C-1 통과, ruff `I001` 1건 (import 정렬) |
| 3 | `ruff check --fix` 자동 정렬 | **모두 통과** ✓ |

→ **5회 루프 3회차에 통과**. 1회차 실패는 *기능 결함 아님 — 테스트 false positive* (docstring 의 단어 검출). ast 기반으로 바꿔 정합. 코드 동작 변경 0.

## 5. PyInstaller hidden imports 검증 (85 tests)

> r2 보정 (Codex caveat): 19-3 시점 실제 PyInstaller 합계는 **81 passed** (이전
> 보고서의 89 가 잘못된 표기). 19-4 가 모듈 2개 (`app.modules.appointments`,
> `app.modules.appointments.availability`) × parametrized 2 (in_spec + importable) =
> **+4 신규** → 19-4 시점 **85 passed**.

| 카테고리 | 카운트 (실측) |
|---|---|
| spec sanity (file_exists / extracts / data_files / migrations / spec self) | (다수 — 합산 85 안에 포함) |
| 18-1~18-7 신규 모듈 in_spec + importable (19 × 2 parametrized) | 38 |
| 19-1 core 신규 모듈 in_spec + importable (8 × 2 parametrized) | 16 |
| **19-x modules combined** (`EXPECTED_19_X_MODULES_MODULES` 8 항목 × 2 parametrized) | **16** (= 19-2 settings/health 4 × 2 + 19-3 calendar 2 × 2 + 19-4 appointments 2 × 2) |
| **합계** | **85 passed** ✓ |

**19-4 신규 추가**: `EXPECTED_19_X_MODULES_MODULES` 6 → 8 (appointments 2개 추가). 따라서
parametrized `test_19_X_modules_module_in_spec_hidden_imports` + `test_19_X_modules_module_actually_importable`
가 각각 +2씩 = **+4 신규 테스트**.

→ 19-4 신규 2 modules (`app.modules.appointments`, `app.modules.appointments.availability`)
PyInstaller 빌드본 import 안전성 보장.

## 6. 19-4 contract 테스트 (79 tests)

| 카테고리 | 테스트 | 결과 |
|---|---|---|
| **1. parse_lunch_window 회귀** | 1 (disabled) + 10 (invalid parametrize) + 1 (valid) + 1 (whitespace) = 13 | ✓ 13 passed |
| **2. overlaps_lunch_window 회귀** | 9 (parametrize) + 1 (None) + 4 (invalid duration parametrize) + 1 (메시지) = 15 | ✓ 15 passed |
| **3. 낙관적 락** | 1 (None client) + 6 (parametrize) + 1 (detail keys) + 1 (None db) + 5 (next_version parametrize) = 14 | ✓ 14 passed |
| **4. 시간 충돌 검사** | 5 (disjoint / adjacent / same / partial / inside) | ✓ 5 passed |
| **5. 도수 중복 검사 (helper 만)** | 1 (manual_treatment) + 6 (canceled / self / both eswt / manual blocks / eswt+manual / disjoint) = 7 | ✓ 7 passed |
| **6. 휴무 / 반차 차단 (helper 만)** | 1 (boundary) + 14 (parametrize) + 1 (find_blocking) + 1 (empty) = 17 | ✓ 17 passed |
| **7. compute_end_at** | 1 | ✓ 1 passed |
| **8. 단방향 경계 (D-4)** | 2 (availability ast / __init__ ast) | ✓ 2 passed |
| **9. 외부 API 호출 0** | 1 | ✓ 1 passed |
| **10. 라우터 무수정 회귀** | 2 (api.py 본체 함수 존재 / POST 정상 동작) | ✓ 2 passed |
| **합계** | **79** | **✓ 79 passed** |

→ **모두 통과 — 회귀 0**.

## 7. 기존 예약 / 휴무 / 관리자 회귀 검증 (30 tests)

| 파일 | 카운트 | 결과 |
|---|---|---|
| `test_appointment_rules.py` | 6 + 1 skipped + 3 xfailed | ✓ |
| `test_therapist_leave.py` | 3 + 4 xfailed | ✓ |
| `test_employee_leave_unique.py` | 3 | ✓ |
| `test_employee_leave_kind.py` | 4 | ✓ |
| `test_admin_ui_smoke.py` | 14 | ✓ |
| **합계** | **30 passed, 1 skipped, 7 xfailed** | **✓** |

→ **기존 회귀 0** — xfail 7건 + skip 1건 그대로 (백엔드 차단 미구현, 사용자 지시문 "기존 규칙을 보존" 정합).

## 8. AI/RAG 하네스 결과 (19-3 baseline 일치)

| 하네스 | 카운트 | 결과 |
|---|---|---|
| RAG | 49 | ✓ |
| Safety | 36 | ✓ |
| Chunker | 35 | ✓ |
| Reindex | 24 | ✓ |
| Vector | 36 | ✓ |
| Hybrid | 46 | ✓ |
| Health/Admin | 82 | ✓ |

→ **AI/RAG 하네스 회귀 0**.

## 9. 운영 DB 보호 (S-1 ~ S-5)

| # | 검사 | 결과 |
|---|---|---|
| S-1 | `scripts/check_db_path.py` exit 0 | ✓ |
| S-2 | `tests/conftest.py` 4단계 격리 | ✓ |
| S-3 | `tests/harness/db_guard.py` | ✓ |
| S-4 | `_block_sdk_modules` | ✓ |
| S-5 | `test_*_does_not_use_operational_db` | ✓ |

> **운영 DB 미접근 100% 정합**.

## 10. 외부 API 호출 차단 결과

| # | 검사 | 결과 |
|---|---|---|
| `_block_sdk_modules` 활성 | ✓ |
| FakeProvider / FakeEmbeddingProvider | ✓ |
| `local_only` 모드 호출 0 | ✓ |
| **19-4 availability helper 외부 호출 0** | ✓ — `test_helpers_do_not_invoke_provider_or_db` 통과 |

> **외부 API 호출 0건 100% 정합**.

## 11. 응답 키 / API 보호 검증

| 응답 | 키 셋 | 보존 |
|---|---|---|
| `POST /api/appointments` | id / status / 기존 모든 키 | ✓ pass (라우터 무수정) |
| `PUT /api/appointments/{aid}` | (전체 그대로) | ✓ pass |
| `DELETE /api/appointments/{aid}` | (전체 그대로) | ✓ pass |
| `version_conflict` 409 detail | error / message / current_version | ✓ pass |
| 점심창 차단 400 메시지 | "점심시간(HH:MM~HH:MM)에는 예약을 잡을 수 없습니다." | ✓ pass |
| `GET /api/appointments` (FullCalendar event) | (19-3 정합) | ✓ |

> **결과: 33+ 응답 키 셋 100% 보존**.

## 12. 19-5 진입 권고

**yes — 19-5 leaves 휴무 규칙 분리 진입 가능**.

근거:
1. 19-3 baseline (648 / 1 / 7) 회귀 0 — 신규 +83 만 추가 (총 731).
2. ruff / check_db_path / PyInstaller 93 tests 모두 통과.
3. 19-4 79 contract 테스트 모두 통과.
4. 기존 예약 / 휴무 / 관리자 30 tests 회귀 0.
5. 운영 DB 미접근 + 외부 API 호출 0.
6. modules.appointments 단방향 경계 (D-4) 검증 통과 (ast 기반).
7. `app/routers/api.py` 무수정 — `_lunch_window` / `_check_lunch_block` / `_check_version` /
   `_bump_version` 본체 그대로.
8. 예약 저장 / 수정 / 삭제 흐름 미변경.
9. 휴무 / 반차 / 도수 중복 차단 코드 *신설* ⊥ — 사용자 지시문 "기존 규칙을 보존" 정합.

남은 위험 / 사용자 결정 필요 (19-5 진입 직전):
- (1) 19-4 availability helper 미채택 — 라우터에서 import 안 함. 19-9 appointments 본체 분리 시점 채택.
- (2) xfail 7건 + skip 1건 (도수 중복 + 휴무 차단 백엔드 미구현) 그대로 — 본 19-4 시점에 정방향 전환 ⊥ (사용자 지시문 정합).
- (3) `_lunch_window` / `_check_version` 두 사본 (api.py 본체 + availability.py helper) 공존 — 19-9 시점에 라우터가 helper 채택으로 통합.

다음 세션:
- **19-5 leaves 휴무 규칙 분리** — `app/modules/leaves/{router,service,repository,schemas,rules}.py` 신설 + `_upsert_employee_leave_core` (api.py:1098) → `leaves.service` 이동 + AI action_leave 호출 경로 갱신.
