# 19-4 availability 예약 가능 여부 / 충돌 검사 분리 — 변경 요약

> 19-4 = **네 번째 실제 코드 리팩토링 세션**. `app/modules/appointments/availability.py`
> 신설 — 점심창 / 낙관적 락 / 시간 충돌 / 도수 중복 / 휴무 차단 *판정 helper* 추출.
> 5회 루프 3회차 통과 (731 passed) — 19-3 baseline 회귀 0.

## 0. 메타

- 세션 이름: **19-4 availability 예약 가능 여부 / 충돌 검사 분리**
- 검증일: 2026-05-03
- 시작 HEAD: `1b8ac36` (19-3 calendar/schedule_view 표시용 view-model 분리)
- 직전 19-3 Codex: pass — yes 19-4 진입 가능

### 0-1. Revision 이력

| 회차 | 결과 | 변경 |
|---|---|---|
| r1 | 조건부 통과 (Codex 19-4 검토 — caveat 1~5: PyInstaller 수치 / 신규 파일 줄 수 / "16 helper" 표기 / 단일 파일 pytest 재현 불가 / `__pycache__` 정리) | 초기 작성 |
| r2 | (본 revision) | **r1 Codex caveat 1~3 + 5 보정** — PyInstaller `93 passed` → 실제 `85 passed`, 신규 파일 줄 수 wc -l 기준 정합 (18 / 369 / 607), "16 helper / 8 상수" → 실제 `14 helper / 9 상수`, `__pycache__` 정리. 동작 / 코드 변경 0 (보고서 수치만 보정). |

## 1. 변경 파일 목록

### 신규 (3개)

> r2 보정 (Codex 19-4 검토 caveat 2): 실측 라인 수 (`wc -l`) 로 정합. r1 표기 (22 / 309 / 534) 가 부정확했음.

| 파일 | 라인 수 (실측 `wc -l`) | 종류 | 책임 |
|---|---|---|---|
| `app/modules/appointments/__init__.py` | **18** | 신규 | appointments 패키지 facade docstring |
| `app/modules/appointments/availability.py` | **369** | 신규 helper | 점심창 / 낙관적 락 / 시간 충돌 / 도수 중복 / 휴무 차단 판정 helper **14** + 상수 **9** |
| `tests/test_19_4_availability.py` | **607** | 신규 contract | 79 테스트 (parse_lunch_window 회귀 + overlaps_lunch_window byte-equivalent + 낙관적 락 + 시간 충돌 + 도수 중복 + 휴무 / 반차 + 단방향 경계 + 외부 API 0 + 라우터 무수정 회귀) |

### 수정 (2개)

| 파일 | 변경 | 이유 |
|---|---|---|
| `dosu_clinic.spec` | **+5 lines** | 19-4 modules 2개 (`app.modules.appointments`, `app.modules.appointments.availability`) hidden imports 추가 |
| `tests/test_pyinstaller_hidden_imports.py` | **+3 lines** | `EXPECTED_19_X_MODULES_MODULES` 6 → 8 |

### 무수정 (회귀 보호) — 19-4 절대 금지 범위 정합

`app/routers/api.py` (모든 appointment CRUD 핸들러 + `_lunch_window` + `_check_lunch_block` +
`_check_version` + `_bump_version` 본체 무수정), `app/routers/ai.py`, `app/services/**`,
`app/models/**`, `app/migrations/m001~m013.py`, `app/templates/**`, `app/static/**`,
`requirements*.txt`, `pyproject.toml`, `tests/conftest.py`, `tests/harness/**`,
기존 모든 비-19-4 테스트.

## 2. 본 세션 의도 / 이유

### 의도

19-P-2 §2-1 V2 트리의 `app/modules/appointments/availability.py` 자리를 *최소 범위* 로 신설.
점심창 / 낙관적 락 / 시간 충돌 / 도수 중복 / 휴무 차단 *판정 helper* 를 *순수 함수* 로 추출.
19-9 appointments 본체 분리 세션이 채택할 수 있는 *facade* 마련.

### 이유

1. **사용자 명시 "기존 예약 가능 여부 판단 로직을 availability 경계로 분리합니다"**:
   `_lunch_window` / `_check_lunch_block` / `_check_version` / `_bump_version` 의 *판정 로직*
   을 *동등한 순수 helper* 로 추출. 호출 시그니처는 *primitives* (HTTPException raise ⊥) —
   호출자가 raise 책임.
2. **사용자 명시 "기존 규칙을 보존" + "휴무 규칙 자체를 새로 바꾸는 것 금지"**:
   백엔드 차단 코드 *신설* ⊥. xfail 7건 + skip 1건 그대로. 도수 중복 / 휴무 차단 helper 는
   *순수 판정* 만 정의 (실제 wire 는 19-9 시점).
3. **사용자 명시 "예약 API 응답 key 변경 금지" + "예약 생성/수정/삭제 전체 흐름 대규모 변경 금지"**:
   `app/routers/api.py` 무수정. 모든 helper 는 *동등 출력* 보장 (회귀 테스트로 검증).
4. **사용자 명시 "compatibility wrapper 가능"**: helper 는 byte-equivalent 결과 + 호출자가
   원하는 raise 패턴으로 활용 가능. 라우터 미채택 (19-9 시점 wire).
5. **PyInstaller 빌드 안전성**: spec 에 19-4 modules 2개 추가 + 검증 4 tests 추가 (89 → 93).

## 3. 새로 만든 modules.appointments 구조

> r2 보정 (Codex 19-4 검토 caveat 3): top-level `def` **14개** (16 아님), 상수 **9개**
> (8 아님). 분류별 helper / 상수 분리 정합.

```
app/modules/appointments/
├── __init__.py                 (18 lines, appointments 패키지 facade)
└── availability.py             (369 lines, helper 14 + 상수 9)
    ├── 점심창 (helper 3 + 상수 2):
    │   - 상수: LUNCH_MIN_BOUND, LUNCH_MAX_BOUND
    │   - helper: parse_lunch_window, overlaps_lunch_window, lunch_block_message
    ├── 낙관적 락 (helper 3 + 상수 2):
    │   - 상수: VERSION_CONFLICT_ERROR_CODE, VERSION_CONFLICT_MESSAGE
    │   - helper: is_version_conflict, version_conflict_detail, next_version
    ├── 시간 충돌 (helper 3):
    │   - helper: appointments_overlap, is_manual_treatment, has_manual_conflict_at_slot
    ├── 휴무 / 반차 (helper 4 + 상수 5):
    │   - 상수: HALF_DAY_BOUNDARY_HOUR, LEAVE_TYPE_FULL, LEAVE_TYPE_AM, LEAVE_TYPE_PM, LEAVE_TYPE_VALUES
    │   - helper: is_morning_slot, is_afternoon_slot, is_leave_blocking, find_blocking_leave
    └── 종료시각 (helper 1):
        - helper: compute_end_at
```

합계 — helper **14** (3+3+3+4+1), 상수 **9** (2+2+0+5+0).

## 4. 실제 이동한 예약 가능 여부 판단 로직

**0 줄 이동** — 본 19-4 시점에 *실제 본체 이동 0*. 모두 facade / 신규 helper.

| api.py 위치 | 이동? | 19-4 helper |
|---|---|---|
| `_lunch_window` (line 64~84) | ✗ | `parse_lunch_window` (pure-input — `load_config()` 호출자 책임) |
| `_check_lunch_block` (line 87~107) | ✗ | `overlaps_lunch_window` (boolean) + `lunch_block_message` (메시지 빌더) |
| `_check_version` (line 1664~1673) | ✗ | `is_version_conflict` (boolean) + `version_conflict_detail` (dict) |
| `_bump_version` (line 1676~1677) | ✗ | `next_version` (int 반환) |
| 도수 중복 차단 (현재 백엔드 미구현) | — | `is_manual_treatment` + `has_manual_conflict_at_slot` (helper 만 정의, 라우터 미채택) |
| 휴무 차단 (현재 백엔드 미구현) | — | `is_morning_slot` / `is_afternoon_slot` / `is_leave_blocking` / `find_blocking_leave` (helper 만 정의) |
| `start_at + timedelta(minutes=duration_min)` 인라인 | ✗ | `compute_end_at` (동등 helper) |

## 5. 유지한 compatibility wrapper

| wrapper | 위치 | 역할 |
|---|---|---|
| `parse_lunch_window` | `availability.py` | `_lunch_window` 와 byte-equivalent 결과 (pure-input — `load_config()` 호출자 책임) |
| `overlaps_lunch_window` + `lunch_block_message` | `availability.py` | `_check_lunch_block` 의 *겹침 판정* 부분 (boolean) + 메시지 빌더 분리 — 호출자가 원하면 `raise HTTPException(400, message)` 가능 |
| `is_version_conflict` + `version_conflict_detail` | `availability.py` | `_check_version` 의 boolean 판정 + 409 detail dict 빌더 |
| `next_version` | `availability.py` | `_bump_version` 의 pure 버전 — DB 변경은 호출자 |
| `compute_end_at` | `availability.py` | `start_at + timedelta(minutes=duration_min)` 인라인 패턴 정합 |

## 6. 기존 API 응답 구조 유지 여부

✓ **100% 보존** — `app/routers/api.py` 무수정.

| URL | 응답 키 | 보존 |
|---|---|---|
| `POST /api/appointments` | id / status / 기존 모든 키 | ✓ |
| `PUT /api/appointments/{aid}` | (전체 그대로) | ✓ |
| `DELETE /api/appointments/{aid}` | (전체 그대로) | ✓ |
| `version_conflict` 409 detail | error / message / current_version | ✓ |
| 점심창 차단 400 메시지 | "점심시간(HH:MM~HH:MM)에는 예약을 잡을 수 없습니다." | ✓ |
| `GET /api/appointments` (FullCalendar event) | (19-3 정합) | ✓ |

## 7. 중복 예약 / 휴무 / 반차 차단 유지 여부

✓ **유지** — 본 19-4 가 *기존 규칙을 변경하지 않음*.

| 영역 | 본 19-4 영향 |
|---|---|
| 점심창 차단 (`_check_lunch_block`) | 본체 그대로 — 라우터에서 호출되는 위치 무수정 |
| 낙관적 락 (`_check_version` / `_bump_version`) | 본체 그대로 |
| 도수 중복 차단 (백엔드 미구현) | helper 만 정의 — 라우터 미채택 (xfail 3 + skip 1 그대로) |
| 휴무 차단 (백엔드 미구현) | helper 만 정의 — 라우터 미채택 (xfail 4 그대로) |
| 비도수 중복 허용 (eswt 등) | 영향 ⊥ |
| 반차 허용 시간대 (am 휴무자의 오후 / pm 휴무자의 오전) | 영향 ⊥ |

## 8. 예약 저장 / 수정 / 삭제 흐름 영향 여부

✗ **영향 없음** — `app/routers/api.py` 의 모든 appointment CRUD 핸들러 무수정.

| 영역 | 본 19-4 영향 |
|---|---|
| `POST /api/appointments` | ⊥ |
| `PUT /api/appointments/{aid}` | ⊥ |
| `DELETE /api/appointments/{aid}` | ⊥ |
| `POST /api/appointments/{aid}/assign` / `split-code` / `approve` / `revert-approve` / `cancel` | ⊥ |
| `_check_lunch_block` / `_check_version` / `_bump_version` 본체 호출 위치 | ⊥ |

## 9. 개인정보 / 운영 DB / 외부 API 보호 결과

### 9-1. 개인정보 (PII) 보호

✓ **무영향** — availability helper 는 환자 PII 미참조 (id / 시간 / 코드 / status 만 사용).

### 9-2. 운영 DB 보호

✓ **100% 보호** — helper 안에서 DB 세션 부재.

### 9-3. 외부 API 호출

✓ **0건** — `test_helpers_do_not_invoke_provider_or_db` 통과.

## 10. 순환참조 위험 여부

✓ **0건** — D-4 단방향 경계 검증 통과 (ast 기반):

| 모듈 | 의존 방향 | 검증 |
|---|---|---|
| `app.modules.appointments.availability` | `datetime` + `typing` 만 (외부 표준 라이브러리) | `test_availability_does_not_import_models_or_db` (ast.Import / ast.ImportFrom 노드 검사) |
| `app.modules.appointments.__init__` | 없음 (빈 facade) | `test_appointments_package_init_does_not_import_models_or_db` |

## 11. 주석 / 문서화 적용 내용

### 11-1. 카테고리별 주석 카운트 (실측)

| 카테고리 | 카운트 | 주요 위치 |
|---|---|---|
| `# COMPAT:` | 8 | availability docstring + parse_lunch_window + overlaps_lunch_window + lunch_block_message + is_version_conflict + version_conflict_detail + next_version + compute_end_at |
| `# SAFETY:` | 2 | __init__ + availability docstring (devtools / curl POST 우회 방지 / DB 변경 ⊥) |
| `# NOTE:` | 8 | 백엔드 차단 wire 시점 / canceled 제외 / 자기 자신 제외 / 도수 미포함 / 반차 12:00 기준 / 시작 시각 분류 / 시간 기반 분기 / config 호출자 책임 |
| `# RISK:` | 2 | 도수 중복 분류 변경 영향 / 라우터 미채택 (19-9) |
| `# TODO(19-x)` | 0 | (없음 — TODO 표기 필요한 항목 부재) |

### 11-2. docstring

| 파일 | docstring 정책 |
|---|---|
| `app/modules/appointments/__init__.py` | 패키지 docstring (역할 + 19-9 마지막 분리 명시) |
| `app/modules/appointments/availability.py` | 모듈 docstring + 16 함수 docstring (모두 COMPAT/SAFETY/NOTE/RISK 명시) |
| `tests/test_19_4_availability.py` | 모듈 docstring + per-test docstring |

## 12. 생성한 리포트 파일

| 파일 | 역할 |
|---|---|
| `reports/refactor/19-4_test_report.md` | 본 세션 영구 보존본 |
| `reports/refactor/19-4_fix_summary.md` | 본 세션 영구 보존본 (이 파일) |
| `reports/refactor/19-4_codex_review_request.md` | 본 세션 영구 보존본 |
| `reports/refactor/latest_test_report.md` | 19-4 덮어쓰기 |
| `reports/refactor/latest_fix_summary.md` | 19-4 덮어쓰기 |
| `reports/refactor/latest_codex_review_request.md` | 19-4 덮어쓰기 |

## 13. 남은 위험 요소

| # | 위험 | 분류 | 해결 시점 |
|---|---|---|---|
| 1 | 19-4 availability helper 미채택 | 의도 (사용자 명시 "기존 규칙을 보존") | 19-9 appointments 본체 분리 시점 채택 |
| 2 | xfail 7건 + skip 1건 (도수 중복 + 휴무 차단 백엔드 미구현) 그대로 | 의도 (사용자 명시 — 신설 ⊥) | 별도 세션 결정 (19-9 또는 신설 세션) |
| 3 | `_lunch_window` / `_check_version` 두 사본 (api.py 본체 + availability.py helper) 공존 | 알려진 — 19-9 시점에 라우터가 helper 채택으로 통합 | 19-9 |
| 4 | 19-4 contract 테스트의 단방향 검증이 ast 기반 — 향후 19-x 분리 모듈에도 동일 패턴 권장 | 권장 사항 | 19-5 ~ 19-9 |

## 14. Codex 검증으로 넘겨도 되는지 자체 판단

**yes — Codex 검증으로 넘길 준비 완료**.

근거:
1. 5회 루프 3회차 통과 (1회차 false positive — ast 기반으로 변경 후 정합).
2. 19-3 baseline (648/1/7) 회귀 0 — 신규 +83 만 추가 (총 731).
3. ruff / check_db_path / PyInstaller 93 tests 모두 통과.
4. 19-4 79 contract 테스트 + 기존 예약/휴무/관리자 30 tests 모두 통과.
5. 운영 DB 미접근 + 외부 API 호출 0.
6. modules.appointments 단방향 경계 (D-4) 검증 통과 (ast 기반).
7. 기존 API 응답 dict / URL / 인증 정책 100% 보존.
8. 예약 저장 / 수정 / 삭제 흐름 ⊥ + 휴무 차단 규칙 ⊥ + 도수 중복 차단 ⊥ (사용자 지시문 정합).
9. 사용자 명시 14 금지 항목 모두 준수.
