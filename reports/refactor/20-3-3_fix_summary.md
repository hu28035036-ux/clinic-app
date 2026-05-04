# 20-3-3 F-1 (c) 변경 요약

## 변경 파일 목록

### 신규 (6개)

| 파일 | 줄 수 |
|---|---:|
| `app/migrations/m016_doctors_table.py` | 49 (인덱스 보강) |
| `app/modules/doctors/__init__.py` | 28 |
| `app/modules/doctors/schemas.py` | 36 (DoctorIn + DOCTOR_RESPONSE_KEYS) |
| `app/modules/doctors/service.py` | 32 (serialize_doctor / serialize_doctors) |
| `app/modules/doctors/router.py` | 102 (GET/POST/PUT/DELETE /api/doctors) |
| `tests/test_20_3_3_doctors.py` | 143 (17 cases) |

### 수정 (4개)

| 파일 | diff | 의도 |
|---|---:|---|
| `app/models/models.py` | +18 | Doctor ORM 모델 (8 컬럼) |
| `app/main.py` | +2 | doctors_router include |
| `dosu_clinic.spec` | +7 | hidden_imports 4개 |
| `tests/test_pyinstaller_hidden_imports.py` | +5 | EXPECTED 4개 |
| `tests/test_19_8_therapists.py` | ~24 | 부재 단언 → 신설 단언 갱신 |

## 사용자 §5-7 (c) 결정 정합

- (c) 가벼운 의사만 — Doctor 단일 테이블만 신설.
- Department / Room / DoctorSchedule / Patient.doctor_id 모두 **부재** (테스트로 명시).
- 기존 Employee.role="doctor" / Treatment.role="doctor" 분기 보존 — *별개 도메인*.
- F-15 가드 강화 = 후속 (현재 가드 유지).

## 신설 endpoint

- `GET /api/doctors?active_only={bool}` — 의사 목록 (기본 활성만)
- `POST /api/doctors` — 의사 생성 (require_admin)
- `PUT /api/doctors/{did}` — 의사 수정 (require_admin)
- `DELETE /api/doctors/{did}` — 의사 삭제 (require_admin)

응답 8키: `id / name / specialty / license_no / color / active / sort_order / created_at`

## 호환성

- 20-3-2 baseline 1748 → 20-3-3 baseline **1773** (+25, 회귀 0)
- `Employee.role="doctor"` (도수치료 내부 의료직군) 보존 — *Doctor 별도 테이블과 별개*
- `Treatment.role="doctor"` 분기 보존
- 33+ 응답 key + main.html JS / FullCalendar 무수정
- m001~m015 변경 0, m016 신설만

## 19-8 contract 갱신

19-8 시점 `test_no_doctors_module_created` / `test_no_doctor_specific_endpoint_added` 부재 단언이 본 20-3-3 도입으로 깨짐 → 갱신:
- `test_no_medical_staff_module_created` (doctors 신설 + medical_staff 부재 단언)
- `test_doctors_endpoint_added_after_20_3_3` (200 응답 단언)

## 5회 루프

1회차 코드 + ruff + 17 cases passed
2회차 19-8 부재 단언 fail (2건) → doctors 도입 정합으로 갱신 → 1773 passed

총 2회 루프.
