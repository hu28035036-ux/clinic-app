# 20-3-4 F-2 반복 예약 — 테스트 리포트

## 환경

- 직전 commit: `20-3-3` (Doctor 별도 테이블)

## 결과

| 검증 | 결과 |
|---|---|
| ruff | All checks passed (1 autofix) |
| check_db_path | exit 0 |
| `pytest test_20_3_4_appointment_series.py -v` | **18 passed** |
| `pytest test_pyinstaller_hidden_imports + spec_discovery` | **231 passed** (m017 자동 글롭 + 신설 4 모듈) |
| `pytest tests -q` 전체 | **1799 passed / 1 skipped / 10 xfailed** in 15.22s |

### baseline 비교

| 시점 | passed | 증가 |
|---|---:|---:|
| 20-3-3 baseline | 1773 | — |
| 20-3-4 (본 세션) | **1799** | **+26** |

증가 26 = test_20_3_4 18 + PyInstaller 신설 4 × 2 = 8.

## 자동 테스트 확인

- AppointmentSeries 모델 + Appointment.series_id (4 cases)
- compute_slot_starts (interval_days + count) 계산 (2 cases)
- _serialize_appointment series_id 추가 + 단일 예약 None (2 cases)
- 응답 스키마 (APPOINTMENT_SERIES_RESPONSE_KEYS / SERIES_CREATE_RESPONSE_KEYS / CONFLICT_INFO_KEYS) (3 cases)
- /api/appointment-series POST + 환자 부재 + count 검증 + DELETE 미래만 + 부재 SID (5 cases)
- 호환성 — 단일 예약 series_id=None / 기존 POST /api/appointments 동작 보존 (2 cases)

## TestClient / API 호출

- POST /api/appointment-series (3회 시리즈 생성) → 200 + series + created + conflicts
- DELETE /api/appointment-series/{sid} → 미래 슬롯만 status="canceled", 과거 보존

## 사용자 §6-6 결정값 정합

- (a) N회만: pattern="n_times" + pattern_data={"interval_days":N,"count":M}
- (i) 미래만: DELETE 시 datetime.utcnow() 이후 슬롯만, 과거 보존 + approved 도 제외
- (ii) 충돌 skip: 점심창 충돌 슬롯은 DB 입력 ⊥ + conflicts 응답에 안내

## 영향 없음

- 19-C §B 휴무 / §C 치료항목 / §D 환자 / §G SMS / §H 통계 / §K Health: 영향 0.
- 기존 POST /api/appointments 동작 보존 (단일 예약 series_id=None).
- m001~m016 변경 0, m017 신설.
- main.html JS / FullCalendar 무수정.

## 19-9 contract 갱신

- APPOINTMENT_EXTENDED_PROPS_KEYS frozenset 17키 → 18키 (`series_id` 추가).

## 보안

- 운영 DB: 없음
- 외부 API: 없음
- 실제 문자 발송: 없음
- PII / API key 원문 노출: 없음 (audit 부재 — series 생성 시 _log 만)

## 수동 확인 필요

- 운영 환경에서 시리즈 등록 흐름 (UI 입력 패널) — 본 v1 백엔드만 (UI 후속).
- 캘린더에서 시리즈 식별 표시 (series_id 그룹 색상 등) — UI 후속.
- 충돌 슬롯 사용자 처리 흐름 (다른 시간으로 옮길지 / 빼고 등록할지) — UI 후속.

## 결론

다음: **20-3-5 F-3 자원 (치료실 / 장비) 진입 전 사용자 §7-7 결정**.
