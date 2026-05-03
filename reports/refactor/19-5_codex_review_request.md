# 19-5 leaves 휴무 규칙 분리 — Codex 검증 요청서

> 사용자 양식 18개 항목 정합. Codex 가 본 문서를 시작점으로 쓰되 **실제 diff /
> 변경 파일 / 결과 / 로그를 독립적으로 확인** 한다.

---

## 1. 세션 이름

**19-5 leaves 휴무 규칙 분리**.

## 2. 이번 세션 목표

`app/modules/leaves/` 후보 구조 신설 — 휴무 도메인 규칙 (LEAVE_TYPE / 반차 / 차단 판정) +
read-only repository + service helper (`_upsert_employee_leave_core` 동등 +
응답 dict 빌더) 분리. 라우터 / AI action_leave 본체 무수정. 19-3 calendar / 19-4
availability / 19-5 leaves.rules 의 LEAVE_TYPE 정합 검증.

## 3. 변경 파일 목록

### 신규 (5개)

| 파일 | 라인 수 (실측) | 종류 |
|---|---|---|
| `app/modules/leaves/__init__.py` | 35 | 신규 facade docstring |
| `app/modules/leaves/rules.py` | 212 | 신규 helper (7 + 상수 다수) |
| `app/modules/leaves/repository.py` | 100 | 신규 helper (4 — DB 호출자 주입) |
| `app/modules/leaves/service.py` | 135 | 신규 helper (3) |
| `tests/test_19_5_leaves.py` | 589 | 신규 contract (54 테스트) |

### 수정 (2개)

| 파일 | 변경 |
|---|---|
| `dosu_clinic.spec` | +6 lines (19-5 modules 4개 hidden imports + 주석) |
| `tests/test_pyinstaller_hidden_imports.py` | +5 lines (`EXPECTED_19_X_MODULES_MODULES` 8 → 12) |

### 무수정 (절대 금지 범위 정합)

`app/routers/api.py` (`_upsert_employee_leave_core` + 휴무 핸들러 + alias 모두 무수정),
`app/routers/ai.py`, `app/services/ai/action_leave.py` (`_do_upsert` 의 import 경로 보존),
`app/services/**`, `app/models/**`, `app/migrations/m001~m013.py`, `app/templates/**`,
`app/static/**`, `requirements*.txt`, `pyproject.toml`, `tests/conftest.py`,
`tests/harness/**`, **`app/modules/appointments/availability.py`** (사용자 명시
"availability 로직 대규모 재작성 ⊥").

## 4. 실제 이동 / 분리한 휴무 규칙

**0 줄 이동** — 본 19-5 시점에 *실제 본체 이동 0*. 모두 facade / 동등 helper.

| api.py / availability.py 위치 | 19-5 helper |
|---|---|
| `_upsert_employee_leave_core` (api.py:1098) | `service.upsert_employee_leave` (byte-equivalent + log_callback 주입) |
| `list_employee_leaves` 응답 dict (6키) | `service.serialize_employee_leave` |
| `list_therapist_leaves_alias` 응답 dict (7키) | `service.serialize_therapist_leave_alias` |
| `r.leave_type or "full"` / `r.leave_kind or "annual"` 인라인 fallback | `rules.normalize_leave_type` / `normalize_leave_kind` |
| 19-4 `availability.is_morning_slot` / `is_afternoon_slot` | `rules.is_morning_slot` / `is_afternoon_slot` (byte-equivalent) |
| 19-4 `availability.is_leave_blocking` / `find_blocking_leave` | `rules.is_leave_blocking` / `find_blocking_leave` (byte-equivalent) |
| 19-4 `availability.LEAVE_TYPE_*` 상수 | `rules.LEAVE_TYPE_*` (parallel — 19-9 통합) |
| 휴무 차단 한국어 메시지 (백엔드 미구현) | `rules.LEAVE_BLOCK_MESSAGE_FULL/AM/PM` + `leave_block_message()` |

## 5. Compatibility wrapper 유지 여부

✓ **유지**. modules.leaves 는 *동등 helper / 후보 구조* — 라우터 / AI action_leave 미채택
(19-9 시점 채택).

## 6. 수정 금지 범위 준수 여부

✓ **모두 준수**:

| 금지 항목 | 본 19-5 결과 |
|---|---|
| 예약 API 응답 key 변경 | ✗ — `app/routers/api.py` 무수정 |
| 예약 생성/수정/삭제 전체 흐름 대규모 변경 | ✗ |
| availability 로직 대규모 재작성 | ✗ — `app/modules/appointments/availability.py` 무수정 |
| 치료항목/완료체크/통계/문자/AI/RAG 로직 변경 | ✗ |
| DB schema / migration 생성 | ✗ |
| UI 디자인 변경 | ✗ |
| 하네스/테스트 약화 | ✗ |
| 운영 DB 접근 | ✗ |
| 외부 API 호출 | ✗ |
| `requirements.txt` / spec 불필요 수정 | ✗ — spec 은 4개 hidden imports 만 |
| 기존 SMS AI / 휴무 AI 동작 변경 | ✗ — `action_leave._do_upsert` import 경로 보존 |

## 7. 기존 API 응답 key 유지 여부

✓ **100% 보존**. `app/routers/api.py` 무수정.

| URL | 응답 키 | 보존 |
|---|---|---|
| `GET /api/employee-leaves` | id / employee_id / leave_date / leave_type / leave_kind / memo (6키) | ✓ |
| `GET /api/therapist-leaves` | id / **therapist_id** / employee_id / leave_date / leave_type / leave_kind / memo (7키 alias) | ✓ |
| `POST /api/employee-leaves` / `bulk-set` / `DELETE` | (전체 그대로) | ✓ |
| AI `action_leave` parse / preview / execute | (전체 그대로) | ✓ |

## 8. 휴무 등록 / 조회 / 삭제 동작 변경 여부

✗ **변경 없음** — 모든 라우터 핸들러 + `_upsert_employee_leave_core` 본체 무수정.
`test_employee_leaves_endpoint_still_works` / `test_therapist_leaves_alias_endpoint_still_works`
회귀 보호.

## 9. 종일 / 오전반차 / 오후반차 차단 유지 여부

✓ **유지** — 본 19-5 가 *기존 규칙을 변경하지 않음*. 백엔드 차단 코드 *신설 ⊥*. xfail 4건
(`test_therapist_leave.py` — 백엔드 미구현) 그대로.

## 10. 휴무 표시 ↔ 예약 차단 기준 일치 여부

✓ **3 경로 정합**:

| 경로 | LEAVE_TYPE | HALF_DAY_BOUNDARY |
|---|---|---|
| 19-3 calendar/view_models LEAVE_TYPE_LABELS | full / am / pm | (12:00 — view_models 가 직접 시간 분기 ⊥) |
| 19-4 availability LEAVE_TYPE_VALUES | full / am / pm | 12 |
| 19-5 leaves/rules LEAVE_TYPE_VALUES | full / am / pm | 12 |
| `is_leave_blocking` 14건 parametrize 비교 | byte-equivalent (availability vs rules) | ✓ |

→ contract 테스트 4건이 회귀 보호.

## 11. availability 연결 영향 여부

✗ **무수정** — `app/modules/appointments/availability.py` 본체 변경 ⊥. leaves.rules 가
*동등 helper*. 19-4 availability 79 tests 회귀 0.

## 12. 운영 DB 보호 여부

✓ **100% 보호** — `scripts/check_db_path.py` exit 0. repository / service 의 DB 세션은
호출자 주입. `tests/conftest.py` 4단계 격리 + db_guard 통과.

## 13. 외부 API 호출 여부

✓ **0건** — `test_rules_helpers_do_not_invoke_provider_or_db` 통과. `_block_sdk_modules`
자동 활성.

## 14. 순환참조 위험 여부

✓ **0건** — D-4 단방향 경계 검증 통과 (ast 기반):

| 모듈 | 의존 방향 |
|---|---|
| `leaves.rules` | `datetime` + `typing` 만 (외부 표준 라이브러리) |
| `leaves.repository` | top-level import 부재 — `app.models` 함수 안 lazy import |
| `leaves.service` | `app.modules.leaves.rules` (단방향) — `app.routers` / `fastapi` ⊥ |
| `leaves.__init__` | 없음 (빈 facade) |

## 15. 주석 / 문서화 기준 적용 여부

✓ **모두 적용**:

| # | 기준 | 적용 |
|---|---|---|
| 1 | 새 파일 상단 docstring | 5 신규 파일 모두 |
| 2 | 주요 helper 함수 docstring | 14 helper 모두 (COMPAT 명시) |
| 3 | 기존 API/UI 호환 wrapper 의 `COMPAT` 주석 | 다수 |
| 4 | devtools/manual POST 우회 방지 / 운영 DB 보호 부분 `SAFETY` 주석 | 4 위치 |
| 5 | 종일/오전반차/오후반차 기준 / 표시-차단 공유 부분 `NOTE` 또는 `RISK` 주석 | 다수 |
| 6 | TODO(19-x) 형식 | 0 (모든 후속 작업이 19-9 시점 명시) |
| 7 | 의미 없는 모든 줄 주석 금지 | ✓ |
| 8 | 주석 작성 때문에 기능 동작 변경 금지 | ✓ |

## 16. 실행한 테스트와 결과

| # | 명령 | 결과 |
|---|---|---|
| C-1 | `pytest tests -q` | **793 passed, 1 skipped, 7 xfailed** (11.73초) |
| C-2 | `ruff check app tests scripts` | **All checks passed!** (1차 `I001` + `F841` 자동 fix 후) |
| C-3 | `scripts/check_db_path.py` | exit 0 |
| C-4 | `pytest tests/test_pyinstaller_hidden_imports.py -q` | **93 passed** |
| C-5 | `pytest tests/test_19_5_leaves.py -q` | **54 passed** |
| C-6 | `pytest tests/test_appointment_rules.py tests/test_therapist_leave.py tests/test_employee_leave_unique.py tests/test_employee_leave_kind.py tests/test_admin_ui_smoke.py tests/test_19_4_availability.py tests/test_ai_action_leave.py -q` | **153 passed, 1 skipped, 7 xfailed** |

## 17. 실패 / 수정 루프 횟수

| 회차 | 결과 |
|---|---|
| 1 | C-1 ~ C-6 통과. ruff `I001` (import 정렬) + `F841` (미사용 `obj` 변수) 2건 — 자동 fix |

→ **5회 루프 1회차에 통과**. ruff 자동 fix 는 *코드 동작 변경 0*.

## 18. 19-6 treatments / completion_rules 분리로 넘어가도 되는지 판단 기준

**yes — 19-6 진입 가능**.

근거:
1. **5회 루프 1회차 통과** — ruff 자동 fix 만 (동작 변경 0).
2. **19-4 baseline (731/1/7) 회귀 0** — 신규 +62 만 추가 (총 793).
3. **ruff / check_db_path / PyInstaller 93 tests 모두 통과**.
4. **19-5 54 contract + 기존 leaves/availability/AI 153 tests 모두 통과**.
5. **휴무 표시 ↔ 예약 차단 ↔ 도메인 규칙 정합** (LEAVE_TYPE 셋 + 반차 12:00 기준).
6. **AI action_leave 흐름 그대로** — `_do_upsert` 의 `app.routers.api._upsert_employee_leave_core`
   import 보존.
7. **라우터 / 서비스 본체 무수정** — 응답 dict / URL / 인증 정책 100% 보존.
8. **availability 본체 무수정** (사용자 명시 정합).
9. **운영 DB 미접근 + 외부 API 호출 0**.
10. **modules.leaves 단방향 경계 (D-4) 검증 통과** (ast 기반).
11. **사용자 명시 14 금지 항목 모두 준수**.

남은 위험 / 사용자 결정 필요 (19-6 진입 직전):
- (1) 19-5 helpers 미채택 (의도) — 19-9 시점 채택.
- (2) `_upsert_employee_leave_core` 두 사본 (api.py + leaves.service) 공존 — 19-9 통합.
- (3) LEAVE_TYPE / `is_leave_blocking` 두 사본 (availability + leaves.rules) 공존 — 19-9 통합.

다음 세션:
- **19-6 treatments / completion_rules 분리** — `app/modules/treatments/` 신설 +
  `manual60=1` 정책 보존 + `_bump_patient_count` / approve / revert 흐름 분리.

---

## Codex 가 집중 검토할 파일

1. `app/modules/leaves/__init__.py` — 패키지 facade.
2. `app/modules/leaves/rules.py` — 도메인 규칙. 19-4 availability 와 byte-equivalent 검증 필수.
3. `app/modules/leaves/repository.py` — read-only helper. lazy import 검증.
4. `app/modules/leaves/service.py` — `_upsert_employee_leave_core` 동등 + 응답 dict.
5. `tests/test_19_5_leaves.py` — 54 contract 테스트.
6. `dosu_clinic.spec` 19-5 추가 6줄 + `tests/test_pyinstaller_hidden_imports.py` 5줄.

## Codex 가 반드시 확인할 체크리스트

1. **응답 키 100% 보존** — `app/routers/api.py` 무수정.
2. **byte-equivalent** — `is_leave_blocking` / `find_blocking_leave` / `is_morning_slot` /
   `is_afternoon_slot` 결과가 19-4 availability 와 동일.
3. **LEAVE_TYPE 정합** — 19-3 / 19-4 / 19-5 세 경로 동일 셋.
4. **AI action_leave 흐름 무수정** — `_do_upsert` 가 `app.routers.api._upsert_employee_leave_core`
   계속 import.
5. **단방향 경계 (D-4)** — leaves.rules 가 ORM/DB/services/routers 미참조 (ast 검증).
6. **운영 DB 미접근** + **외부 API 호출 0**.
7. **PyInstaller 빌드 안전성** — 19-5 modules 4개 spec 등록 + 8 신규 tests 통과.
8. **5회 루프 1회차 통과** (ruff 자동 fix — 동작 변경 0).

## 자체 판단

**yes — 19-6 진입 가능 (Codex 검증 통과 후)**.
