# 19-3 calendar / schedule_view 표시용 view-model 분리 — 테스트 리포트

> 19-3 = **세 번째 실제 코드 리팩토링 세션**. `app/modules/calendar/` 신설 +
> `view_models.py` 표시용 순수 helper 추가.
> **5회 루프 1회차에 통과 (648 passed, 1 skipped, 7 xfailed) — 19-2 baseline 회귀 0**.

## 0. 메타

- 세션 이름: **19-3 calendar / schedule_view 표시용 view-model 분리**
- 검증일: 2026-05-03
- 기준 브랜치: `ai-rag-v1-integration`
- 기준 commit (시작 HEAD): 19-2 r1 (settings/feature_flags/health 경계 정리 — Codex 검증 통과)
- 18-8 baseline: 529 / 1 / 7
- 19-1 baseline: 545 / 1 / 7
- 19-2 baseline: 585 / 1 / 7
- **19-3 baseline (신규)**: **648 passed, 1 skipped, 7 xfailed** = 585 + 63 (19-3 contract 51 + PyInstaller 19-3 modules 12)
- 직전 19-2 Codex: pass — yes 19-3 진입 가능

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
| C-1 | `pytest tests -q` | **648 passed, 1 skipped, 7 xfailed, 27 warnings** | 11.31초 |
| C-2 | `ruff check app tests scripts` | **All checks passed!** | 즉시 |
| C-3 | `scripts/check_db_path.py` | exit 0 | 즉시 |
| C-4 | `pytest tests/test_pyinstaller_hidden_imports.py -q` | **89 passed** (= 53 + 16 19-1 + 8 19-2 + 12 19-3) | 0.50초 |
| C-5 | `pytest tests/test_19_3_calendar_view_model.py -q` | **51 passed** | 0.18초 |
| C-6 | `pytest tests/test_admin_ui_smoke.py tests/test_appointment_rules.py tests/test_therapist_leave.py tests/test_employee_leave_unique.py tests/test_employee_leave_kind.py -q` | **30 passed, 1 skipped, 7 xfailed** | 1.76초 |

## 3. baseline 회귀 검증

| 항목 | 18-8 | 19-0 | 19-1 | 19-2 | **19-3** | 일치 |
|---|---|---|---|---|---|---|
| passed | 529 | 529 | 545 | 585 | **648** (= 585 + 63 신규) | ✓ (신규만 +63) |
| skipped | 1 | 1 | 1 | 1 | **1** | ✓ |
| xfailed | 7 | 7 | 7 | 7 | **7** | ✓ |
| failed | 0 | 0 | 0 | 0 | **0** | ✓ |
| errors | 0 | 0 | 0 | 0 | **0** | ✓ |

> **19-2 baseline 회귀 0** — 추가된 63 tests = (a) `tests/test_19_3_calendar_view_model.py` 51 (=
> 7 status_to_opacity parametrize + 1 STATUS_OPACITY 상수 + 5 therapist_color parametrize + 1 상수 +
> 12 lighten_hex parametrize + 1 clamp + 4 appointment_to_calendar_event + 2 employee_to_resource_view +
> 3 leave_to_display + 6 leave_type_label + 5 leave_kind_label + 7 status_to_label/class + 1
> is_past_appointment + 2 단방향 import + 1 외부 API 0 + 1 PII 보존). (b) `tests/test_pyinstaller_hidden_imports.py`
> 의 19-3 modules 2 × (in_spec + importable) = 4 + 19-2 EXPECTED_19_X_MODULES_MODULES 4 → 6 (re-parametrize) =
> 12 신규. 합계 51 + 12 = **63** ✓.

## 4. 5회 루프 카운트

| 회차 | 실행 명령 | 결과 |
|---|---|---|
| 1 | C-1 ~ C-6 + ruff | **모두 1회차 통과** ✓ |

→ **5회 루프 1회차에 통과** (땜질 ⊥, ruff 자동 fix ⊥, 추가 가설 / 수정 ⊥).

## 5. PyInstaller hidden imports 검증 (89 tests = 53 + 16 19-1 + 8 19-2 + 12 19-3)

| 카테고리 | 카운트 | 결과 |
|---|---|---|
| 18-1~18-7 신규 모듈 in_spec + importable | 38 | ✓ 38 passed |
| 19-1 core 신규 모듈 in_spec + importable | 16 | ✓ 16 passed |
| 19-2 modules 신규 모듈 in_spec + importable | 8 | ✓ 8 passed |
| **19-3 modules.calendar 신규 모듈 in_spec** | **6** (= EXPECTED_19_X_MODULES_MODULES 6 × 1) | ✓ **6 passed** |
| **19-3 modules.calendar 신규 모듈 importable** | **6** | ✓ **6 passed** |
| spec sanity / data files / migrations | 15 | ✓ 15 passed |
| **합계** | **89** | **✓ 89 passed** |

→ 19-3 신규 2 modules (`app.modules.calendar`, `app.modules.calendar.view_models`) PyInstaller 빌드본
import 안전성 보장. `EXPECTED_19_X_MODULES_MODULES` 가 6개로 확장됨 (19-2 4 + 19-3 2).

## 6. 19-3 contract 테스트 (51 tests)

| 카테고리 | 테스트 | 결과 |
|---|---|---|
| **1. status_to_opacity 회귀** | 7 (parametrize) + 1 (상수) = 8 | ✓ 8 passed |
| **2. therapist_color fallback** | 5 (parametrize) + 1 (상수) = 6 | ✓ 6 passed |
| **3. lighten_hex byte-equivalent** | 12 (parametrize) + 1 (clamp) = 13 | ✓ 13 passed |
| **4. appointment_to_calendar_event 회귀** | 4 (shape/unassigned/canceled/copy) | ✓ 4 passed |
| **5. employee_to_resource_view** | 2 (3키 + 미배정) | ✓ 2 passed |
| **6. leave_to_display** | 3 (employee form / therapist alias / defaults) | ✓ 3 passed |
| **7. 휴무 / 상태 라벨** | 6 leave_type + 5 leave_kind + 7 status (label/class) = 18 | ✓ 18 passed |
| **8. is_past_appointment** | 1 (basic + None / 빈 fallback) | ✓ 1 passed |
| **9. 단방향 경계 (D-4 정합)** | 2 (view_models / __init__) | ✓ 2 passed |
| **10. 외부 API 호출 0** | 1 (helper tripwire) | ✓ 1 passed |
| **11. PII 보존** | 1 (extended_props 통과) | ✓ 1 passed |
| **합계** | **51** | **✓ 51 passed** |

→ **모두 1회차에 통과 — 회귀 0**.

## 7. 기존 calendar / appointment / leave 회귀 검증 (30 tests)

| 파일 | 카운트 | 결과 |
|---|---|---|
| `test_admin_ui_smoke.py` (관리자 화면) | 14 | ✓ 14 passed |
| `test_appointment_rules.py` (예약 규칙) | 6 + 1 skipped + 3 xfailed | ✓ |
| `test_therapist_leave.py` (휴무 표시) | 3 + 4 xfailed | ✓ |
| `test_employee_leave_unique.py` | 3 | ✓ |
| `test_employee_leave_kind.py` | 4 | ✓ |
| **합계** | **30 passed, 1 skipped, 7 xfailed** | **✓** |

→ **기존 회귀 0** — 19-3 view_model 추가가 calendar/appointment/leave 흐름에 영향 ⊥.

## 8. AI/RAG 하네스 결과 (19-2 baseline 일치)

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
| S-1 | `scripts/check_db_path.py` exit 0 | ✓ pass |
| S-2 | `tests/conftest.py` 4단계 격리 | ✓ pass (648 passed 자동 검증) |
| S-3 | `tests/harness/db_guard.py` | ✓ pass |
| S-4 | `_block_sdk_modules` | ✓ pass |
| S-5 | `test_*_does_not_use_operational_db` | ✓ pass |

> **결과: 운영 DB 미접근 100% 정합**.

## 10. 외부 API 호출 차단 결과

| # | 검사 | 결과 |
|---|---|---|
| `_block_sdk_modules` 활성 | ✓ pass |
| FakeProvider / FakeEmbeddingProvider 만 사용 | ✓ pass |
| `local_only` 모드 호출 0 단언 | ✓ pass (test_local_only_mode.py 4 passed) |
| **19-3 view_model helper 외부 호출 0** | ✓ pass — `test_view_model_helpers_do_not_invoke_provider_or_sdk` 통과 |

> **결과: 외부 API 호출 0건 100% 정합**.

## 11. 응답 키 / API 보호 검증

| 응답 | 키 셋 | 보존 |
|---|---|---|
| `GET /api/appointments` (FullCalendar event) | `id / start / end / color / textColor / extendedProps` (9 top + 16 extendedProps) | ✓ pass (router 무수정) |
| `GET /api/employee-leaves` (6키) | `id / employee_id / leave_date / leave_type / leave_kind / memo` | ✓ pass |
| `GET /api/therapist-leaves` (alias 7키) | `id / therapist_id / employee_id / leave_date / leave_type / leave_kind / memo` | ✓ pass (이중 키 보존) |
| `GET /api/employees` / `/api/therapists` (10키) | `id / name / role / color / active / birth_date / phone / hire_date / can_eswt / can_manual / sort_order` | ✓ pass |
| `GET /api/ai/health` / `/health/public` / `/status` | (19-2 보존 — 19-3 무영향) | ✓ pass |

> **결과: 33+ 응답 키 셋 100% 보존**.

## 12. 19-4 진입 권고

**yes — 19-4 availability 예약 가능 여부 / 충돌 검사 분리 진입 가능**.

근거:
1. 19-2 baseline (585 / 1 / 7) 회귀 0 — 신규 +63 만 추가 (총 648).
2. ruff / check_db_path / PyInstaller 89 tests 모두 통과.
3. 19-3 51 contract 테스트 모두 1회차 통과.
4. 기존 calendar / appointment / leave 30 tests 회귀 0.
5. 운영 DB 미접근 + 외부 API 호출 0 + PII 보존 (마스킹 변경 ⊥) 모두 정합.
6. core / modules.calendar 단방향 경계 (D-4) 검증 통과.
7. `app/routers/api.py` 무수정 — 기존 응답 dict / URL / 인증 정책 100% 보존.
8. 예약 저장 / 수정 / 삭제 로직 미변경. 휴무 차단 규칙 미변경.

남은 위험 / 사용자 결정 필요 (19-4 진입 직전):
- (1) 19-3 view_model 미채택 — 의도. 19-9 appointments 본체 분리 시점에 점진적 채택.
- (2) `_serialize_appointment` (api.py:186) 본체는 19-9 appointments 분리 세션에서 view_model 호출로 위임 예정.
- (3) `_lighten_hex` 본체 (api.py:4316) 는 19-11 stats / 19-7 export_import 분리 세션에서 view_model 호출로 위임 가능성 있음.

다음 세션:
- **19-4 availability 예약 가능 여부 / 충돌 검사 분리** — `_lunch_window` / `_check_lunch_block` (api.py:64~107) 추출 + 휴무 / 도수 중복 백엔드 차단 코드 신설 + xfail 7 + skip 1 정방향 전환.
