# 19-8 therapists 분리 — 변경 요약

## 세션 이름

`19-8_therapists_doctors_boundary` — 치료사 / 직원 도메인 후보 구조 정리 +
의사 / medical_staff 현재 기능 부재 문서화.

## 작업 목표 (한 문장)

`api.py:_serialize_employee` / `list_employees` / `list_therapists_alias` /
통계 ``id → name`` 매핑 / 도수치료 표 등 *치료사 관련 순수 로직* 을
`app/modules/therapists/` 후보 구조에 분리하고, 라우터 / DB schema / API
응답 key 는 *무수정* 으로 유지.

## 변경 파일 목록

| 파일 | 변경 종류 | 줄 수 |
|---|---|---:|
| `app/modules/therapists/__init__.py` | 신규 | 41 |
| `app/modules/therapists/rules.py` | 신규 | 211 |
| `app/modules/therapists/repository.py` | 신규 | 173 |
| `app/modules/therapists/service.py` | 신규 | 168 |
| `tests/test_19_8_therapists.py` | 신규 | 619 |
| `dosu_clinic.spec` | 수정 (+7) | — |
| `tests/test_pyinstaller_hidden_imports.py` | 수정 (+5) | — |

## 파일별 변경 요약

### `app/modules/therapists/__init__.py` (신규, 41줄)

- 패키지 docstring — 19-8 본 세션 범위 / 범위 외 / COMPAT / SAFETY / NOTE / RISK
  주석 + `TODO(후속 검토)` 마커 (doctors / medical_staff 분리 후보 표시).

### `app/modules/therapists/rules.py` (신규, 211줄)

순수 도메인 규칙 (DB / ORM 미참조).

- **상수 re-export** : `ROLE_DOCTOR` / `ROLE_THERAPIST` / `ROLES` —
  `app.models.constants` 의 단일 진실원천 `import`.
- **DEFAULT_THERAPIST_COLOR** : 19-3 `calendar.view_models.UNASSIGNED_THERAPIST_COLOR`
  를 *lazy import* 로 re-export (top-level circular import 회피).
- **역할 판정** :
  - `is_therapist_role(role)` / `is_doctor_role(role)` / `is_valid_role(role)`.
  - `normalize_role(role)` : None / 빈값 → `"therapist"`.
- **활성 / 권한 정규화** :
  - `is_active_employee(active)` / `can_handle_eswt(...)` / `can_handle_manual(...)`.
- **색상 fallback** : `therapist_color_or_default(color)` — 19-3 view_models 와 동등.
- **미배정 sentinel** : `UNASSIGNED_SENTINEL = "__none__"` / `UNASSIGNED_LABEL =
  "미배정"` + `is_unassigned(tid)` helper.

### `app/modules/therapists/repository.py` (신규, 173줄)

read-only `Employee` row 조회 helper (DB 세션 호출자 주입, lazy import).

- `list_all_employees(db, role=None, active=None)` — `api.py:list_employees` 의
  query 패턴 정합 (`sort_order, name` 정렬).
- `get_employee_by_id(db, employee_id)` — `db.get(Employee, eid)`.
- `list_therapists(db, active=None)` — `api.py:list_therapists_alias` 정합
  (`role=therapist`, `name` 단일 정렬).
- `list_doctors(db, active=None)` — `api.py:3525` 정합 (`role=doctor`).
- `list_therapists_for_manual_scheduler(db)` — `api.py:4364~4369` 정합
  (`role=therapist + active=True + can_manual=True`).
- `list_active_therapists(db)` — `api.py:3783~3786` 정합.
- `get_employees_by_ids(db, employee_ids)` — `api.py:1552` 의 `in_(...)` 정합
  (빈 리스트는 빈 결과 반환).
- `count_employees_by_role(db, role)` — `api.py:create_employee` 의 sort_order
  자동 계산 정합.

### `app/modules/therapists/service.py` (신규, 168줄)

직렬화 / 빌더 helper.

- `serialize_employee(employee)` — `api.py:_serialize_employee` 와
  byte-equivalent (10키 dict).
- `serialize_employees(employees)` — list comprehension.
- `build_employee_name_map(employees, *, include_unassigned=True)` —
  통계 `id → name` 매핑 + `"__none__" → "미배정"` 합산.
- `build_employee_color_map(employees, *, include_unassigned=True)` —
  `t.color or "#9CA3AF"` fallback.
- `build_therapist_resource_view(employee)` — 캘린더 resource view (3키 —
  id/name/color), 19-3 `calendar.view_models.employee_to_resource_view` 와 동등.
- `build_therapist_resource_views(employees)` — list 빌더.
- `next_sort_order_for_role(*, current_count_for_role)` — `count + 1`.

### `tests/test_19_8_therapists.py` (신규, 619줄)

78 cases — contract 검증.

1. ROLE 상수 / `app.models.constants` 정합.
2. 역할 판정 / normalize_role.
3. 색상 상수 19-3 정합.
4. `therapist_color_or_default` 19-3 byte-equivalent.
5. 활성 / 권한 정규화.
6. 미배정 sentinel.
7. repository 동작 (시드 fixture 사용 — 격리 DB).
8. `serialize_employee` byte-equivalent + API 응답 키 일치.
9. id → name / color 매핑.
10. resource view 19-3 정합.
11. `next_sort_order_for_role`.
12. 단방향 경계 (D-4) — `app.routers` 미참조 / SQLAlchemy 미참조 / lazy import.
13. doctors / medical_staff 부재 검증 (디렉토리 / 엔드포인트 / 기존 ?role=doctor 흐름).
14. 라우터 시그니처 무수정.
15. 기존 휴무 / treatment-meta 흐름 영향 없음.

### `dosu_clinic.spec` (수정, +7줄)

`hidden` 리스트에 19-8 신규 4개 모듈 등록:

```
'app.modules.therapists',
'app.modules.therapists.rules',
'app.modules.therapists.repository',
'app.modules.therapists.service',
```

### `tests/test_pyinstaller_hidden_imports.py` (수정, +5줄)

`EXPECTED_19_X_MODULES_MODULES` 에 위 4개 모듈 추가 — spec 등록 + 실제 import
가능성을 parametrize 로 검증 (8 cases 추가 = 4 in_spec + 4 importable).

## 의도 / 이유

- **단일 진실원천 분리** : `_serialize_employee` 의 10키 정합 로직, 통계
  ``id → name`` / ``id → color`` 매핑, 도수치료 표 / 캘린더 resource view 의
  ``t.color or "#9CA3AF"`` fallback 패턴이 `api.py` 안에 *중복 인라인* 으로
  존재 — 후속 19-9 (appointments service/repository 분리) 시점에 본 helper 가
  채택될 후보.
- **doctors / medical_staff 분리 ⊥** : 현재 진료과 / 진료실 / 오더 / 처방 /
  EMR 기능이 *부재* — 의사는 `Employee.role='doctor'` 로 같은 테이블 공유
  + `injection / cartilage` 치료항목의 `role='doctor'` 로만 다뤄짐.
  본 19-8 시점에는 *후속 검토* 로 명시 (rules.py 의 `TODO(후속 검토)` 마커).
- **라우터 / API 응답 무수정** : 19-7 패턴 정합 — `app/routers/api.py` 본체
  무수정, 본 helper 는 *byte-equivalent 후보* 로 19-9 채택 대기.
- **D-4 경계 보존** : `rules.py` 는 ORM / DB 미참조, `repository.py` /
  `service.py` 만 함수 안 lazy import 로 `app.models` 참조. `app.routers` 미참조.

## doctors / medical_staff 현재 기능 여부 확인 결과

| 기능 | 현재 코드 | 본 19-8 처리 |
|---|---|---|
| 의사 직원 등록 / 조회 / 비활성 | ✅ 존재 (`Employee.role='doctor'` + `/api/employees?role=doctor`) | rules / repository / service 가 *공통 직원 도메인* 으로 다룸 |
| 의사 항목 (`injection` / `cartilage`) | ✅ 존재 (Treatment.role='doctor') | 19-6 treatments 모듈 분리 시점 |
| 통계 `stats_by_therapist` 의 doctor 분기 | ✅ 존재 (`api.py:3525` `role == "doctor"`) | repository.list_doctors 로 query 패턴만 helper 화 |
| 진료과 / 진료실 | ❌ 부재 | TODO(후속 검토) — 본 세션 미구현 |
| 오더 / 처방 / EMR | ❌ 부재 | TODO(후속 검토) — 본 세션 미구현 |
| 진료 일정 / 의사별 휴무 분리 | ❌ 부재 (휴무는 EmployeeLeave 공유) | TODO(후속 검토) |

→ `app/modules/doctors/` 또는 `app/modules/medical_staff/` 디렉토리 *생성 ⊥*.
   `test_no_doctors_module_created` 가 부재를 검증.

## compatibility wrapper / 라우터 무수정

- `app/routers/api.py` 본체 *완전 무수정* — `_serialize_employee` /
  `list_employees` / `list_therapists_alias` / `_upsert_employee_leave_core` /
  통계 빌더 등 모든 핸들러 그대로 동작.
- `tests/test_19_8_therapists.py` 의 `test_*_router_signature_unchanged` 테스트가
  서명 무수정을 검증.
- 기존 `/api/employees` / `/api/therapists` / `/api/employee-leaves` /
  `/api/therapist-leaves` / `/api/treatment-meta` 엔드포인트의 응답 키 / 타입
  *완전 보존*.

## 수정 금지 범위 준수

| 금지 항목 | 준수 |
|---|---|
| 예약 생성/수정/삭제 흐름 변경 | ✅ 무수정 |
| 예약 API 응답 key 변경 | ✅ 무수정 |
| 휴무 규칙 변경 | ✅ 무수정 (19-5 leaves 그대로) |
| 치료항목/완료체크 로직 변경 | ✅ 무수정 (19-6 treatments 그대로) |
| 통계 집계 기준 변경 | ✅ 무수정 |
| 문자/SMS 로직 변경 | ✅ 무수정 |
| AI/RAG 로직 변경 | ✅ 무수정 |
| 의사/진료진 기능을 실제 기능처럼 구현 | ✅ 부재 확인 + TODO(후속 검토) 만 |
| DB schema 변경 | ✅ 무수정 |
| migration 생성 | ✅ 무수정 |
| UI 디자인 변경 | ✅ 무수정 |
| 운영 DB 접근 | ✅ 미접근 (`scripts/check_db_path.py` exit 0) |
| 외부 API 호출 | ✅ 미호출 |
| requirements.txt / spec 불필요 수정 | ✅ spec 은 19-8 hidden imports 추가만 |

## 자동 수정 루프 횟수

**0회** — 78 / 78 contract 1회차 통과. ruff I001 1건만 수동 수정 (테스트
파일의 import 정렬).

## 5회 실패 여부

**미해당** — 1회차 통과.

## 위반 / 우회 없음

- `pyproject.toml` per-file-ignores 무수정.
- 운영 DB 직접 open 없음.
- 외부 API 호출 없음.
- `app.routers` 본체 무수정.
- DB schema / migration 무수정.
