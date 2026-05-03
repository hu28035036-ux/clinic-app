# 19-5 leaves 휴무 규칙 분리 — 테스트 리포트

> 19-5 = **다섯 번째 실제 코드 리팩토링 세션**. `app/modules/leaves/` 신설 — 휴무
> 도메인 규칙 / read-only repository / service helper 분리.
> **5회 루프 1회차에 통과 (793 passed, 1 skipped, 7 xfailed) — 19-4 baseline 회귀 0**.
> ruff 자동 fix 1회 (import 정렬 + 미사용 변수, 코드 동작 변경 0).

## 0. 메타

- 세션 이름: **19-5 leaves 휴무 규칙 분리**
- 검증일: 2026-05-03
- 기준 commit (시작 HEAD): `48c76de` (19-4 availability 분리)
- baseline 추이: 18-8 (529) → 19-1 (545) → 19-2 (585) → 19-3 (648) → 19-4 (731) → **19-5 (793)** = 731 + 62 (19-5 contract 54 + PyInstaller 19-5 modules 8)
- 직전 19-4 Codex (r2): pass — yes 19-5 진입 가능

## 1. 실행 환경

| 항목 | 값 |
|---|---|
| Python | 3.12.10 |
| pytest | 8.4.2 |
| ruff | 0.15.12 |

## 2. 실행한 검증 명령

| # | 명령 | 결과 |
|---|---|---|
| C-1 | `pytest tests -q` | **793 passed, 1 skipped, 7 xfailed** (11.73초) |
| C-2 | `ruff check app tests scripts` | **All checks passed!** (1차 `I001` + `F841` 자동 fix 후) |
| C-3 | `scripts/check_db_path.py` | exit 0 |
| C-4 | `pytest tests/test_pyinstaller_hidden_imports.py -q` | **93 passed** (= 19-4 시점 85 + 19-5 신규 8 = modules 4개 × parametrized 2) |
| C-5 | `pytest tests/test_19_5_leaves.py -q` | **54 passed** |
| C-6 | `pytest tests/test_appointment_rules.py tests/test_therapist_leave.py tests/test_employee_leave_unique.py tests/test_employee_leave_kind.py tests/test_admin_ui_smoke.py tests/test_19_4_availability.py tests/test_ai_action_leave.py -q` | **153 passed, 1 skipped, 7 xfailed** (3.56초) |

## 3. baseline 회귀 검증

| 항목 | 19-4 | **19-5** | 일치 |
|---|---|---|---|
| passed | 731 | **793** (= 731 + 62 신규) | ✓ (신규만 +62) |
| skipped | 1 | **1** | ✓ |
| xfailed | 7 | **7** | ✓ |
| failed | 0 | **0** | ✓ |
| errors | 0 | **0** | ✓ |

> **19-4 baseline 회귀 0** — xfail 7건 + skip 1건 그대로 (19-4 와 동일 — leaves 분리는
> 백엔드 차단 코드 신설 ⊥, 사용자 지시문 정합).

## 4. 5회 루프 카운트

| 회차 | 결과 |
|---|---|
| 1 | C-1 ~ C-6 통과. ruff `I001` (import 정렬) + `F841` (미사용 `obj` 변수) 2건 — 자동 fix |

→ **5회 루프 1회차에 통과**. ruff 자동 fix 는 *코드 동작 변경 0* (import 정렬 + 미사용 변수 삭제).

## 5. PyInstaller hidden imports 검증 (93 tests)

| 카테고리 | 카운트 |
|---|---|
| spec sanity / 18-x / 19-1 core / data files / migrations | (합산 안에 포함) |
| 19-x modules combined (parametrized: 8 in_spec + 8 importable) | **24** (= settings/health 4 + calendar 2 + appointments 2 + **leaves 4**) × 2 = 24 |
| **19-5 신규** | **8** (modules 4개 × parametrized 2) |
| **합계** | **93 passed** |

→ 19-5 신규 4 modules (`app.modules.leaves`, `rules`, `repository`, `service`) PyInstaller
빌드본 import 안전성 보장. `EXPECTED_19_X_MODULES_MODULES` 가 8 → 12 으로 확장.

## 6. 19-5 contract 테스트 (54 tests)

| 카테고리 | 테스트 수 |
|---|---|
| 1. LEAVE_TYPE / LEAVE_KIND 상수 정합 (19-3 / 19-4 와) | 4 |
| 2. is_morning_slot / is_afternoon_slot 동등 (parametrize 6) | 6 |
| 3. is_leave_blocking 동등 (parametrize 14) + find_blocking_leave 동등 | 15 |
| 4. leave_block_message 한국어 키워드 | 2 |
| 5. normalize_leave_type / kind (parametrize 6+5) | 11 |
| 6. service.upsert_employee_leave 동등 + log_callback | 2 |
| 7. serialize_employee_leave / serialize_therapist_leave_alias | 2 |
| 8. repository read-only (FIXED_LEAVE_DATE / 직원-날짜 조회) | 2 |
| 9. 단방향 경계 ast 기반 (rules / repository / service / __init__) | 4 |
| 10. AI action_leave 흐름 무수정 회귀 (import 경로 보존 / api.py 본체 보존) | 2 |
| 11. 라우터 무수정 회귀 (POST 휴무 / GET alias) | 2 |
| 12. rules 외부 호출 0 | 1 |
| **합계** | **54** ✓ |

## 7. 기존 회귀 검증 (153 tests)

| 파일 | 카운트 | 결과 |
|---|---|---|
| `test_appointment_rules.py` | 6 + 1 skipped + 3 xfailed | ✓ |
| `test_therapist_leave.py` | 3 + 4 xfailed | ✓ |
| `test_employee_leave_unique.py` | 3 | ✓ |
| `test_employee_leave_kind.py` | 4 | ✓ |
| `test_admin_ui_smoke.py` | 14 | ✓ |
| `test_19_4_availability.py` | 79 | ✓ |
| `test_ai_action_leave.py` | 44 | ✓ |
| **합계** | **153 passed, 1 skipped, 7 xfailed** | ✓ |

→ **AI action_leave 44 tests 회귀 0** — 사용자 명시 "기존 휴무 AI 동작 변경 금지" 정합.
→ **19-4 availability 79 tests 회귀 0** — 사용자 명시 "availability 로직 대규모 재작성 ⊥" 정합.

## 8. AI/RAG 하네스 결과

회귀 0 (전체 793 안에 포함).

## 9. 운영 DB 보호 / 외부 API 차단 결과

| # | 검사 | 결과 |
|---|---|---|
| `scripts/check_db_path.py` exit 0 | ✓ |
| `tests/conftest.py` 4단계 격리 | ✓ |
| `_block_sdk_modules` | ✓ |
| `local_only` 모드 호출 0 | ✓ |
| **19-5 rules helper 외부 호출 0** | ✓ — `test_rules_helpers_do_not_invoke_provider_or_db` 통과 |
| **leaves.repository / service** | DB 세션은 *호출자 주입* — 운영 DB 직접 open ⊥ |

## 10. 응답 키 / API 보호 검증

| 응답 | 키 셋 | 보존 |
|---|---|---|
| `GET /api/employee-leaves` | id / employee_id / leave_date / leave_type / leave_kind / memo | ✓ pass (라우터 무수정) |
| `GET /api/therapist-leaves` (alias) | id / **therapist_id** / employee_id / leave_date / leave_type / leave_kind / memo | ✓ pass (이중 키 보존) |
| `POST /api/employee-leaves` | (전체 그대로) | ✓ |
| `POST /api/employee-leaves/bulk-set` | ok / count | ✓ |
| `DELETE /api/employee-leaves/{lid}` | ok | ✓ |
| AI `action_leave` 흐름 (parse / preview / execute) | (전체 그대로) | ✓ pass — `_do_upsert` 가 `app.routers.api._upsert_employee_leave_core` import 유지 |

## 11. 휴무 표시 ↔ 예약 차단 ↔ 도메인 규칙 정합 검증

| 영역 | 기준 | 정합 |
|---|---|---|
| 19-3 calendar/view_models LEAVE_TYPE_LABELS 키 셋 | full / am / pm | ✓ |
| 19-4 availability LEAVE_TYPE_VALUES | full / am / pm | ✓ |
| 19-5 leaves/rules LEAVE_TYPE_VALUES | full / am / pm | ✓ |
| 반차 12:00 정확 기준 (19-4 vs 19-5) | HALF_DAY_BOUNDARY_HOUR == 12 | ✓ |
| `is_leave_blocking` (19-4 vs 19-5) | byte-equivalent (parametrize 14건 비교) | ✓ |
| `find_blocking_leave` (19-4 vs 19-5) | byte-equivalent | ✓ |

→ **세 경로 (표시 / 차단 / 도메인) 모두 동일 LEAVE_TYPE 기준** — contract 테스트가 회귀 보호.

## 12. 19-6 진입 권고

**yes — 19-6 treatments / completion_rules 분리 진입 가능**.

근거:
1. 19-4 baseline (731 / 1 / 7) 회귀 0 — 신규 +62 만 추가 (총 793).
2. ruff / check_db_path / PyInstaller 93 tests 모두 통과.
3. 19-5 54 contract + 기존 leaves/availability/AI 153 tests 모두 통과.
4. 휴무 표시 ↔ 예약 차단 ↔ 도메인 규칙 정합 (LEAVE_TYPE 셋 + 반차 12:00 기준).
5. AI action_leave 흐름 그대로 — `_do_upsert` 의 `app.routers.api._upsert_employee_leave_core`
   import 보존.
6. 라우터 / 서비스 본체 무수정 — 응답 dict / URL / 인증 정책 100% 보존.
7. 운영 DB 미접근 + 외부 API 호출 0 + PII 미참조.
8. modules.leaves 단방향 경계 (D-4) 검증 통과 (ast 기반).

남은 위험 / 사용자 결정 필요 (19-6 진입 직전):
- (1) 19-5 helpers 미채택 (의도) — 19-9 시점 라우터 + AI action_leave 가 채택 통합.
- (2) `_upsert_employee_leave_core` 두 사본 (api.py 본체 + leaves.service) 공존 —
  19-9 시점 단일 진실원천 통합.
- (3) `is_leave_blocking` / LEAVE_TYPE 두 사본 (availability + leaves.rules) 공존 —
  19-9 시점 통합 후보.

다음 세션:
- **19-6 treatments / completion_rules 분리** — `app/modules/treatments/` 신설 +
  `manual60=1` 정책 보존 + `_bump_patient_count` / approve / revert 흐름 분리.
