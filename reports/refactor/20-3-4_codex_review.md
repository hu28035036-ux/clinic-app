# 20-3-4 Codex 검증 결과

## 1. 검증 대상

- 요청서: `reports/refactor/latest_codex_review_request.md`
- 세션 요청서: `reports/refactor/20-3-4_codex_review_request.md`
- 세션명: `20-3-4_appointment_series`
- 검증 일시: 2026-05-04

## 2. 결론

**통과.**

Claude Code 요약만 보지 않고 실제 변경 파일, diff, 테스트 결과, 로그를 직접 비교했다. 20-P-2 §6-6 결정값인 (a) N회 반복, (i) 미래 일정만 일괄 처리, (ii) 충돌 슬롯 skip + 응답 안내에 맞춰 `AppointmentSeries`, `Appointment.series_id`, `/api/appointment-series` 생성/삭제 흐름이 구현되어 있다.

다음 세션은 `20-3-5 F-3 자원` 이며, 진입 전 사용자 §7-7 자원 범위/Room 통합 여부 결정이 필요하다.

## 3. 실제 변경 파일 확인

### 신규 파일

- `app/migrations/m017_appointment_series.py`
- `app/modules/appointment_series/__init__.py`
- `app/modules/appointment_series/schemas.py`
- `app/modules/appointment_series/service.py`
- `app/modules/appointment_series/router.py`
- `tests/test_20_3_4_appointment_series.py`
- `reports/refactor/20-3-4_fix_summary.md`
- `reports/refactor/20-3-4_test_report.md`
- `reports/refactor/20-3-4_codex_review_request.md`

### 수정 파일

- `app/main.py`
- `app/models/models.py`
- `app/modules/appointments/schemas.py`
- `app/routers/api.py`
- `dosu_clinic.spec`
- `tests/test_pyinstaller_hidden_imports.py`
- `reports/refactor/latest_fix_summary.md`
- `reports/refactor/latest_test_report.md`
- `reports/refactor/latest_codex_review_request.md`

`git diff --stat` 의 tracked 범위에서는 신규 untracked 파일이 제외되므로, 실제 파일 목록은 `git status`, `Get-ChildItem`, 신규 파일 직접 읽기로 별도 확인했다.

## 4. 구현 검증

- `AppointmentSeries` ORM 모델이 추가됐고 `pattern="n_times"` 및 `pattern_data` JSON 문자열로 N회 반복 정보를 저장한다.
- `Appointment.series_id` 는 nullable FK 로 추가되어 기존 단일 예약은 `None` 을 유지한다.
- m017 마이그레이션은 `appointments.series_id` 컬럼과 `ix_appointments_series_id` 인덱스를 idempotent 하게 보강한다. `appointment_series` 테이블 존재 시 `ix_appointment_series_patient_created` 도 보강한다.
- `_serialize_appointment()` 의 `extendedProps` 에 `series_id` 가 추가됐고, `APPOINTMENT_EXTENDED_PROPS_KEYS` 는 기존 17개 + `series_id` 로 갱신됐다.
- `app/modules/appointment_series` 에 router/service/schemas가 추가됐고 `APPOINTMENT_SERIES_RESPONSE_KEYS`, `SERIES_CREATE_RESPONSE_KEYS`, `CONFLICT_INFO_KEYS` 계약이 정의됐다.
- `POST /api/appointment-series` 는 series row 생성 후 `interval_days` + `count` 로 슬롯을 만들고, 생성된 예약 id 리스트와 `conflicts` 리스트를 응답한다.
- `DELETE /api/appointment-series/{sid}` 는 `datetime.utcnow()` 이후 미래 슬롯만 `status="canceled"` 로 변경하고 과거 슬롯과 approved 슬롯은 건드리지 않는다.
- `app/main.py` 에 appointment_series router가 include 됐다.
- `dosu_clinic.spec` 와 `tests/test_pyinstaller_hidden_imports.py` 에 appointment_series 모듈 4개가 hidden import 대상으로 추가됐다.

## 5. 테스트/로그 재실행 결과

직접 재실행한 결과:

```text
ruff check app tests scripts
All checks passed!
```

```text
pytest tests/test_20_3_4_appointment_series.py tests/test_19_9_appointments.py tests/test_pyinstaller_hidden_imports.py tests/test_migration_spec_discovery.py -q
330 passed, 1 warning in 1.53s
```

```text
pytest tests -q
1799 passed, 1 skipped, 10 xfailed, 27 warnings in 14.95s
```

```text
scripts/check_db_path.py
exit 0
```

추가로 테스트 격리 DB에서 실제 생성/삭제 성공 경로를 직접 확인했다.

```text
POST /api/appointment-series -> 200
created 3 appointments
conflicts []
DELETE /api/appointment-series/{sid} -> 200
canceled 3 future appointments
```

격리 DB 시작 로그에서 m001~m017 마이그레이션 적용도 확인했다.

전체 테스트 결과는 `reports/refactor/20-3-4_test_report.md` 의 reported result 와 일치한다. 경고는 기존 테스트 함수 return warning 및 pytest cache 경로 warning 이며, 이번 appointment_series 구현 실패는 아니다.

## 6. 보고서 정합성

- `latest_fix_summary.md` 와 `20-3-4_fix_summary.md` 는 동일했다.
- `latest_test_report.md` 와 `20-3-4_test_report.md` 는 동일했다.
- `latest_codex_review_request.md` 와 `20-3-4_codex_review_request.md` 는 동일했다.
- test report 의 `1799 passed / 1 skipped / 10 xfailed` 는 직접 재실행 결과와 일치했다.

## 7. Caveat

- PyInstaller 실제 exe build 는 실행하지 않았다. 대신 hidden import/spec discovery 테스트 231개가 통과해 m017 발견과 appointment_series 모듈 import 가능성은 확인했다.
- UI 시리즈 등록 패널, 캘린더 시리즈 그룹 표시, 충돌 슬롯 사용자 선택 처리는 이번 백엔드 v1 범위 밖이다.
- 현재 `conflicts` 리스트는 구현상 `_check_lunch_block()` 에 걸린 슬롯 skip 을 중심으로 생성된다. 일반적인 치료사 시간 중복/휴무 충돌까지 포괄하는 검증이라고 보기는 어렵다. 후속 20-3-5 또는 UI 작업 전, “충돌”의 범위를 점심창만으로 볼지 예약 중복/휴무까지 확장할지 결정하는 편이 안전하다.
- series 생성 endpoint 는 기존 단일 `POST /api/appointments` 와 별도 구현으로 예약 row를 직접 만든다. 현재 테스트는 단일 예약 호환성과 series 생성/삭제를 확인했지만, 기존 예약 생성의 모든 부가 정책을 재사용한다고 단정하면 안 된다.
- m017은 `Base.metadata.create_all()` 이후 인덱스/컬럼 보강을 수행하는 구조다. 현재 `init_db()` 순서상 정상이나, 마이그레이션만 독립 실행해 `appointment_series` 테이블이 없으면 해당 인덱스 보강은 skip 한다.
- `git status` 의 `C:\Users\user/.config/git/ignore` permission warning 은 기존 환경 경고로 보이며 검증 판정에는 영향이 없다.

## 8. 최종 판정

**20-3-4 검증 통과.**

백엔드 F-2 반복 예약 구현은 요청서 범위와 테스트 결과에 부합한다. 다음 단계는 `20-3-5 F-3 자원` 이며, 시작 전 사용자 §7-7 자원 범위와 F-1 Room 통합 여부 결정이 필요하다.
