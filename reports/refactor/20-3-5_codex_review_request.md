# 20-3-5 Codex 검증 요청서

## 1. 세션 이름

`20-3-5_resources` — F-3 자원 (치료실 v1) + Appointment.resource_id + 충돌 검사 (단일 + 시리즈) + Codex 20-3-4 caveat 3 반영.

## 2. 작업 목표

20-P-2 §7 사용자 §7-7 결정값 정합 + Codex 20-3-4 caveat 3 (시리즈 자원 충돌 통합):
- (a) 치료실만 — type='room' v1, 'equipment' 컬럼 보존
- (i) F-1 Room 별개 — F-1 (c) 정합
- (i) capacity=1 — 같은 자원 + 시간 겹침 1건이라도 ⊥
- (i) 인력 자원 미도입
- (i) F-2 시리즈 + F-3 통합 — 시리즈 등록 시 자원 충돌 검사 (충돌 슬롯 skip + 응답 안내)

## 3. 변경 파일 목록

### 신규 (6개)
```
app/migrations/m018_resources.py            (60줄)
app/modules/resources/__init__.py            (26줄)
app/modules/resources/schemas.py             (35줄, ResourceIn + RESOURCE_RESPONSE_KEYS)
app/modules/resources/service.py             (67줄, serialize_resource + check_resource_conflict)
app/modules/resources/router.py              (95줄, GET/POST/PUT/DELETE)
tests/test_20_3_5_resources.py               (327줄, 18 cases)
```

### 수정 (9개)
```
app/models/models.py                         (+25, Resource 모델 + Appointment.resource_id)
app/models/schemas.py                        (+4, AppointmentIn / AppointmentUpdate.resource_id)
app/routers/api.py                           (~25, _serialize 19키 + POST/PUT 자원 충돌)
app/main.py                                  (+2, resources_router include)
app/modules/appointments/schemas.py          (+2, EXTENDED_PROPS_KEYS 19키)
app/modules/appointment_series/schemas.py    (+2, resource_id)
app/modules/appointment_series/router.py     (+20, 시리즈 자원 충돌 검사)
dosu_clinic.spec                             (+6, hidden_imports 4)
tests/test_pyinstaller_hidden_imports.py     (+5, EXPECTED 4개)
```

## 4. 수정 가능 / 금지 범위

- 가능: m018, Resource 모델, Appointment.resource_id, _serialize 19키, modules/resources/, /api/resources CRUD, POST/PUT /api/appointments 자원 충돌 검사, 시리즈 자원 충돌 검사, 19-9 contract 갱신.
- 금지: m001~m017, 기존 33+ 응답 key, main.html JS, F-15 doctor_guard.

## 5. 실제 변경

- m018: ALTER TABLE appointments ADD resource_id (nullable FK) + 충돌 인덱스 + resources 테이블 인덱스. 본체는 Base.metadata.create_all.
- Resource: id/type/name/capacity/active/sort_order/created_at/updated_at. type='room'|'equipment'. capacity 기본 1.
- check_resource_conflict: resource_id + start_at < end_at + status != canceled + exclude_appt_id 제외.
- POST /api/appointments: resource_id 지정 시 충돌 검사 → 409 + 메시지.
- PUT /api/appointments/{aid}: resource_id / start_at / duration_min 변경 시 충돌 검사 (자기 자신 제외).
- POST /api/appointment-series: 각 슬롯 자원 충돌 검사 → skip + `{start_at, reason="resource_conflict"}` conflicts 응답.
- _serialize_appointment.extendedProps 18 → 19키 (resource_id).
- 19-9 EXTENDED_PROPS_KEYS frozenset 19키 갱신.

## 6. 실행한 테스트 + 결과

```
ruff check app tests scripts                                    → All passed (1 autofix)
scripts/check_db_path.py                                        → exit 0
pytest tests/test_20_3_5_resources.py -v                        → 18 passed
pytest tests/test_pyinstaller_hidden_imports + spec_discovery   → 239 passed (m018 자동 + 신설 4 모듈)
pytest tests -q                                                 → 1825 passed / 1 skipped / 10 xfailed
```

20-3-4 baseline 1799 → 20-3-5 **1825** (+26, 회귀 0).

## 7. 수정 루프

1회차 코드 + ruff + 18 passed → 2회차 전체 회귀 1825.

총 2회 루프.

## 8. 작동확인 (19-C §A 예약 + §F 캘린더 + §M 보안)

- §A 예약: POST /api/appointments 자원 충돌 → 409. 시리즈 자원 충돌 슬롯 skip.
- §F 캘린더: extendedProps 에 resource_id 추가 (UI 가 자원별 표시 가능 — 후속).
- §M 보안: 운영 DB / 외부 API / 문자 발송 / PII·API key 원문 부재.

## 9. 자동 테스트로 확인

- 모델 + 컬럼 (5) + 응답 스키마 (2) + check_resource_conflict 4 + endpoints 5 + POST 충돌 1 + 시리즈 자원 충돌 1 = 18 cases.
- PyInstaller 신설 4 모듈 등록 + import (8 cases).

## 10. TestClient / API 호출

- POST /api/appointments (같은 자원 + 시간 겹침) → 409 + "자원 충돌" 메시지.
- POST /api/appointment-series (3회 + 11/12 자원 점유 환자 있음) → 200, created 2 + conflicts 1 (`reason="resource_conflict"`).

## 11. 수동 확인 필요

- UI 자원 dropdown — 후속 분할.
- 캘린더 자원별 view — 후속.
- 장비 (equipment) 자원 도입 — 사용자 결정 후 후속.

## 12. 영향 없음

- 19-C §B 휴무 / §C 치료항목 / §D 환자 / §G SMS / §H 통계 / §K Health: 영향 0.
- m001~m017 변경 0. main.html JS / FullCalendar 무수정.
- 단일 예약 (resource_id=None) 동작 보존.

## 13. 보안

- 운영 DB: 없음 / 외부 API: 없음 / 실제 문자 발송: 없음
- PII / API key 원문 노출: 없음 (audit detail = name 만)

## 14. 응답 key 유지

- 19 extendedProps (18 + resource_id) — 기존 18 보존.
- 신설 /api/resources 7키.
- 시리즈 conflicts 응답에 reason="resource_conflict" 추가 (기존 reason 값과 별개).
- 기존 33+ 응답 key 보존.

## 15. 다음 세션 진행

**yes** Codex 통과 시. **그룹 C 5/5 완료**. 다음 = 그룹 D 진입 전 20-P-3 그룹 D 상세 기획 (F-4 알림 / F-5 출력물 / F-6 export 확장 / F-9 EMR) — Codex 20-P-1 caveat ("그룹 C/D 진입 전 별도 상세 기획 권장") 정합. 또는 현재 단계로 마무리.

## 16. Codex 결과 위치

- [reports/refactor/20-3-5_codex_review.md](20-3-5_codex_review.md)
- [reports/refactor/latest_codex_review.md](latest_codex_review.md)

## 17. 사용자 → Codex 전달 문구

> "reports/refactor/latest_codex_review_request.md 20-3-5 F-3 자원 (치료실 v1) 검증 시작해줘. Claude Code 요약만 믿지 말고 m018 / Resource 모델 / Appointment.resource_id / _serialize_appointment 19키 / app/modules/resources/ / /api/resources CRUD / POST·PUT /api/appointments 자원 충돌 (capacity=1) / POST /api/appointment-series 자원 충돌 슬롯 skip (Codex 20-3-4 caveat 3 반영) / 19-9 contract 갱신 / 사용자 §7-7 결정 (a)·(i)·(i)·(i)·(i) 정합을 직접 비교해서 검증해줘. 검증 결과는 reports/refactor/latest_codex_review.md 와 reports/refactor/20-3-5_codex_review.md 에 남겨줘."
