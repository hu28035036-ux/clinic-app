# 20-3-4 Codex 검증 요청서

## 1. 세션 이름

`20-3-4_appointment_series` — F-2 반복 예약 도입 (m017 + AppointmentSeries + /api/appointment-series CRUD).

## 2. 작업 목표

20-P-2 §6 사용자 §6-6 결정값 정합:
- (a) N회만 — interval_days + count
- (i) 미래만 일괄 처리 — DELETE 시 utcnow 이후 슬롯만
- (ii) 충돌 슬롯 skip + 응답 안내 (DB 입력 ⊥, conflicts 리스트 제공)

## 3. 변경 파일 목록

### 신규 (6개)
```
app/migrations/m017_appointment_series.py        (65줄)
app/modules/appointment_series/__init__.py        (22줄)
app/modules/appointment_series/schemas.py         (53줄)
app/modules/appointment_series/service.py         (50줄)
app/modules/appointment_series/router.py          (165줄)
tests/test_20_3_4_appointment_series.py           (285줄, 18 cases)
```

### 수정 (6개)
```
app/models/models.py                              (+25, AppointmentSeries + series_id)
app/routers/api.py                                (+2, _serialize_appointment series_id)
app/main.py                                       (+2, appointment_series_router include)
app/modules/appointments/schemas.py               (+2, EXTENDED_PROPS_KEYS 18키)
dosu_clinic.spec                                  (+6, hidden_imports 4)
tests/test_pyinstaller_hidden_imports.py          (+5, EXPECTED 4개)
```

## 4. 수정 가능 / 금지 범위

- 가능: m017, AppointmentSeries 모델, Appointment.series_id, _serialize_appointment 18키, modules/appointment_series/, /api/appointment-series CRUD, 19-9 contract 갱신.
- 금지: m001~m016, 기존 POST /api/appointments / cancel / mark-no-show 동작 변경, 기존 33+ 응답 key, main.html JS, F-15 doctor_guard.

## 5. 실제 변경

- m017: ALTER TABLE appointments ADD COLUMN series_id (nullable FK) + 인덱스 보강. 본체는 Base.metadata.create_all.
- AppointmentSeries: id/patient_id/therapist_id/pattern/pattern_data/start_date/end_date/treatment_codes/created_at.
- POST /api/appointment-series: 시리즈 + N 슬롯 생성. 점심창 충돌 슬롯은 DB 입력 ⊥ + conflicts 응답.
- DELETE /api/appointment-series/{sid}: utcnow 이후 슬롯만 status="canceled" + 메모 [취소-시리즈]. approved 슬롯 제외.
- _serialize_appointment.extendedProps 17 → 18키 (series_id).
- 19-9 EXTENDED_PROPS_KEYS frozenset 18키 갱신.

## 6. 마이그레이션 번호

20-P-2 §3 계획 = m017~m020 (F-1 풀 EMR) → 사용자 §5-7 (c) 가벼운 의사 결정으로 패스. **m017 = F-2** (연속 번호).

## 7. 실행한 테스트 + 결과

```
ruff check app tests scripts                                    → All passed (1 autofix)
scripts/check_db_path.py                                        → exit 0
pytest tests/test_20_3_4_appointment_series.py -v               → 18 passed
pytest tests/test_pyinstaller_hidden_imports + spec_discovery   → 231 passed (m017 자동 + 신설 4 모듈)
pytest tests -q                                                 → 1799 passed / 1 skipped / 10 xfailed
```

20-3-3 baseline 1773 → 20-3-4 **1799** (+26, 회귀 0).

## 8. 수정 루프

1회차 코드 + ruff + 18 cases → 2회차 PyInstaller 231 + 전체 회귀 1799.

총 2회 루프.

## 9. 작동확인 (19-C §A 예약 + §F 캘린더 + §M 보안)

- §A 예약: TestClient POST 시리즈 등록 → series + created + conflicts. DELETE → 미래만 취소 + 과거 보존.
- §F 캘린더: extendedProps 에 series_id 추가 (UI 가 시리즈 그룹 표시 가능 — 후속).
- §M 보안: 운영 DB / 외부 API / 문자 발송 / PII·API key 원문 부재.

## 10. 자동 테스트로 확인

- 모델 (4) + 슬롯 계산 (2) + serialize (2) + 응답 스키마 (3) + endpoints (5) + 호환성 (2) = 18 cases.
- PyInstaller 신설 4 모듈 등록 + import (8 cases).

## 11. 수동 확인 필요

- UI 시리즈 등록 입력 패널 — 후속 분할.
- 캘린더 시리즈 그룹 표시 (색상 / 마커) — 후속.
- 충돌 슬롯 사용자 별도 처리 흐름 — UI 후속.

## 12. 영향 없음

- 19-C §B 휴무 / §C 치료항목 / §D 환자 / §G SMS / §H 통계 / §K Health: 영향 0.
- m001~m016 변경 0. main.html JS / FullCalendar 무수정.
- 기존 /api/appointments POST / cancel / mark-no-show 동작 보존.

## 13. 운영 DB / 외부 API / 문자 / PII

모두 없음.

## 14. 응답 key 유지

- 18 extendedProps (17 + series_id) — 기존 17 보존.
- 신설 series 응답 7키 / SERIES_CREATE 3키 (series/created/conflicts) / CONFLICT 2키.
- 기존 33+ 응답 key 보존.

## 15. 다음 세션 진행

**yes** Codex 통과 시. 다음 = 20-3-5 F-3 자원 (치료실 / 장비) 진입 전 사용자 §7-7 결정.

## 16. Codex 결과 위치

- [reports/refactor/20-3-4_codex_review.md](20-3-4_codex_review.md)
- [reports/refactor/latest_codex_review.md](latest_codex_review.md)

## 17. 사용자 → Codex 전달 문구

> "reports/refactor/latest_codex_review_request.md 20-3-4 F-2 반복 예약 검증 시작해줘. Claude Code 요약만 믿지 말고 m017 (m021 → m017 번호 변경) / AppointmentSeries 모델 / Appointment.series_id / _serialize_appointment 18키 / app/modules/appointment_series/ / POST·DELETE /api/appointment-series / 19-9 contract 갱신 / 사용자 §6-6 결정 (a)·(i)·(ii) 정합 / 점심창 충돌 skip / 미래만 취소 / 과거 보존을 직접 비교해서 검증해줘. 검증 결과는 reports/refactor/latest_codex_review.md 와 reports/refactor/20-3-4_codex_review.md 에 남겨줘."
