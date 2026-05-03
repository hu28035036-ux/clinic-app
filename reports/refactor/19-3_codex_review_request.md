# 19-3 calendar / schedule_view 표시용 view-model 분리 — Codex 검증 요청서

> 사용자 양식 17개 항목 정합. Codex 가 본 문서를 시작점으로 쓰되 **실제 diff /
> 변경 파일 / 결과 / 로그를 독립적으로 확인** 한다.

---

## 1. 세션 이름

**19-3 calendar / schedule_view 표시용 view-model 분리**.

## 2. 이번 세션 목표

`app/modules/calendar/` 후보 구조 신설 + `view_models.py` 표시용 순수 helper 추가.
캘린더 / 미니캘린더 / 금일예약환자 / 치료사 색상 / 휴무자 표시 데이터 조립 책임을
*순수 helper* 로 분리. 기존 응답 키 / URL / 인증 / UI 100% 보존. 예약 저장/수정/삭제 /
휴무 차단 규칙 / availability 판단 모두 무수정.

## 3. 변경 파일 목록

### 신규 (3개)

| 파일 | 라인 수 | 종류 | 책임 |
|---|---|---|---|
| `app/modules/calendar/__init__.py` | 38 | 신규 | calendar 패키지 facade docstring |
| `app/modules/calendar/view_models.py` | 288 | 신규 helper | 표시용 순수 helper 11 + 색상/opacity/라벨 상수 7 |
| `tests/test_19_3_calendar_view_model.py` | 373 | 신규 contract | 51 테스트 (회귀 + 단방향 + 외부 API 0 + PII 보존) |

### 수정 (2개)

| 파일 | 변경 | 이유 |
|---|---|---|
| `dosu_clinic.spec` | +5 lines | 19-3 modules 2개 hidden imports 추가 |
| `tests/test_pyinstaller_hidden_imports.py` | +3 lines | `EXPECTED_19_X_MODULES_MODULES` 4 → 6 |

### 무수정 (절대 금지 범위 정합)

`app/routers/api.py`, `app/routers/ai.py`, `app/services/**`, `app/services/auth.py`, `app/config.py`,
`app/database.py`, `app/models/**`, `app/migrations/m001~m013.py`, `app/templates/**` (main.html
7331줄 무수정), `app/static/**`, `requirements*.txt`, `pyproject.toml`, `tests/conftest.py`,
`tests/harness/**`.

## 4. 실제 이동 / 분리한 표시용 로직

**0 줄 이동** — 본 19-3 시점에 *실제 본체 이동 0*. 모두 facade / 신규 helper.

| api.py 위치 | 이동? | 19-3 helper |
|---|---|---|
| `_serialize_appointment` (line 186) | ✗ | `appointment_to_calendar_event` (동등 helper) |
| `_serialize_employee` (line 169) | ✗ | `employee_to_resource_view` (3키 부분) |
| `_lighten_hex` (line 4316) | ✗ | `lighten_hex` (byte-equivalent) |
| `list_employee_leaves` 응답 dict | ✗ | `leave_to_display(include_therapist_alias=False)` |
| `list_therapist_leaves_alias` 응답 dict | ✗ | `leave_to_display(include_therapist_alias=True)` |
| `opacity = {...}.get(a.status, 1.0)` 인라인 | ✗ | `status_to_opacity` |
| `t.color or "#9CA3AF"` 인라인 (5곳) | ✗ | `therapist_color` + `UNASSIGNED_THERAPIST_COLOR` 상수 |

## 5. Compatibility wrapper 유지 여부

✓ **유지**. 7개 wrapper / facade 모두 *대체 ⊥*, *추가만*.

## 6. 수정 금지 범위 준수 여부

✓ **모두 준수**:

| 금지 항목 | 본 19-3 결과 |
|---|---|
| 예약 생성/수정/삭제 로직 변경 | ✗ — `app/routers/api.py` 무수정 |
| 휴무 차단 규칙 변경 | ✗ — `_upsert_employee_leave_core` / m011 무수정 |
| 치료항목/완료체크 로직 변경 | ✗ |
| 통계 집계 로직 변경 | ✗ |
| 문자/SMS 로직 변경 | ✗ |
| AI/RAG 로직 변경 | ✗ |
| DB schema 변경 | ✗ — m001~m013 무수정 |
| migration 생성 | ✗ |
| UI 디자인 변경 | ✗ — `templates/main.html`, `static/css/app.css` 무수정 |
| 기존 API 응답 key 변경 | ✗ — 33+ 키 셋 보존 |
| 하네스/테스트 약화 | ✗ — `conftest.py`, `harness/**` 무수정 |
| 운영 DB 접근 | ✗ |
| 외부 API 호출 | ✗ |
| `requirements.txt` / PyInstaller spec 불필요 수정 | ✗ — spec 은 2개 모듈 hidden imports 만 추가 |
| 기존 SMS AI / 휴무 AI 동작 변경 | ✗ |

## 7. 기존 API 응답 key 유지 여부

✓ **100% 보존**. `app/routers/api.py` 무수정.

| URL | 응답 키 | 보존 |
|---|---|---|
| `GET /api/appointments` (FullCalendar event) | `id / start / end / color / textColor / extendedProps` (9 top + 16 extendedProps) | ✓ |
| `GET /api/employee-leaves` (6키) | `id / employee_id / leave_date / leave_type / leave_kind / memo` | ✓ |
| `GET /api/therapist-leaves` (alias 7키) | `id / therapist_id / employee_id / leave_date / leave_type / leave_kind / memo` | ✓ (이중 키) |
| `GET /api/employees` / `/api/therapists` | (전체 그대로) | ✓ |

## 8. 예약 저장 / 수정 / 삭제 로직 변경 여부

✗ **변경 없음** — `app/routers/api.py` 의 모든 appointment CRUD 핸들러 무수정.

| 영역 | 본 19-3 영향 |
|---|---|
| `POST /api/appointments` 등 모든 CRUD | ⊥ |
| `_check_lunch_block` (api.py:64) | ⊥ — 19-4 availability 분리 시점 |
| `_check_version` / `_bump_version` (낙관적 락) | ⊥ |
| `Appointment.version` 컬럼 | ⊥ |

## 9. 휴무 차단 규칙 변경 여부

✗ **변경 없음** — `_upsert_employee_leave_core` (api.py:1098) 무수정.

| 영역 | 본 19-3 영향 |
|---|---|
| 휴무 CRUD 핸들러 | ⊥ — 19-5 leaves 분리 시점 |
| `EmployeeLeave` ORM / m011 UNIQUE | ⊥ |
| AI `action_leave` 흐름 | ⊥ |
| `xfail` 4건 (휴무 차단 백엔드 미구현) | 그대로 |

## 10. 개인정보 노출 여부

✓ **기존 정책 그대로 유지** — 본 19-3 helper 가 PII 마스킹 변경 ⊥.

| 영역 | 정책 |
|---|---|
| `extendedProps` 안의 patient_name / phone / birth_date / memo | 기존 동작 보존 — caller 가 책임. 19-3 helper 가 추가 / 제거 / 마스킹 변경 ⊥. |
| 로그 / audit_log 의 PII 원문 | 부재 (기존 정책) |
| `pii.scan` + sha256 마스킹 | 무수정 |
| AI 컨텍스트 / RAG 입력 PII | 영향 ⊥ |

회귀 보호: `test_extended_props_preserves_existing_pii_fields_unchanged` — view_model 이 PII
필드를 *그대로 통과* 시킴을 검증 (마스킹 추가 / 제거 / 누락 ⊥).

## 11. 운영 DB 보호 여부

✓ **100% 보호**.

| # | 검사 | 결과 |
|---|---|---|
| `scripts/check_db_path.py` exit 0 | ✓ |
| modules.calendar 안에서 DB 세션 직접 open | 0 (helper 는 primitives 또는 ORM attribute read) |
| view_models.py 가 SQLAlchemy import | ⊥ (`test_calendar_view_models_does_not_import_models_or_db`) |
| `tests/conftest.py` 4단계 격리 / `db_guard` | ✓ (648 passed 자동 검증) |

## 12. 외부 API 호출 여부

✓ **0건**.

| # | 검사 | 결과 |
|---|---|---|
| view_model helper 안에서 provider 호출 | 0 (`test_view_model_helpers_do_not_invoke_provider_or_sdk`) |
| view_model helper 안에서 SDK import | 0 |
| `_block_sdk_modules` 자동 활성 | ✓ |
| `local_only` 모드 호출 0 단언 (기존 회귀) | ✓ 4 passed |

## 13. 순환참조 위험 여부

✓ **0건** — D-4 단방향 경계 검증 통과:

| 모듈 | 의존 방향 | 검증 |
|---|---|---|
| `app.modules.calendar.view_models` | (외부) `typing` 만 | `test_calendar_view_models_does_not_import_models_or_db` |
| `app.modules.calendar.__init__` | 없음 (빈 facade) | `test_calendar_package_init_does_not_import_models_or_db` |

→ **core / modules.settings / modules.health / app.models / app.services / app.routers / sqlalchemy** 모두 미참조.

## 14. 주석 / 문서화 기준 적용 여부

✓ **모두 적용**:

| # | 기준 | 적용 |
|---|---|---|
| 1 | 새 파일 상단 docstring | calendar/__init__ + view_models 모두 docstring 보유 |
| 2 | 주요 helper 함수 docstring | 11 helper 모두 docstring 보유 (COMPAT/SAFETY/NOTE 명시) |
| 3 | 기존 API/UI 호환 wrapper 의 `COMPAT` 주석 | 11 위치 (api.py 인라인 정합 / dict literal 정합 / alias / fallback) |
| 4 | 개인정보 포함 표시 데이터 부분의 `SAFETY` 주석 | 4 위치 (calendar/__init__ + extended_props PII 보존 + dict copy + lighten_hex fallback) |
| 5 | 예약 저장 vs 표시 분리 이유의 `NOTE` 주석 | 6 위치 (저장-표시 분리 이유 / 시간 비교 / fallback / wire 시점 / 19-9 채택 / UI 후속) |
| 6 | 프론트 응답 key 변경 위험의 `RISK` 주석 | 2 위치 (FullCalendar event 키 변경 위험) |
| 7 | TODO(post-19-P) 형식 | 1 위치 (UI 분리 후속) |
| 8 | 의미 없는 모든 줄 주석 금지 | ✓ — `# COMPAT/SAFETY/NOTE/RISK/TODO` 만 사용 |
| 9 | 주석 작성 때문에 기능 동작 변경 금지 | ✓ — 본 19-3 의 모든 변경은 *주석 없이도 동일 결과* |

## 15. 실행한 테스트와 결과

| # | 명령 | 결과 |
|---|---|---|
| C-1 | `pytest tests -q` | **648 passed, 1 skipped, 7 xfailed, 27 warnings** (11.31초) |
| C-2 | `ruff check app tests scripts` | **All checks passed!** |
| C-3 | `scripts/check_db_path.py` | exit 0 |
| C-4 | `pytest tests/test_pyinstaller_hidden_imports.py -q` | **89 passed** |
| C-5 | `pytest tests/test_19_3_calendar_view_model.py -q` | **51 passed** |
| C-6 | `pytest tests/test_admin_ui_smoke.py tests/test_appointment_rules.py tests/test_therapist_leave.py tests/test_employee_leave_unique.py tests/test_employee_leave_kind.py -q` | **30 passed, 1 skipped, 7 xfailed** |

## 16. 실패 / 수정 루프 횟수

| 회차 | 실행 명령 | 결과 |
|---|---|---|
| 1 | C-1 ~ C-6 + ruff | **모두 통과** ✓ |

→ **5회 루프 1회차에 통과** (땜질 ⊥, ruff 자동 fix 0회, 추가 가설 ⊥).

## 17. 19-4 availability 예약 가능 여부 / 충돌 검사 분리로 넘어가도 되는지 판단 기준

**yes — 19-4 진입 가능**.

근거:
1. **5회 루프 1회차 통과** — 땜질 / 추가 수정 ⊥.
2. **19-2 baseline (585/1/7) 회귀 0** — 신규 +63 만 추가 (총 648).
3. **ruff / check_db_path / PyInstaller 89 tests 모두 통과**.
4. **19-3 51 contract 테스트 + 기존 calendar/appointment/leave 30 tests 모두 통과**.
5. **운영 DB 미접근 + 외부 API 호출 0 + PII 마스킹 정책 보존**.
6. **core / modules.calendar 단방향 경계 (D-4) 검증 통과**.
7. **기존 API 응답 dict / URL / 인증 정책 100% 보존**.
8. **예약 저장 / 수정 / 삭제 로직 ⊥ + 휴무 차단 규칙 ⊥**.
9. **UI 디자인 ⊥** (main.html 7331줄 / app.css 무수정).
10. **사용자 명시 13 금지 항목 모두 준수**.

남은 위험 / 사용자 결정 필요 (19-4 진입 직전):
- (1) 19-3 view_model 미채택 (의도) — 19-9 appointments 본체 분리 시점에 점진적 채택.
- (2) `_serialize_appointment` 본체 + `appointment_to_calendar_event` 두 경로 공존 — 19-9 시점 통합.
- (3) `_lighten_hex` 본체 (api.py:4316) + `_lighten_hex_inner` (api.py:5115) + `lighten_hex` 세 사본 공존 — 19-7 / 19-11 export 분리 시점 통합.
- (4) UI 분리 (main.html JS 외부화) — post-19-P 후속.

다음 세션:
- **19-4 availability 예약 가능 여부 / 충돌 검사 분리** — `_lunch_window` / `_check_lunch_block` (api.py:64~107) 추출 + 휴무 / 도수 중복 백엔드 차단 코드 신설 + xfail 7 + skip 1 정방향 전환.

---

## Codex 가 집중 검토할 파일

1. `app/modules/calendar/__init__.py` — calendar 패키지 facade docstring + 4 comment 카테고리.
2. `app/modules/calendar/view_models.py` — 11 helper + 7 상수. `_serialize_appointment` / `_serialize_employee` / `_lighten_hex` 와 byte-equivalent 검증 필수.
3. `tests/test_19_3_calendar_view_model.py` — 51 contract 테스트 검증 범위 적정성.
4. `dosu_clinic.spec` 19-3 추가 5줄 + `tests/test_pyinstaller_hidden_imports.py` 3줄 — PyInstaller 빌드 안전성.

## Codex 가 반드시 확인할 체크리스트

1. **응답 키 100% 보존** — `app/routers/api.py` 무수정 + 회귀 테스트.
2. **PII 마스킹 정책 보존** — `extended_props` 안의 patient_name/phone/birth_date/memo 가 helper 통과 시 변경 ⊥.
3. **외부 API 호출 0** — view_model helper 안에서 provider/SDK 호출 ⊥.
4. **운영 DB 미접근** — `scripts/check_db_path.py` exit 0 + helper 안에서 DB 세션 부재.
5. **단방향 경계 (D-4)** — `app.modules.calendar.view_models` 가 ORM/DB/services/routers/sqlalchemy/다른 modules 미참조.
6. **PyInstaller 빌드 안전성** — 19-3 modules 2개 spec 등록 + 12 tests 통과.
7. **5회 루프 1회차 통과** — 땜질 / ruff 자동 fix ⊥.
8. **본체 이동 0 줄** — 라우터 / 서비스 본체 무수정. 모두 facade / 신규 helper.
9. **UI 무수정** — `app/templates/main.html` / `app/static/**` 무수정.
10. **예약 저장 / 휴무 규칙 / availability 무수정** — 19-4 / 19-5 / 19-9 분리 시점 그대로.

## 자체 판단

**yes — 19-4 진입 가능 (Codex 검증 통과 후)**.
