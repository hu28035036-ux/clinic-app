# 19-3 calendar / schedule_view 표시용 view-model 분리 — 변경 요약

> 19-3 = **세 번째 실제 코드 리팩토링 세션**. `app/modules/calendar/` 후보 구조 신설 +
> `view_models.py` 표시용 순수 helper 추가.
> 5회 루프 1회차 통과 (648 passed) — 19-2 baseline 회귀 0.

## 0. 메타

- 세션 이름: **19-3 calendar / schedule_view 표시용 view-model 분리**
- 검증일: 2026-05-03
- 시작 HEAD: 19-2 r1 (settings/feature_flags/health 경계 정리 — Codex 검증 통과)
- 직전 19-2 Codex: pass — yes 19-3 진입 가능

## 1. 변경 파일 목록

### 신규 (3개) — `app/modules/calendar/` + 19-3 contract test

| 파일 | 라인 수 | 종류 | 책임 |
|---|---|---|---|
| `app/modules/calendar/__init__.py` | 38 | 신규 | calendar 패키지 facade docstring + COMPAT/SAFETY/NOTE/RISK 주석 |
| `app/modules/calendar/view_models.py` | **288** | 신규 helper | 표시용 순수 helper 11개 + 색상/opacity/라벨 상수 7개 |
| `tests/test_19_3_calendar_view_model.py` | **373** | 신규 contract | 51 테스트 (status_to_opacity / therapist_color / lighten_hex / appointment_to_calendar_event 회귀 + employee/leave view + 단방향 경계 + 외부 API 0 + PII 보존) |

### 수정 (2개) — spec / PyInstaller 검증

| 파일 | 변경 | 이유 |
|---|---|---|
| `dosu_clinic.spec` | **+5 lines** | 19-3 modules 2개 (`app.modules.calendar`, `app.modules.calendar.view_models`) hidden imports 추가 |
| `tests/test_pyinstaller_hidden_imports.py` | **+3 lines** | `EXPECTED_19_X_MODULES_MODULES` 4 → 6 (calendar 2 추가) |

### 무수정 (회귀 보호) — 19-3 절대 금지 범위 정합

`app/routers/api.py` (`_serialize_appointment` / `_serialize_employee` / `_lighten_hex` /
appointment CRUD / leave CRUD 등 모두 무수정), `app/routers/ai.py`, `app/services/ai/**`,
`app/services/auth.py`, `app/config.py`, `app/database.py`, `app/models/**`,
`app/migrations/m001~m013.py`, `app/templates/**` (main.html 7331줄 무수정),
`app/static/**`, `requirements*.txt`, `pyproject.toml`, `tests/conftest.py`,
`tests/harness/**`, 기존 모든 비-19-3 테스트.

## 2. 본 세션 의도 / 이유

### 의도

19-P-2 §2-2 의 calendar / schedule_view 후보 자리를 *최소 범위* 로 신설.
표시용 데이터 조립 책임 (FullCalendar event / 미니캘린더 / 금일예약환자 / 치료사 색상 /
휴무자 표시) 을 *순수 helper* 로 추출. 19-9 appointments 본체 분리 세션이 채택할 수 있는
*facade* 만 마련.

### 이유

1. **사용자 명시 "예약 저장/수정/삭제 로직 변경 ⊥" + "기존 endpoint 응답 key 변경 ⊥"**:
   `app/routers/api.py` 의 모든 핸들러 + `_serialize_appointment` / `_serialize_employee` /
   `_lighten_hex` 본체 무수정. modules.calendar 는 *동등 helper* 만 정의 (대체 ⊥).
2. **사용자 명시 "UI 디자인 변경 ⊥"**: `app/templates/main.html` (7331줄) +
   `app/static/css/app.css` 무수정. 인라인 JS 의 FullCalendar / Alpine 로직 무수정.
3. **사용자 명시 "표시용 view model 분리"**: 색상 / opacity / 상태 라벨 / 휴무 라벨 / 시간
   비교를 *순수 함수* 로 분리. ORM / DB / SQLAlchemy import ⊥.
4. **사용자 명시 "예약 가능 여부 판단은 19-4 / 휴무 규칙 자체는 19-5 / appointments 본체 분리는
   후속"**: 본 19-3 은 *표시* 만. `_check_lunch_block` / `_upsert_employee_leave_core` /
   appointment CRUD 무수정.
5. **PyInstaller 빌드 안전성**: spec 에 19-3 modules 2개 추가 + 검증 12 tests 추가 (77 → 89).

## 3. 새로 만든 modules.calendar 구조

```
app/modules/calendar/
├── __init__.py                 (38 lines, calendar 패키지 facade + 4 comment 카테고리)
└── view_models.py              (288 lines, 11 helper + 7 상수)
    ├── 색상 상수 (3): UNASSIGNED_THERAPIST_COLOR / UNASSIGNED_COLUMN_COLOR / DEFAULT_EVENT_TEXT_COLOR
    ├── opacity (3): STATUS_OPACITY / DEFAULT_OPACITY / status_to_opacity()
    ├── 색상 helper (2): therapist_color() / lighten_hex()
    ├── 휴무 라벨 (4): LEAVE_TYPE_LABELS / LEAVE_KIND_LABELS / leave_type_label() / leave_kind_label()
    ├── 상태 라벨 (4): STATUS_DISPLAY_LABELS / STATUS_CSS_CLASSES / status_to_label() / status_to_css_class()
    ├── 시간 비교 (1): is_past_appointment()
    └── view-model 조립 (3): appointment_to_calendar_event() / employee_to_resource_view() / leave_to_display()
```

## 4. 실제 이동한 표시용 로직

**0 줄** — 본 19-3 시점에 *실제 본체 이동 0*. 모두 facade / 신규 helper.

| api.py 위치 | 이동? | 비고 |
|---|---|---|
| `_serialize_appointment` (line 186~219) | ✗ | 본체 그대로. `appointment_to_calendar_event` 는 *동등 helper* (대체 ⊥). |
| `_serialize_employee` (line 169~176) | ✗ | 본체 그대로. `employee_to_resource_view` 는 *3키 부분 helper*. |
| `_lighten_hex` (line 4316) / `_lighten_hex_inner` (line 5115) | ✗ | 본체 그대로. `lighten_hex` 는 *byte-equivalent helper*. |
| `list_employee_leaves` 응답 dict (line 1088~1095) | ✗ | 본체 그대로. `leave_to_display(include_therapist_alias=False)` 는 동등. |
| `list_therapist_leaves_alias` 응답 dict (line 1191~1199) | ✗ | 본체 그대로. `leave_to_display(include_therapist_alias=True)` 는 동등. |
| `opacity = {...}.get(a.status, 1.0)` 인라인 (line 189) | ✗ | 본체 그대로. `status_to_opacity` 는 동등. |
| 색상 인라인 `"#9CA3AF"` (line 188 외 5곳) | ✗ | 본체 그대로. `UNASSIGNED_THERAPIST_COLOR` 상수 + `therapist_color` helper 로 미래 채택. |

## 5. 유지한 compatibility wrapper

| wrapper | 위치 | 역할 |
|---|---|---|
| `appointment_to_calendar_event` | `view_models.py` | `_serialize_appointment` 와 9 top-level + 16 extendedProps 키 byte-equivalent |
| `employee_to_resource_view` | `view_models.py` | `_serialize_employee` 의 색상 표시용 3키 부분 |
| `leave_to_display(include_therapist_alias=False)` | `view_models.py` | `list_employee_leaves` 응답 dict 6키 정합 |
| `leave_to_display(include_therapist_alias=True)` | `view_models.py` | `list_therapist_leaves_alias` 응답 dict 7키 (alias) 정합 |
| `lighten_hex` | `view_models.py` | `_lighten_hex` (api.py:4316) 와 byte-equivalent — 잘못된 입력 fallback `"FFFFFF"` 동일 |
| `therapist_color` | `view_models.py` | `t.color or "#9CA3AF"` 인라인 패턴 정합 |
| `status_to_opacity` | `view_models.py` | `{...}.get(a.status, 1.0)` 인라인 dict 정합 |

## 6. 기존 API 응답 구조 유지 여부

✓ **100% 보존** — `app/routers/api.py` 무수정.

| URL | 응답 키 | 보존 |
|---|---|---|
| `GET /api/appointments` (FullCalendar event 9 top + 16 extendedProps) | `id / start / end / color / textColor / extendedProps + 16개` | ✓ |
| `GET /api/employee-leaves` (6키) | `id / employee_id / leave_date / leave_type / leave_kind / memo` | ✓ |
| `GET /api/therapist-leaves` (7키 alias) | `id / therapist_id / employee_id / leave_date / leave_type / leave_kind / memo` | ✓ (이중 키 보존) |
| `GET /api/employees` / `/api/therapists` (10키) | (전체 그대로) | ✓ |

## 7. 기존 캘린더 / 미니캘린더 / 금일예약환자 표시 유지 여부

✓ **100% 유지** — UI / FullCalendar / Alpine JS 무수정.

| 표시 영역 | 데이터 소스 | 본 19-3 영향 |
|---|---|---|
| 월/주/일 캘린더 | `GET /api/appointments` 의 FullCalendar event | 영향 ⊥ — 라우터 무수정 |
| 미니캘린더 | `GET /api/appointments` (월간 조회) | 영향 ⊥ |
| 금일예약환자 (today-items) | `GET /api/appointments?start=YYYY-MM-DDT00:00:00&end=YYYY-MM-DDT23:59:59` (main.html:2161) | 영향 ⊥ |
| 치료사별 색상 표시 | `GET /api/employees` / `/api/therapists` 의 `color` | 영향 ⊥ — 색상 fallback 정책 정합 |
| 휴무자 표시 | `GET /api/employee-leaves` / `/api/therapist-leaves` | 영향 ⊥ |

## 8. 예약 저장 / 수정 / 삭제 로직 미변경 검증

✓ **무수정**:

| 영역 | 본 19-3 영향 |
|---|---|
| `POST /api/appointments` | ⊥ — 라우터 무수정 |
| `PUT /api/appointments/{aid}` | ⊥ |
| `DELETE /api/appointments/{aid}` | ⊥ |
| `POST /api/appointments/{aid}/assign` | ⊥ |
| `POST /api/appointments/{aid}/split-code` | ⊥ |
| `POST /api/appointments/{aid}/approve` / `revert-approve` | ⊥ |
| `POST /api/appointments/{aid}/cancel` | ⊥ |
| `_check_lunch_block` (api.py:64~107) | ⊥ — 19-4 availability 분리 시점 |
| `_check_version` / `_bump_version` (낙관적 락) | ⊥ |
| `Appointment.version` 컬럼 | ⊥ |

## 9. 휴무 차단 규칙 미변경 검증

✓ **무수정**:

| 영역 | 본 19-3 영향 |
|---|---|
| `_upsert_employee_leave_core` (api.py:1098) | ⊥ — 19-5 leaves 분리 시점 |
| `POST /api/employee-leaves` / `bulk-set` / `DELETE` | ⊥ |
| `EmployeeLeave` ORM 컬럼 / `(employee_id, leave_date)` UNIQUE / `leave_kind` / `leave_type` | ⊥ |
| AI `action_leave` 의 parse / preview / execute 흐름 | ⊥ |
| `xfail` 4건 (test_therapist_leave.py — 휴무 차단 백엔드 미구현) | 그대로 — 19-4/19-5 정방향 전환 |

## 10. 개인정보 / 운영 DB / 외부 API 보호 결과

### 10-1. 개인정보 (PII) 보호

✓ **기존 정책 그대로 유지**:

| 영역 | 정책 | 검증 |
|---|---|---|
| `extendedProps` 안의 patient_name / phone / birth_date / memo | 기존 동작 보존 — 19-3 helper 가 마스킹 변경 ⊥ | `test_extended_props_preserves_existing_pii_fields_unchanged` |
| 로그 / audit_log 에 PII 원문 | 부재 (기존 정책 — `pii.scan` + sha256 정합) | 기존 회귀 |
| AI 컨텍스트 / RAG 입력 PII | 영향 ⊥ — 본 19-3 무관 |

### 10-2. 운영 DB 보호

✓ **100% 보호** — `scripts/check_db_path.py` exit 0 + helper 안에서 DB 세션 부재.

### 10-3. 외부 API 호출

✓ **0건** — view_model helper tripwire 통과 (`test_view_model_helpers_do_not_invoke_provider_or_sdk`).

## 11. 순환참조 위험 여부

✓ **0건** — D-4 단방향 경계 검증 통과:

| 모듈 | 의존 방향 | 검증 |
|---|---|---|
| `app.modules.calendar.view_models` | (외부) `typing` 만 — `app.models` / `app.services` / `app.routers` / `app.database` / `sqlalchemy` / `app.modules.settings` / `app.modules.health` ⊥ | `test_calendar_view_models_does_not_import_models_or_db` |
| `app.modules.calendar.__init__` | 없음 — 빈 facade | `test_calendar_package_init_does_not_import_models_or_db` |

## 12. 주석 / 문서화 적용 내용

### 12-1. 카테고리별 주석 카운트 (실측)

| 카테고리 | 카운트 | 주요 위치 |
|---|---|---|
| `# COMPAT:` | 11 | calendar/__init__ (응답 키 보존) / view_models (api.py 인라인 정합 / dict literal 정합 / alias / fallback) |
| `# SAFETY:` | 4 | calendar/__init__ (PII 보존) / view_models (PII 보존 / extended_props copy / lighten_hex fallback) |
| `# NOTE:` | 6 | calendar/__init__ (UI 분리 후속) / view_models (저장 vs 표시 분리 이유 / 시간 비교 / 알 수 없는 값 fallback / wire 시점 / 19-9 채택) |
| `# RISK:` | 2 | calendar/__init__ (FullCalendar event 키 변경 위험) / view_models (FullCalendar event 회귀) |
| `# TODO(post-19-P)` | 1 | UI 분리 후속 — main.html JS 외부 분리 별도 세션 |

### 12-2. docstring

| 파일 | docstring 정책 |
|---|---|
| `app/modules/calendar/__init__.py` | 패키지 docstring (역할 + 8 분리 대상 + COMPAT/SAFETY/RISK) |
| `app/modules/calendar/view_models.py` | 모듈 docstring + 11 함수 docstring (모두 COMPAT/SAFETY/NOTE/RISK 명시) |
| `tests/test_19_3_calendar_view_model.py` | 모듈 docstring + per-test docstring |

## 13. 생성한 리포트 파일

| 파일 | 역할 |
|---|---|
| `reports/refactor/19-3_test_report.md` | 본 세션 영구 보존본 |
| `reports/refactor/19-3_fix_summary.md` | 본 세션 영구 보존본 (이 파일) |
| `reports/refactor/19-3_codex_review_request.md` | 본 세션 영구 보존본 (Codex 검증 요청서) |
| `reports/refactor/latest_test_report.md` | 19-3 덮어쓰기 |
| `reports/refactor/latest_fix_summary.md` | 19-3 덮어쓰기 |
| `reports/refactor/latest_codex_review_request.md` | 19-3 덮어쓰기 |

## 14. 남은 위험 요소

| # | 위험 | 분류 | 해결 시점 |
|---|---|---|---|
| 1 | 19-3 view_model 미채택 — 라우터에서 본 helper 를 import 안 함 | 의도 (사용자 명시 "라우터 무수정") | 19-9 appointments 본체 분리 시점에 점진적 채택 |
| 2 | `_serialize_appointment` 본체와 `appointment_to_calendar_event` 가 두 경로 공존 | 알려진 — 19-9 시점에 라우터가 view_model 호출로 위임 | 19-9 |
| 3 | `_lighten_hex` 본체 + `_lighten_hex_inner` 두 사본 (api.py:4316 + 5115) 와 `lighten_hex` 가 세 경로 공존 | 알려진 — 19-7 / 19-11 export 분리 시점에 통합 | 19-7 / 19-11 |
| 4 | UI 분리 (main.html JS 외부화 / FullCalendar 이벤트 핸들러 분리) | 후속 분류 | post-19-P |
| 5 | `xfail` 4건 (휴무 차단 백엔드 미구현) | 그대로 — 19-4/19-5 정방향 전환 | 19-4/19-5 |

## 15. Codex 검증으로 넘겨도 되는지 자체 판단

**yes — Codex 검증으로 넘길 준비 완료**.

근거:
1. 5회 루프 1회차 통과 — 땜질 / ruff 자동 fix / 추가 가설 ⊥.
2. 19-2 baseline (585/1/7) 회귀 0 — 신규 +63 만 추가 (총 648).
3. ruff / check_db_path / PyInstaller 89 tests 모두 통과.
4. 19-3 51 contract 테스트 + 기존 calendar/appointment/leave 30 tests 모두 통과.
5. 운영 DB 미접근 + 외부 API 호출 0 + PII 보존 (마스킹 변경 ⊥).
6. core / modules.calendar 단방향 경계 (D-4) 검증 통과.
7. 기존 API 응답 dict / URL / 인증 정책 100% 보존.
8. 예약 저장 / 수정 / 삭제 로직 ⊥ + 휴무 차단 규칙 ⊥.
9. UI 디자인 ⊥ (main.html / app.css 무수정).
10. 사용자 명시 13 금지 항목 모두 준수.
