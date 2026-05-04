# 20-3-5 Codex 검증 결과

## 1. 검증 대상

- 요청서: `reports/refactor/latest_codex_review_request.md`
- 세션 요청서: `reports/refactor/20-3-5_codex_review_request.md`
- 세션명: `20-3-5_resources`
- 검증 일시: 2026-05-04

## 2. 결론

**통과.**

Claude Code 요약만 보지 않고 실제 변경 파일, diff, 테스트 결과, 로그를 직접 비교했다. 20-P-2 §7-7 결정값에 맞춰 치료실 v1 자원 모델, `Appointment.resource_id`, `/api/resources` CRUD, 단일 예약 자원 충돌, 시리즈 예약 자원 충돌 skip 흐름이 구현되어 있다. 특히 20-3-4 검증 caveat였던 “시리즈 충돌이 점심창 중심으로만 처리됨” 문제는 자원 충돌에 한해 `reason="resource_conflict"` 응답으로 보강됐다.

Group C 5/5 구현은 완료 상태다. 다음 단계는 Group D 진입 전 `20-P-3` 상세 기획이 안전하다.

## 3. 실제 변경 파일 확인

### 신규 파일

- `app/migrations/m018_resources.py`
- `app/modules/resources/__init__.py`
- `app/modules/resources/schemas.py`
- `app/modules/resources/service.py`
- `app/modules/resources/router.py`
- `tests/test_20_3_5_resources.py`
- `reports/refactor/20-3-5_fix_summary.md`
- `reports/refactor/20-3-5_test_report.md`
- `reports/refactor/20-3-5_codex_review_request.md`

### 수정 파일

- `app/main.py`
- `app/models/models.py`
- `app/models/schemas.py`
- `app/modules/appointment_series/router.py`
- `app/modules/appointment_series/schemas.py`
- `app/modules/appointments/schemas.py`
- `app/routers/api.py`
- `dosu_clinic.spec`
- `tests/test_pyinstaller_hidden_imports.py`
- `reports/refactor/latest_fix_summary.md`
- `reports/refactor/latest_test_report.md`
- `reports/refactor/latest_codex_review_request.md`

## 4. 구현 검증

- `Resource` ORM 모델이 추가됐고 컬럼은 `id`, `type`, `name`, `capacity`, `active`, `sort_order`, `created_at`, `updated_at` 이다.
- `Appointment.resource_id` 는 nullable FK 로 추가되어 기존 단일 예약은 `None` 동작을 유지한다.
- m018 마이그레이션은 `appointments.resource_id`, `ix_appointments_resource_time`, `ix_resources_type_active` 를 idempotent 하게 보강한다.
- `_serialize_appointment()` 의 `extendedProps` 에 `resource_id` 가 추가됐고, `APPOINTMENT_EXTENDED_PROPS_KEYS` 는 기존 18개 + `resource_id` 로 갱신됐다.
- `app/modules/resources` 에 router/service/schemas가 추가됐고 `RESOURCE_RESPONSE_KEYS` 7키 계약이 정의됐다.
- `GET /api/resources` 는 public 목록 조회이며, `POST/PUT/DELETE /api/resources` 는 `require_admin` 을 사용한다.
- `check_resource_conflict()` 는 같은 `resource_id`, 시간 겹침, `status != "canceled"` 조건으로 충돌 예약을 찾고, PUT 흐름에서는 자기 자신을 제외한다.
- `POST /api/appointments` 는 `resource_id` 지정 시 충돌이 있으면 409를 반환한다.
- `PUT /api/appointments/{aid}` 는 `resource_id`, `start_at`, `duration_min` 변경 시 자원 충돌을 검사한다.
- `POST /api/appointment-series` 는 각 슬롯마다 자원 충돌을 검사하고 충돌 슬롯은 skip 하며 `reason="resource_conflict"` 로 응답한다.
- `dosu_clinic.spec` 와 `tests/test_pyinstaller_hidden_imports.py` 에 resources 모듈 4개가 hidden import 대상으로 추가됐다.

## 5. 테스트/로그 재실행 결과

직접 재실행한 결과:

```text
ruff check app tests scripts
All checks passed!
```

```text
pytest tests/test_20_3_5_resources.py tests/test_19_9_appointments.py tests/test_pyinstaller_hidden_imports.py tests/test_migration_spec_discovery.py -q
338 passed, 1 warning in 2.17s
```

```text
pytest tests -q
1825 passed, 1 skipped, 10 xfailed, 27 warnings in 16.06s
```

```text
scripts/check_db_path.py
exit 0
```

추가로 테스트 격리 DB에서 실제 API 흐름을 직접 확인했다.

```text
POST /api/resources -> 200
POST /api/appointments with resource_id -> 200
POST /api/appointments overlapping same resource -> 409
POST /api/appointment-series with one resource conflict -> 200
series created: 2
series conflicts: [{"start_at": "2099-07-11T10:00:00", "reason": "resource_conflict"}]
```

격리 DB 시작 로그에서 m001~m018 마이그레이션 적용도 확인했다.

전체 테스트 결과는 `reports/refactor/20-3-5_test_report.md` 의 reported result 와 일치한다. 경고는 기존 테스트 함수 return warning 및 pytest cache 경로 warning 이며, 이번 resources 구현 실패는 아니다.

## 6. 보고서 정합성

- `latest_fix_summary.md` 와 `20-3-5_fix_summary.md` 는 동일했다.
- `latest_test_report.md` 와 `20-3-5_test_report.md` 는 동일했다.
- `latest_codex_review_request.md` 와 `20-3-5_codex_review_request.md` 는 동일했다.
- test report 의 `1825 passed / 1 skipped / 10 xfailed` 는 직접 재실행 결과와 일치했다.

## 7. Caveat

- PyInstaller 실제 exe build 는 실행하지 않았다. 대신 hidden import/spec discovery 테스트 239개가 통과해 m018 발견과 resources 모듈 import 가능성은 확인했다.
- UI 자원 dropdown, FullCalendar resourceTimeline, equipment 자원 도입은 이번 백엔드 v1 범위 밖이다.
- `capacity` 컬럼은 존재하지만 현재 충돌 정책은 capacity=1 고정처럼 동작한다. capacity > 1 사용은 후속 확장 정책이 필요하다.
- 존재하지 않는 `resource_id` 로 `POST /api/appointments` 를 호출하면 현재 200으로 예약이 생성된다. UI dropdown 경로에서는 보통 유효 id만 들어오겠지만, 백엔드 무결성 관점에서는 resource 존재/active 검증을 후속 보완하는 편이 안전하다.
- `DELETE /api/resources/{rid}` 는 이미 예약에서 참조 중인 자원 삭제를 별도로 차단하지 않는다. 실제 운영 전에 삭제 대신 inactive 처리 정책을 정하는 것이 안전하다.
- `git status` 의 `C:\Users\user/.config/git/ignore` permission warning 은 기존 환경 경고로 보이며 검증 판정에는 영향이 없다.

## 8. 최종 판정

**20-3-5 검증 통과.**

백엔드 F-3 자원 구현은 요청서 범위와 테스트 결과에 부합한다. Group C는 5/5 완료 상태이며, 다음 단계는 Group D 진입 전 `20-P-3` 상세 기획이다.
