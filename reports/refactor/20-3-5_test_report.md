# 20-3-5 F-3 자원 (치료실 v1) — 테스트 리포트

## 환경

- 직전 commit: `fce1773` (20-3-4 F-2 반복 예약)

## 결과

| 검증 | 결과 |
|---|---|
| ruff | All checks passed (1 autofix) |
| check_db_path | exit 0 |
| `pytest test_20_3_5_resources.py -v` | **18 passed** |
| `pytest test_pyinstaller_hidden_imports + spec_discovery` | **239 passed** (m018 자동 + 신설 4 모듈) |
| `pytest tests -q` 전체 | **1825 passed / 1 skipped / 10 xfailed** in 16.83s |

### baseline 비교

| 시점 | passed | 증가 |
|---|---:|---:|
| 20-3-4 baseline | 1799 | — |
| 20-3-5 (본 세션) | **1825** | **+26** |

증가 26 = test_20_3_5 18 + PyInstaller 신설 4 × 2 = 8.

## 자동 테스트 확인

- Resource 모델 + Appointment.resource_id (5 cases)
- 응답 스키마 (RESOURCE_RESPONSE_KEYS / EXTENDED_PROPS_KEYS) (2 cases)
- check_resource_conflict — 자원 미지정 / 시간 겹침 / canceled 제외 / 자기 자신 제외 (4 cases)
- /api/resources GET / POST/PUT/DELETE require_admin (5 cases)
- POST /api/appointments 자원 충돌 시 409 (1 case)
- POST /api/appointment-series 자원 충돌 슬롯 skip + conflicts (1 case, Codex caveat 3 반영)

## TestClient / API 호출

- POST /api/appointments (같은 자원 + 시간 겹침) → **409 + "자원 충돌" 메시지**
- POST /api/appointment-series (3회 시리즈 + 자원 1슬롯 충돌) → 200 + created 2 + conflicts 1 (`reason="resource_conflict"`)

## 사용자 §7-7 결정값 정합

- (a) 치료실만: type='room' v1, 'equipment' 컬럼 보존 (후속 확장)
- (i) F-1 Room 별개: F-1 (c) 정합, Department / Room 모델 부재
- (i) capacity=1: 같은 자원 + 시간 겹침 검사 (`check_resource_conflict`)
- (i) 인력 자원 미도입: Employee 분기로 충분
- (i) F-2 시리즈 + F-3 통합: 시리즈 등록 시 자원 충돌 검사 추가 (Codex 20-3-4 caveat 3)

## 영향 없음

- 19-C §B 휴무 / §C 치료항목 / §D 환자 / §G SMS / §H 통계 / §K Health: 영향 0.
- m001~m017 변경 0, m018 신설.
- main.html JS / FullCalendar 무수정.
- 단일 예약 (resource_id=None) 동작 보존.

## 19-9 contract 갱신

- APPOINTMENT_EXTENDED_PROPS_KEYS frozenset 18 → 19키 (`resource_id` 추가).

## 보안

- 운영 DB: 없음
- 외부 API: 없음
- 실제 문자 발송: 없음
- PII / API key 원문 노출: 없음 (audit detail = name 만, capacity / type 평문 응답)

## 수동 확인 필요

- UI 자원 dropdown — 본 v1 백엔드만 (UI 후속).
- 캘린더 자원별 view (FullCalendar resourceTimeline) — 후속.
- 장비 (equipment) 자원 도입 — 사용자 결정 후 후속.

## 결론

다음: **그룹 C 5/5 완료. 다음 단계 = 그룹 D 진입 전 20-P-3 그룹 D 상세 기획 (F-4 알림 / F-5 출력물 / F-6 export 확장 / F-9 EMR)** 또는 **현재 단계로 마무리**.
