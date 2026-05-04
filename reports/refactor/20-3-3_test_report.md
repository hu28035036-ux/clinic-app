# 20-3-3 F-1 (c) 가벼운 의사만 — 테스트 리포트

## 환경

- 직전 commit: `dad8bc7` (20-3-2 F-11 권한)

## 결과

| 검증 | 결과 |
|---|---|
| ruff | All checks passed (1 autofix) |
| check_db_path | exit 0 |
| `pytest test_20_3_3_doctors.py -v` | **17 passed** in 0.12s |
| `pytest test_pyinstaller_hidden_imports.py -q` | **219 passed** (신설 4 모듈 +8 cases) |
| `pytest tests -q` 전체 | **1773 passed / 1 skipped / 10 xfailed** in 14.32s |

### baseline 비교

| 시점 | passed | 증가 |
|---|---:|---:|
| 20-3-2 baseline | 1748 | — |
| 20-3-3 (본 세션) | **1773** | **+25** |

증가 25 = test_20_3_3_doctors.py 17 + PyInstaller 신설 4 × 2 = 8 = 25.

## 자동 테스트 확인

- Doctor 모델 (8 컬럼) + Department / Room / DoctorSchedule / Patient.doctor_id 부재 (6 cases)
- DOCTOR_RESPONSE_KEYS frozenset + serialize_doctor 8키 (2 cases)
- /api/doctors GET (public) + POST/PUT/DELETE (require_admin) (4 cases)
- Employee.role="doctor" 보존 + 별개 도메인 + Treatment.role="doctor" 보존 (3 cases)
- license_no / specialty nullable (PII 비저장 정책 정합) (2 cases)
- 신설 4 모듈 PyInstaller 등록 + import (8 cases)

## TestClient / API 호출

- GET /api/doctors → 200 + 빈 list (시드 0)
- POST/PUT/DELETE /api/doctors → 401/403 (인증 없이)

## 영향 없음

- 19-C §A 예약 / §B 휴무 / §C 치료항목 / §D 환자 / §G SMS / §H 통계 / §K Health: 영향 0.
- m001~m015 변경 0, m016 신설.
- main.html JS / FullCalendar 무수정.
- 기존 `Employee.role="doctor"` 분기 / Treatment.role="doctor" 분기 보존.

## 19-8 contract 갱신

- `test_no_doctors_module_created` → `test_no_medical_staff_module_created` (doctors 신설 / medical_staff 부재 단언으로 갱신)
- `test_no_doctor_specific_endpoint_added` → `test_doctors_endpoint_added_after_20_3_3` (200 응답 단언)

## 보안

- 운영 DB: 없음
- 외부 API: 없음
- 실제 문자 발송: 없음
- PII / API key 원문 노출: 없음 (audit detail = name 만, license_no / specialty 비저장)

## 수동 확인 필요

- 운영 환경에서 의사 등록 흐름 — 본 v1 백엔드만 (UI 후속).
- 의사 정보를 캘린더 / 환자 카드에 표시 — 후속 분할.
- F-15 가드 강화 (DB 근거 기반 검증) — 후속 (현재 가드 유지).

## 결론

다음: **20-3-4 F-2 반복 예약 진입 전 사용자 §6-6 결정**.
