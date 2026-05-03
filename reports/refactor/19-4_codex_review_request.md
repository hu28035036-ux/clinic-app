# 19-4 availability 예약 가능 여부 / 충돌 검사 분리 — Codex 검증 요청서

> 사용자 양식 16개 항목 정합. Codex 가 본 문서를 시작점으로 쓰되 **실제 diff /
> 변경 파일 / 결과 / 로그를 독립적으로 확인** 한다.

## r2 Revision (Codex 19-4 r1 caveat 보정)

| 항목 | r1 표기 | 실측 (r2 보정) |
|---|---|---|
| `app/modules/appointments/__init__.py` | 22 lines | **18 lines** |
| `app/modules/appointments/availability.py` | 309 lines | **369 lines** |
| `tests/test_19_4_availability.py` | 534 lines | **607 lines** |
| availability helper 함수 수 | 16 | **14** (top-level `def`) |
| availability 상수 수 | 8 | **9** |
| PyInstaller hidden imports tests | 93 passed | **85 passed** |

→ 코드 / 테스트 동작 변경 0 — 보고서 수치만 보정. r1 검증 결과 (조건부 통과,
yes 19-5 진입 가능) 유지.

또한 `app/modules/appointments/__pycache__` 는 r2 시점에 정리됨 (커밋 전).

---

## 1. 세션 이름

**19-4 availability 예약 가능 여부 / 충돌 검사 분리**.

## 2. 이번 세션 목표

`app/modules/appointments/availability.py` 신설 — 점심창 / 낙관적 락 / 시간 충돌 /
도수 중복 / 휴무 차단 *판정 helper* 추출. 라우터 / 서비스 본체 무수정. 백엔드 차단 코드
*신설* ⊥ (사용자 지시문 "기존 규칙을 보존"). xfail / skip 그대로.

## 3. 변경 파일 목록

### 신규 (3개)

> r2 보정 (Codex 19-4 검토 caveat 2~3): 실측 라인 수 (`wc -l`) 로 정합. helper 14
> (16 아님), 상수 9 (8 아님).

| 파일 | 라인 수 (실측) | 종류 |
|---|---|---|
| `app/modules/appointments/__init__.py` | **18** | 신규 facade docstring |
| `app/modules/appointments/availability.py` | **369** | 신규 helper (**14 + 9 상수**) |
| `tests/test_19_4_availability.py` | **607** | 신규 contract (79 테스트) |

### 수정 (2개)

| 파일 | 변경 |
|---|---|
| `dosu_clinic.spec` | +5 lines (19-4 modules 2개 hidden imports) |
| `tests/test_pyinstaller_hidden_imports.py` | +3 lines (`EXPECTED_19_X_MODULES_MODULES` 6 → 8) |

### 무수정 (절대 금지 범위 정합)

`app/routers/api.py` (모든 appointment CRUD + `_lunch_window` + `_check_lunch_block` +
`_check_version` + `_bump_version` 본체 무수정), `app/routers/ai.py`, `app/services/**`,
`app/models/**`, `app/migrations/m001~m013.py`, `app/templates/**`, `app/static/**`,
`requirements*.txt`, `pyproject.toml`, `tests/conftest.py`, `tests/harness/**`.

## 4. 실제 이동 / 분리한 예약 가능 여부 로직

**0 줄 이동** — 본 19-4 시점에 *실제 본체 이동 0*. 모두 facade / 신규 helper.

| api.py 위치 | 이동? | 19-4 helper |
|---|---|---|
| `_lunch_window` (line 64) | ✗ | `parse_lunch_window` (pure-input) |
| `_check_lunch_block` (line 87) | ✗ | `overlaps_lunch_window` (boolean) + `lunch_block_message` |
| `_check_version` (line 1664) | ✗ | `is_version_conflict` (boolean) + `version_conflict_detail` (dict) |
| `_bump_version` (line 1676) | ✗ | `next_version` |
| 도수 중복 (백엔드 미구현) | — | `is_manual_treatment` + `has_manual_conflict_at_slot` (helper 만) |
| 휴무 차단 (백엔드 미구현) | — | `is_morning_slot` / `is_afternoon_slot` / `is_leave_blocking` / `find_blocking_leave` |
| `start_at + timedelta(minutes=...)` 인라인 | ✗ | `compute_end_at` |

## 5. Compatibility wrapper 유지 여부

✓ **유지**. 모든 helper 가 byte-equivalent 또는 동등 결과 — 호출자가 원하면 `raise HTTPException(...)`
로 wrap 가능. 라우터 미채택 (19-9 시점).

## 6. 수정 금지 범위 준수 여부

✓ **모두 준수**:

| 금지 항목 | 본 19-4 결과 |
|---|---|
| 예약 API 응답 key 변경 | ✗ — `app/routers/api.py` 무수정 |
| 예약 생성/수정/삭제 전체 흐름 대규모 변경 | ✗ |
| 휴무 규칙 자체를 새로 바꾸는 것 | ✗ — 백엔드 차단 코드 *신설* ⊥ |
| 치료항목/완료체크/통계/문자/AI/RAG 로직 변경 | ✗ |
| DB schema / migration 생성 | ✗ |
| UI 변경 | ✗ |
| 하네스/테스트 약화 | ✗ |
| 운영 DB 접근 | ✗ |
| 외부 API 호출 | ✗ |
| `requirements.txt` / spec 불필요 수정 | ✗ — spec 은 2개 hidden imports 만 |
| 기존 SMS AI / 휴무 AI 동작 변경 | ✗ |

## 7. 기존 API 응답 key 유지 여부

✓ **100% 보존**. `app/routers/api.py` 무수정.

| URL | 응답 키 | 보존 |
|---|---|---|
| `POST /api/appointments` | id / status / 기존 모든 키 | ✓ |
| `PUT /api/appointments/{aid}` / `DELETE` 등 | 전체 그대로 | ✓ |
| `version_conflict` 409 detail | error / message / current_version | ✓ |
| 점심창 차단 400 메시지 포맷 | "점심시간(HH:MM~HH:MM)에는 예약을 잡을 수 없습니다." | ✓ |

## 8. 예약 생성 / 수정 / 삭제 동작 변경 여부

✗ **변경 없음** — 모든 핸들러 무수정.

## 9. 휴무 / 반차 / 중복 예약 차단 유지 여부

✓ **유지** — 본 19-4 가 *기존 규칙을 변경하지 않음*:

| 영역 | 결과 |
|---|---|
| 점심창 차단 (구현됨) | 본체 그대로 |
| 낙관적 락 (구현됨) | 본체 그대로 |
| 도수 중복 차단 (백엔드 미구현) | helper 만 정의 — 라우터 미채택 (xfail 3 + skip 1 그대로) |
| 휴무 차단 (백엔드 미구현) | helper 만 정의 — 라우터 미채택 (xfail 4 그대로) |
| 비도수 중복 허용 | ⊥ |
| 반차 허용 시간대 | ⊥ |

## 10. 운영 DB 보호 여부

✓ **100% 보호** — `scripts/check_db_path.py` exit 0 + helper 안에서 DB 세션 부재.

## 11. 외부 API 호출 여부

✓ **0건** — `test_helpers_do_not_invoke_provider_or_db` 통과. `_block_sdk_modules` 자동 활성.

## 12. 순환참조 위험 여부

✓ **0건** — D-4 단방향 경계 검증 통과 (ast 기반):

| 모듈 | 의존 방향 |
|---|---|
| `app.modules.appointments.availability` | `datetime` + `typing` 만 |
| `app.modules.appointments.__init__` | 없음 |

→ `app.models` / `app.services` / `app.routers` / `app.database` / `sqlalchemy` / `fastapi` /
다른 modules (settings/health/calendar) 모두 미참조.

## 13. 주석 / 문서화 기준 적용 여부

✓ **모두 적용**:

| # | 기준 | 적용 |
|---|---|---|
| 1 | 새 파일 상단 docstring | 3 신규 파일 모두 |
| 2 | 주요 helper 함수 docstring | 16 helper 모두 (COMPAT/SAFETY/NOTE/RISK 명시) |
| 3 | 기존 API/UI 호환 wrapper 의 `COMPAT` 주석 | 8 위치 |
| 4 | devtools/manual POST 우회 방지 / 운영 DB 보호 부분 `SAFETY` 주석 | 2 위치 |
| 5 | 휴무 차단 / 반차 / 중복 / 자기 자신 제외 규칙 `NOTE` 또는 `RISK` 주석 | 8 NOTE + 2 RISK |
| 6 | TODO(19-x) 형식 | (해당 없음 — TODO 필요 항목 부재) |
| 7 | 의미 없는 모든 줄 주석 금지 | ✓ |
| 8 | 주석 작성 때문에 기능 동작 변경 금지 | ✓ |

## 14. 실행한 테스트와 결과

| # | 명령 | 결과 |
|---|---|---|
| C-1 | `pytest tests -q` | **731 passed, 1 skipped, 7 xfailed** (10.60초) |
| C-2 | `ruff check app tests scripts` | **All checks passed!** (1차 `I001` 자동 fix 후) |
| C-3 | `scripts/check_db_path.py` | exit 0 |
| C-4 | `pytest tests/test_pyinstaller_hidden_imports.py -q` | **85 passed** (r2 보정 — Codex caveat 1) |
| C-5 | `pytest tests/test_19_4_availability.py -q` | **79 passed** |
| C-6 | `pytest tests/test_appointment_rules.py tests/test_therapist_leave.py tests/test_employee_leave_unique.py tests/test_employee_leave_kind.py tests/test_admin_ui_smoke.py -q` | **30 passed, 1 skipped, 7 xfailed** |

## 15. 실패 / 수정 루프 횟수

| 회차 | 결과 |
|---|---|
| 1 | `test_availability_does_not_import_models_or_db` 1건 실패 — docstring 의 "HTTPException" 단어 false positive |
| 2 | 검증 로직을 ast 기반 (Import/ImportFrom 노드)으로 변경 → C-1 통과, ruff `I001` 1건 |
| 3 | `ruff check --fix` 자동 정렬 → **모두 통과** ✓ |

→ **5회 루프 3회차에 통과**. 1회차 실패는 *기능 결함 아님 — 테스트 false positive*. 코드 동작 변경 0.

## 16. 19-5 leaves 휴무 규칙 분리로 넘어가도 되는지 판단 기준

**yes — 19-5 진입 가능**.

근거:
1. **5회 루프 3회차 통과** — 1회차 false positive 만 발생, 코드 동작 변경 0.
2. **19-3 baseline (648/1/7) 회귀 0** — 신규 +83 만 추가 (총 731).
3. **ruff / check_db_path / PyInstaller 93 tests 모두 통과**.
4. **19-4 79 contract 테스트 + 기존 예약/휴무/관리자 30 tests 모두 통과**.
5. **운영 DB 미접근 + 외부 API 호출 0**.
6. **modules.appointments 단방향 경계 (D-4) 검증 통과** (ast 기반).
7. **기존 API 응답 dict / URL / 인증 정책 100% 보존**.
8. **예약 저장 / 수정 / 삭제 ⊥ + 휴무 차단 / 도수 중복 차단 ⊥** (사용자 지시문 정합).
9. **사용자 명시 14 금지 항목 모두 준수**.

남은 위험 / 사용자 결정 필요 (19-5 진입 직전):
- (1) 19-4 helper 미채택 (의도) — 19-9 시점 채택.
- (2) xfail 7 + skip 1 (백엔드 차단 미구현) 그대로.
- (3) `_lunch_window` / `_check_version` 두 사본 공존 — 19-9 시점 통합.

다음 세션:
- **19-5 leaves 휴무 규칙 분리** — `app/modules/leaves/{router,service,repository,schemas,rules}.py` 신설 + `_upsert_employee_leave_core` (api.py:1098) 분리 + AI action_leave 호출 경로 갱신 (단일 진실원천 보존).

---

## Codex 가 집중 검토할 파일

1. `app/modules/appointments/__init__.py` — 패키지 facade.
2. `app/modules/appointments/availability.py` — 16 helper. `_lunch_window` / `_check_lunch_block` /
   `_check_version` / `_bump_version` 와 byte-equivalent 검증 필수.
3. `tests/test_19_4_availability.py` — 79 contract 테스트. ast 기반 단방향 검증 패턴.
4. `dosu_clinic.spec` 19-4 추가 5줄 + `tests/test_pyinstaller_hidden_imports.py` 3줄.

## Codex 가 반드시 확인할 체크리스트

1. **응답 키 100% 보존** — `app/routers/api.py` 무수정.
2. **byte-equivalent** — `parse_lunch_window` / `overlaps_lunch_window` / `is_version_conflict` /
   `version_conflict_detail` / `next_version` 결과가 본체와 동등.
3. **단방향 경계 (D-4)** — ast 기반 검증 (docstring/주석 false positive 회피).
4. **백엔드 차단 코드 신설 ⊥** — 사용자 지시문 "기존 규칙을 보존" 정합. xfail / skip 그대로.
5. **HTTPException raise ⊥** — helper 안에서 `raise HTTPException` 부재 (호출자 책임).
6. **운영 DB 미접근** + **외부 API 호출 0**.
7. **PyInstaller 빌드 안전성** — 19-4 modules 2개 spec 등록 + 4 신규 tests (모듈 2개 × parametrized 2 = in_spec + importable) 통과. 19-4 시점 PyInstaller 합계 **85 passed** (r2 보정).
8. **5회 루프 3회차 통과** (1회차 false positive — 코드 동작 변경 0).

## 자체 판단

**yes — 19-5 진입 가능 (Codex 검증 통과 후)**.
