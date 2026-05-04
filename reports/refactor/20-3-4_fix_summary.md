# 20-3-4 F-2 반복 예약 변경 요약

## 변경 파일 목록

### 신규 (6개)

| 파일 | 줄 수 |
|---|---:|
| `app/migrations/m017_appointment_series.py` | 65 |
| `app/modules/appointment_series/__init__.py` | 22 |
| `app/modules/appointment_series/schemas.py` | 53 |
| `app/modules/appointment_series/service.py` | 50 |
| `app/modules/appointment_series/router.py` | 165 |
| `tests/test_20_3_4_appointment_series.py` | 285 (18 cases) |

### 수정 (5개)

| 파일 | diff | 의도 |
|---|---:|---|
| `app/models/models.py` | +25 | AppointmentSeries 모델 + Appointment.series_id |
| `app/routers/api.py` | +2 | _serialize_appointment.extendedProps 에 series_id |
| `app/main.py` | +2 | appointment_series_router include |
| `app/modules/appointments/schemas.py` | +2 | EXTENDED_PROPS_KEYS 18키 |
| `dosu_clinic.spec` | +6 | hidden_imports 4 |
| `tests/test_pyinstaller_hidden_imports.py` | +5 | EXPECTED 4개 |

## 사용자 §6-6 결정값 정합

- **(a) N회만**: `pattern="n_times"` + `pattern_data={"interval_days":N,"count":M}` (count: 2~52)
- **(i) 미래만 일괄 처리**: DELETE 시 `datetime.utcnow()` 이후 슬롯만 취소, 과거 보존, `status="approved"` 도 제외 (개별 처리)
- **(ii) 충돌 슬롯 skip**: 점심창 충돌은 DB 입력 ⊥ + `conflicts` 응답에 `[{start_at, reason}, ...]` 안내

## 신설 endpoint

- `POST /api/appointment-series` — 시리즈 + N개 슬롯 생성. 응답: `{series, created: [appt_id...], conflicts: [{start_at, reason}...]}`
- `DELETE /api/appointment-series/{sid}` — 미래 슬롯만 일괄 `status="canceled"` + 메모 `[취소-시리즈]` prefix

## 호환성

- 20-3-3 baseline 1773 → 20-3-4 baseline **1799** (+26, 회귀 0)
- 기존 POST /api/appointments / PUT / DELETE / cancel / mark-no-show 동작 무수정 (단일 예약은 series_id=None)
- 기존 33+ 응답 key + 기존 17 extendedProps 보존 (series_id 추가 — 18키)
- 기존 _check_lunch_block 점심창 검사 재사용 (도수 중복 / 휴무 차단은 19-4 백엔드 검증 자동 적용)
- m001~m016 변경 0, m017 신설만

## 마이그레이션 번호 정리

20-P-2 §3 계획 = m017~m020 (F-1 풀 EMR Department/Room/Schedule/Patient.doctor_id) → 사용자 §5-7 (c) 가벼운 의사 결정으로 패스.
**m017 = F-2 (반복 예약)** 으로 사용 (연속 번호). m016 (Doctor) → m017 (Series) 자연스러움.

## 5회 루프

1회차 코드 + ruff (1 autofix) + 18 cases passed
2회차 PyInstaller 231 + 전체 회귀 1799

총 2회 루프 안에 통과.
