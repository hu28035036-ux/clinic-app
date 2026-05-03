# 19-5 leaves 휴무 규칙 분리 — 변경 요약

> 19-5 = **다섯 번째 실제 코드 리팩토링 세션**. `app/modules/leaves/` 후보 구조 신설 —
> 휴무 도메인 규칙 / read-only repository / service helper 분리.
> 5회 루프 1회차 통과 (793 passed) — 19-4 baseline 회귀 0.

## 0. 메타

- 세션 이름: **19-5 leaves 휴무 규칙 분리**
- 검증일: 2026-05-03
- 시작 HEAD: `48c76de` (19-4 availability)
- 직전 19-4 Codex (r2): pass — yes 19-5 진입 가능

## 1. 변경 파일 목록

### 신규 (5개)

> 라인 수는 실측 (`wc -l`) 기준.

| 파일 | 라인 수 | 종류 | 책임 |
|---|---|---|---|
| `app/modules/leaves/__init__.py` | 35 | 신규 | leaves 패키지 facade docstring |
| `app/modules/leaves/rules.py` | 212 | 신규 helper | 휴무 도메인 규칙 — LEAVE_TYPE/LEAVE_KIND 상수 + 종일/반차 차단 판정 + 차단 사유 메시지. 단일 진실원천 후보. helper 7 + 상수 다수. |
| `app/modules/leaves/repository.py` | 100 | 신규 helper | 휴무 row read-only 조회 (DB 세션 호출자 주입). helper 4. |
| `app/modules/leaves/service.py` | 135 | 신규 helper | `_upsert_employee_leave_core` 동등 helper + 응답 dict 빌더 (employee / therapist alias). helper 3. |
| `tests/test_19_5_leaves.py` | 589 | 신규 contract | 54 테스트 (LEAVE_TYPE 정합 + is_leave_blocking byte-equivalent + service 동등 + 단방향 ast + AI action_leave 무수정 회귀) |

### 수정 (2개)

| 파일 | 변경 |
|---|---|
| `dosu_clinic.spec` | +6 lines (19-5 modules 4개 hidden imports + 주석) |
| `tests/test_pyinstaller_hidden_imports.py` | +5 lines (`EXPECTED_19_X_MODULES_MODULES` 8 → 12) |

### 무수정 (회귀 보호) — 19-5 절대 금지 범위 정합

`app/routers/api.py` (`_upsert_employee_leave_core` + 휴무 핸들러 + alias 모두 무수정),
`app/routers/ai.py`, `app/services/ai/action_leave.py` (`_do_upsert` 의 import 경로 보존),
`app/services/**`, `app/models/**`, `app/migrations/m001~m013.py`, `app/templates/**`,
`app/static/**`, `requirements*.txt`, `pyproject.toml`, `tests/conftest.py`,
`tests/harness/**`, **`app/modules/appointments/availability.py`** (사용자 명시
"availability 로직 대규모 재작성 ⊥").

## 2. 본 세션 의도 / 이유

### 의도

19-P-2 §2-1 V2 트리의 `app/modules/leaves/` 자리를 *최소 범위* 로 신설. 휴무 도메인
규칙 (LEAVE_TYPE / 반차 / 차단 판정) + 조회 + service helper 를 *parallel 정의*
(라우터 + AI action_leave 무수정). 19-9 appointments 본체 분리 시점에 채택할
*단일 진실원천 후보* 마련.

### 이유

1. **사용자 명시 "기존 예약 가능 여부 판단 로직을 leaves 경계로 분리"**:
   `_upsert_employee_leave_core` 동등 service helper + LEAVE_TYPE 도메인 규칙 분리.
   라우터 무수정 (19-9 시점 채택).
2. **사용자 명시 "휴무 표시 로직과 예약 차단 규칙이 서로 불일치하지 않도록 정리"**:
   19-3 calendar/view_models / 19-4 availability / 19-5 leaves/rules 의 LEAVE_TYPE
   상수가 모두 일치. 19-5 contract 테스트가 세 경로 정합 회귀 검증.
3. **사용자 명시 "기존 SMS AI / 휴무 AI 동작 변경 금지"**:
   `app/services/ai/action_leave.py:_do_upsert` 의 `from ...routers.api import
   _upsert_employee_leave_core` 그대로 보존. 19-9 시점에 leaves.service 채택.
4. **사용자 명시 "availability 로직 대규모 재작성 ⊥"**:
   19-4 availability.py 무수정. leaves.rules 가 *동등 helper* (byte-equivalent) —
   contract 테스트로 동등성 보호.
5. **사용자 명시 "기존 endpoint/import 경로가 깨지지 않도록 compatibility wrapper"**:
   라우터 / AI 흐름 무수정. modules.leaves 는 *후보 구조* 만 — 19-9 시점 채택.

## 3. 새로 만든 modules.leaves 구조

```
app/modules/leaves/
├── __init__.py           (35 lines, leaves 패키지 facade)
├── rules.py              (212 lines, helper 7 + 상수 다수)
│   ├── 상수: LEAVE_TYPE_FULL/AM/PM/VALUES, LEAVE_KIND_ANNUAL/MONTHLY/VALUES/DEFAULT,
│   │       HALF_DAY_BOUNDARY_HOUR, LEAVE_BLOCK_MESSAGE_FULL/AM/PM
│   ├── helper: is_morning_slot / is_afternoon_slot / is_leave_blocking /
│   │          find_blocking_leave / leave_block_message /
│   │          normalize_leave_type / normalize_leave_kind
├── repository.py         (100 lines, helper 4 — DB 호출자 주입)
│   └── helper: list_leaves_for_date / get_leave_for_employee_date /
│              get_leave_by_id / list_leaves_for_employee_date_range
└── service.py            (135 lines, helper 3)
    └── helper: upsert_employee_leave / serialize_employee_leave /
               serialize_therapist_leave_alias
```

합계 — helper **14** (rules 7 + repository 4 + service 3), 상수 11.

## 4. 실제 이동한 휴무 규칙

**0 줄 이동** — 본 19-5 시점에 *실제 본체 이동 0*. 모두 facade / 동등 helper.

| api.py / availability.py 위치 | 이동? | 19-5 helper |
|---|---|---|
| `_upsert_employee_leave_core` (api.py:1098) | ✗ | `service.upsert_employee_leave` (동등 helper, sync 로깅 콜백 주입) |
| `list_employee_leaves` 응답 dict (api.py:1088~1095) | ✗ | `service.serialize_employee_leave` (6키 byte-equivalent) |
| `list_therapist_leaves_alias` 응답 dict (api.py:1191~1199) | ✗ | `service.serialize_therapist_leave_alias` (7키 byte-equivalent) |
| `r.leave_type or "full"` 인라인 (api.py:1092 외) | ✗ | `rules.normalize_leave_type` |
| `r.leave_kind or "annual"` 인라인 (api.py:1093 외) | ✗ | `rules.normalize_leave_kind` |
| 19-4 `availability.is_morning_slot` / `is_afternoon_slot` | ✗ | `rules.is_morning_slot` / `is_afternoon_slot` (byte-equivalent) |
| 19-4 `availability.is_leave_blocking` / `find_blocking_leave` | ✗ | `rules.is_leave_blocking` / `find_blocking_leave` (byte-equivalent) |
| 19-4 `availability.LEAVE_TYPE_*` 상수 | ✗ | `rules.LEAVE_TYPE_*` (parallel 정의 — 19-9 통합) |

## 5. 유지한 compatibility wrapper

| wrapper | 위치 | 역할 |
|---|---|---|
| `service.upsert_employee_leave` | `service.py` | `_upsert_employee_leave_core` 와 byte-equivalent — log_callback 주입 가능 |
| `service.serialize_employee_leave` / `serialize_therapist_leave_alias` | `service.py` | `api.py` 응답 dict 와 byte-equivalent |
| `rules.is_leave_blocking` / `find_blocking_leave` | `rules.py` | `availability.py` 와 byte-equivalent |
| `rules.normalize_leave_type` / `normalize_leave_kind` | `rules.py` | `api.py` 인라인 fallback 패턴 정합 |
| `repository.list_leaves_for_date` | `repository.py` | `list_employee_leaves` query 패턴 정합 |
| `repository.get_leave_for_employee_date` | `repository.py` | `_upsert_employee_leave_core` filter 패턴 정합 |

## 6. 기존 API 응답 구조 유지 여부

✓ **100% 보존** — `app/routers/api.py` 무수정. 응답 dict / URL / 인증 정책 그대로.

## 7. 종일 / 오전반차 / 오후반차 차단 유지 여부

✓ **유지** — 본 19-5 가 *기존 규칙을 변경하지 않음*. 백엔드 차단 코드 *신설 ⊥*
(사용자 지시문 정합). `xfail` 4건 (test_therapist_leave.py — 백엔드 미구현) 그대로.

## 8. 휴무 표시 ↔ 예약 차단 ↔ 도메인 규칙 정합 여부

✓ **3 경로 정합** — 19-3 calendar / 19-4 availability / 19-5 leaves.rules 의 LEAVE_TYPE
상수 셋 + 반차 12:00 기준이 동일. contract 테스트가 회귀 보호 (4 테스트).

## 9. availability 연결 영향 여부

✓ **무수정** — `app/modules/appointments/availability.py` 본체 변경 ⊥. leaves.rules 는
*동등 helper* (byte-equivalent) — contract 테스트가 동등성 검증 (parametrize 14 + 정합 4).
19-4 availability 79 tests 회귀 0.

## 10. 개인정보 / 운영 DB / 외부 API 보호 결과

### 10-1. 개인정보 (PII) 보호

✓ **무영향** — leaves helper 는 환자 PII 미참조 (employee_id / 날짜 / leave_type /
leave_kind / memo 만 사용).

### 10-2. 운영 DB 보호

✓ **100% 보호** — `scripts/check_db_path.py` exit 0. repository / service 의 DB 세션은
*호출자 주입* — 운영 DB 직접 open ⊥. `tests/conftest.py` 4단계 격리.

### 10-3. 외부 API 호출

✓ **0건** — `test_rules_helpers_do_not_invoke_provider_or_db` 통과. `_block_sdk_modules`
자동 활성.

## 11. 순환참조 위험 여부

✓ **0건** — D-4 단방향 경계 검증 통과 (ast 기반):

| 모듈 | 의존 방향 |
|---|---|
| `leaves.rules` | `datetime` + `typing` 만 (외부 표준 라이브러리) |
| `leaves.repository` | top-level import 부재 — `app.models` 는 함수 안 lazy import |
| `leaves.service` | `app.modules.leaves.rules` (단방향) — `app.routers` / `fastapi` ⊥ |
| `leaves.__init__` | 없음 (빈 facade) |

→ **rules.py 가 ORM/DB/services/routers/sqlalchemy/fastapi/다른 modules 미참조** —
strict pure helper. **repository.py 는 `app.models` 를 lazy import** — top-level 부재.
**service.py 는 `app.routers` 미참조**.

## 12. 주석 / 문서화 적용 내용

### 12-1. 카테고리별 주석 카운트

| 카테고리 | 카운트 | 위치 |
|---|---|---|
| `# COMPAT:` | 다수 | __init__ + rules + repository + service docstring + helper docstring |
| `# SAFETY:` | 4 | __init__ + rules + repository + service docstring |
| `# NOTE:` | 다수 | rules / service helper docstring (반차 12:00 기준 / log_callback / commit 호출자 책임) |
| `# RISK:` | 2 | __init__ + rules docstring (단일 진실원천 / 19-9 통합) |
| `TODO(19-x)` | 0 | (해당 없음 — 모든 후속 작업이 19-9 시점 명시) |

### 12-2. docstring

| 파일 | docstring 정책 |
|---|---|
| `__init__.py` | 패키지 docstring (4 카테고리 — COMPAT / SAFETY / NOTE / RISK) |
| `rules.py` | 모듈 docstring + 7 helper docstring (모두 COMPAT 명시) |
| `repository.py` | 모듈 docstring + 4 helper docstring (COMPAT 명시) |
| `service.py` | 모듈 docstring + 3 helper docstring (COMPAT/SAFETY/NOTE 명시) |
| `tests/test_19_5_leaves.py` | 모듈 docstring + per-test docstring |

## 13. 생성한 리포트 파일

| 파일 | 역할 |
|---|---|
| `reports/refactor/19-5_test_report.md` | 본 세션 영구 보존본 |
| `reports/refactor/19-5_fix_summary.md` | 본 세션 영구 보존본 (이 파일) |
| `reports/refactor/19-5_codex_review_request.md` | 본 세션 영구 보존본 |
| `reports/refactor/latest_test_report.md` | 19-5 덮어쓰기 |
| `reports/refactor/latest_fix_summary.md` | 19-5 덮어쓰기 |
| `reports/refactor/latest_codex_review_request.md` | 19-5 덮어쓰기 |

## 14. 남은 위험 요소

| # | 위험 | 분류 | 해결 시점 |
|---|---|---|---|
| 1 | 19-5 helpers 미채택 (라우터 + AI action_leave) | 의도 (사용자 명시) | 19-9 |
| 2 | `_upsert_employee_leave_core` 두 사본 (api.py + leaves.service) 공존 | 알려진 — 19-9 통합 | 19-9 |
| 3 | LEAVE_TYPE / `is_leave_blocking` 두 사본 (availability + leaves.rules) 공존 | 알려진 — 19-9 통합 후보 | 19-9 |
| 4 | xfail 7건 + skip 1건 (도수 중복 / 휴무 차단 백엔드 미구현) 그대로 | 의도 (19-4 / 19-5 모두 보존) | 별도 결정 |

## 15. Codex 검증으로 넘겨도 되는지 자체 판단

**yes — Codex 검증으로 넘길 준비 완료**.

근거:
1. 5회 루프 1회차 통과 (ruff 자동 fix 1회 — 코드 동작 변경 0).
2. 19-4 baseline (731/1/7) 회귀 0 — 신규 +62 만 추가 (총 793).
3. ruff / check_db_path / PyInstaller 93 tests 모두 통과.
4. 19-5 54 contract + 기존 leaves/availability/AI action_leave 153 tests 모두 통과.
5. 휴무 표시 ↔ 예약 차단 ↔ 도메인 규칙 정합 (LEAVE_TYPE 셋 + 반차 12:00 기준).
6. AI action_leave 흐름 그대로 — `_do_upsert` 의 import 경로 보존.
7. 라우터 / 서비스 본체 무수정 — 응답 dict / URL / 인증 정책 100% 보존.
8. 운영 DB 미접근 + 외부 API 호출 0 + PII 미참조.
9. modules.leaves 단방향 경계 (D-4) 검증 통과 (ast 기반).
10. 사용자 명시 14 금지 항목 모두 준수.
