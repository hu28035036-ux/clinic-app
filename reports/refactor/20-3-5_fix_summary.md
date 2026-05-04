# 20-3-5 F-3 자원 변경 요약

## 변경 파일 목록

### 신규 (6개)

| 파일 | 줄 수 |
|---|---:|
| `app/migrations/m018_resources.py` | 60 |
| `app/modules/resources/__init__.py` | 26 |
| `app/modules/resources/schemas.py` | 35 |
| `app/modules/resources/service.py` | 67 |
| `app/modules/resources/router.py` | 95 |
| `tests/test_20_3_5_resources.py` | 327 (18 cases) |

### 수정 (8개)

| 파일 | diff | 의도 |
|---|---:|---|
| `app/models/models.py` | +25 | Resource 모델 + Appointment.resource_id FK |
| `app/models/schemas.py` | +4 | AppointmentIn / AppointmentUpdate.resource_id |
| `app/routers/api.py` | ~25 | _serialize_appointment 19키 + POST/PUT 자원 충돌 검사 |
| `app/main.py` | +2 | resources_router include |
| `app/modules/appointments/schemas.py` | +2 | EXTENDED_PROPS_KEYS 19키 |
| `app/modules/appointment_series/schemas.py` | +2 | resource_id |
| `app/modules/appointment_series/router.py` | +20 | 시리즈 자원 충돌 검사 (Codex caveat 3 반영) |
| `dosu_clinic.spec` | +6 | hidden_imports 4 |
| `tests/test_pyinstaller_hidden_imports.py` | +5 | EXPECTED 4개 |

## 사용자 §7-7 결정값 정합

- **(a) 치료실만**: type='room' v1. 'equipment' 컬럼 보존 (후속 확장 — pydantic pattern 으로 'room|equipment' 허용)
- **(i) F-1 Room 별개**: F-1 (c) 가벼운 의사 결정 정합. Department / Room 모델 부재
- **(i) capacity=1**: 같은 자원 + 시간 겹침 1건 → 409. capacity 컬럼 보존 (후속 capacity > 1 확장 가능)
- **(i) 인력 자원 미도입**: Employee 분기로 충분. type='person' 후보 미설치
- **(i) F-2 시리즈 + F-3 통합**: 시리즈 등록 시 자원 충돌 슬롯 skip + `reason="resource_conflict"` 응답

## 신설 endpoint

- `GET /api/resources?active_only={bool}&type={room|equipment}` (public 목록)
- `POST /api/resources` (require_admin)
- `PUT /api/resources/{rid}` (require_admin)
- `DELETE /api/resources/{rid}` (require_admin)
- 응답 7키: id / type / name / capacity / active / sort_order / created_at

## 충돌 검사 정책

- POST /api/appointments — `resource_id` 지정 시 capacity=1 충돌 검사 → 409
- PUT /api/appointments/{aid} — resource_id / start_at / duration_min 변경 시 충돌 검사 (자기 자신 제외)
- POST /api/appointment-series — 12개 슬롯 각각 자원 충돌 검사 → 충돌 슬롯 DB 입력 ⊥ + conflicts 응답에 `{start_at, reason="resource_conflict"}`

## 호환성

- 20-3-4 baseline 1799 → 20-3-5 baseline **1825** (+26, 회귀 0)
- 기존 POST /api/appointments / PUT 동작 보존 (resource_id=None 시 충돌 검사 skip)
- 기존 33+ 응답 key + 18 extendedProps 보존 (resource_id 추가 — 19키)
- 기존 _check_lunch_block 점심창 정책 보존
- m001~m017 변경 0, m018 신설만
- main.html JS / FullCalendar 무수정

## 5회 루프

1회차 코드 + ruff (1 autofix) + 18 cases passed
2회차 PyInstaller 239 + 전체 회귀 1825

총 2회 루프 안에 통과.
