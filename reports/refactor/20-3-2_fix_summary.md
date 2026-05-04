# 20-3-2 F-11 변경 요약

## 변경 파일 목록

### 신규 (2개)

| 파일 | 줄 수 |
|---|---:|
| `app/migrations/m015_employee_permission_level.py` | 49 |
| `tests/test_20_3_2_permission_level.py` | 207 (13 cases) |

### 수정 (5개)

| 파일 | diff | 의도 |
|---|---:|---|
| `app/models/models.py` | +3 | Employee.permission_level Column |
| `app/models/schemas.py` | +9 | EmployeePermissionIn pydantic |
| `app/routers/api.py` | ~35 | _serialize_employee + EMPLOYEE_PERMISSION_LEVELS + /api/admin/employees/{eid}/permission |
| `app/modules/therapists/service.py` | +2 | serialize_employee 동기 |
| `tests/test_19_8_therapists.py` | +6 | 12키 contract 갱신 |

## 사용자 §4-6 권장값 정합

- (a) 3등급: staff / admin / super (viewer 미도입)
- (i) admin 별도 게이트 보존 — 기존 PBKDF2 / 5회 잠금 / 8h 세션 / require_admin 86 endpoint 무수정. 권한 등급 변경은 require_admin 권한 통과한 admin 만.
- (ii) viewer 미도입 — `EMPLOYEE_PERMISSION_LEVELS = ("staff", "admin", "super")` 상수에서 제외.

## 신설 endpoint

- `POST /api/admin/employees/{eid}/permission` — body `{"permission_level": "staff"|"admin"|"super"}`
  - require_admin 의존
  - EMPLOYEE_PERMISSION_LEVELS 외 값 → 400
  - audit("employee.permission_update", eid, f"level={...}")

## 호환성

- 20-3-1 baseline 1735 → 20-3-2 baseline **1748** (+13, 회귀 0)
- 기존 Employee `role` 컬럼 (therapist / doctor) 보존 — *직군 분기*. permission_level 은 *권한 등급* (별개).
- 기존 33+ 응답 key + 기존 11 employee 키 보존 (permission_level 추가 — 12키)
- 기존 admin 로그인 / PBKDF2 / 5회 잠금 / 8h 세션 / require_admin 흐름 무수정
- m001~m014 변경 0, m015 신설만, main.html JS / FullCalendar 무수정

## 5회 루프

1회차 코드 + ruff (3 autofix) + 13 cases
2회차 require_admin import 위치 정정 (services.auth → routers.api) + 19-8 contract 갱신 (permission_level)
3회차 전체 회귀 1748 passed

총 3회 루프 안에 통과.
