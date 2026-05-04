# 20-3-3 Codex 검증 요청서

## 1. 세션 이름

`20-3-3_doctors_light` — F-1 (c) 가벼운 의사만 (Doctor 별도 테이블 + /api/doctors CRUD).

## 2. 작업 목표

20-P-2 §5 사용자 §5-7 (c) 결정값 정합:
- (c) 가벼운 의사만 — Doctor 단일 테이블 신설.
- Department / Room / DoctorSchedule / Patient.doctor_id **모두 부재** (post-(c) 후속).
- 기존 Employee.role="doctor" / Treatment.role="doctor" 분기 보존 — Doctor 와 *별개 도메인*.
- F-15 가드 강화 = 후속 (현재 가드 유지).

## 3. 변경 파일 목록

### 신규 (6개)
```
app/migrations/m016_doctors_table.py     (49줄, 인덱스 보강)
app/modules/doctors/__init__.py          (28줄)
app/modules/doctors/schemas.py           (36줄, DoctorIn + DOCTOR_RESPONSE_KEYS)
app/modules/doctors/service.py           (32줄, serialize_doctor)
app/modules/doctors/router.py            (102줄, GET/POST/PUT/DELETE /api/doctors)
tests/test_20_3_3_doctors.py             (143줄, 17 cases)
```

### 수정 (5개)
```
app/models/models.py                     (+18, Doctor ORM 8 컬럼)
app/main.py                              (+2, doctors_router include)
dosu_clinic.spec                         (+7, hidden_imports 4)
tests/test_pyinstaller_hidden_imports.py (+5, EXPECTED 4개)
tests/test_19_8_therapists.py            (~24, 부재 단언 → 신설 단언 갱신)
```

## 4. 수정 가능 / 금지 범위

- 가능: m016, Doctor 모델, app/modules/doctors/ 신설, /api/doctors CRUD, main.py include, 19-8 부재 단언 갱신.
- 금지: m001~m015, Employee 모델 (role="doctor" 보존), Treatment.role="doctor", 기존 33+ 응답 key, main.html JS, F-15 doctor_guard.

## 5. 실제 변경

- `Doctor` 테이블: id / name / specialty(nullable) / license_no(nullable) / color / active / sort_order / created_at / updated_at.
- m016: doctors 테이블 인덱스 보강 (active+sort_order / license_no UNIQUE WHERE NOT NULL). 테이블 본체는 Base.metadata.create_all.
- modules.doctors.{schemas,service,router}: 8키 응답 + CRUD + admin 권한 게이트.
- /api/doctors: GET public + POST/PUT/DELETE require_admin.
- audit detail = name 만 (license_no / specialty 비저장).
- 19-8 부재 단언 2건 갱신 — 본 20-3-3 신설 정합.

## 6. 실행한 테스트 + 결과

```
ruff check app tests scripts                                    → All passed (1 autofix)
scripts/check_db_path.py                                        → exit 0
pytest tests/test_20_3_3_doctors.py -v                          → 17 passed
pytest tests/test_pyinstaller_hidden_imports.py -q              → 219 passed (신설 4 × 2 = +8)
pytest tests -q                                                 → 1773 passed / 1 skipped / 10 xfailed
```

20-3-2 baseline 1748 → 20-3-3 **1773** (+25, 회귀 0).

## 7. 수정 루프

1회차 코드 + ruff + 17 cases → 2회차 19-8 부재 단언 갱신 → 1773 passed.

총 2회 루프.

## 8. 작동확인 (19-C §E 치료사·의사 + §I 관리자 + §M 보안)

- §E 치료사·의사: Doctor 모델 + serialize_doctor + Department/Room/Schedule/Patient.doctor_id 부재 단언.
- §I 관리자: GET public / write require_admin + audit name only.
- §M 보안: 운영 DB / 외부 API / 문자 / PII·API key 원문 부재.

## 9. 자동 테스트로 확인

- Doctor 모델 8 컬럼 + 부재 항목 6 cases
- serialize 8키 + DOCTOR_RESPONSE_KEYS contract 2 cases
- /api/doctors GET/POST/PUT/DELETE 4 cases
- Employee/Treatment 분기 보존 + 별개 도메인 3 cases
- nullable 단언 (license_no / specialty) 2 cases
- PyInstaller 신설 4 모듈 등록 + import 8 cases

## 10. TestClient / API 호출

- GET /api/doctors → 200 + 빈 list
- POST/PUT/DELETE /api/doctors → 401/403 (인증 없이)

## 11. 수동 확인 필요

- 운영 환경 의사 등록 흐름 (UI 화면) — 후속 분할.
- 의사 정보 캘린더 / 환자 카드 표시 — 후속.
- F-15 가드 강화 (DB 근거) — 후속.

## 12. 영향 없음

- 19-C §A 예약 / §B 휴무 / §C 치료항목 / §D 환자 / §G SMS / §H 통계 / §K Health: 영향 0.
- m001~m015 변경 0. main.html JS / FullCalendar 무수정.

## 13. 보안

- 운영 DB: 없음 / 외부 API: 없음 / 실제 문자 발송: 없음
- PII / API key 원문 노출: 없음 (audit detail = name 만, license_no / specialty 평문 응답에만)

## 14. 응답 key 유지

- 신설 /api/doctors 8키 (id/name/specialty/license_no/color/active/sort_order/created_at)
- 기존 33+ 응답 key 셋 보존 — 변경 0.

## 15. 다음 세션 진행

**yes** Codex 통과 시. 다음 = 20-3-4 F-2 반복 예약 진입 전 사용자 §6-6 결정 (반복 패턴 / 시리즈 일괄 처리 / 충돌 검사).

## 16. Codex 결과 위치

- [reports/refactor/20-3-3_codex_review.md](20-3-3_codex_review.md)
- [reports/refactor/latest_codex_review.md](latest_codex_review.md)

## 17. 사용자 → Codex 전달 문구

> "reports/refactor/latest_codex_review_request.md 20-3-3 F-1 (c) 가벼운 의사만 검증 시작해줘. Claude Code 요약만 믿지 말고 m016 마이그레이션 / Doctor ORM 8 컬럼 / app/modules/doctors/ 신설 (router/service/schemas) / /api/doctors CRUD / main.py include / Employee.role=doctor·Treatment.role=doctor 보존 / Department/Room/Schedule/Patient.doctor_id 부재 / F-15 가드 미강화 / 19-8 부재 단언 갱신 정합성을 직접 비교해서 검증해줘. 검증 결과는 reports/refactor/latest_codex_review.md 와 reports/refactor/20-3-3_codex_review.md 에 남겨줘."
