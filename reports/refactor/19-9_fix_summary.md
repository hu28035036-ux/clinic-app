# 19-9 appointments 분리 — 변경 요약

## 세션 이름

`19-9_appointments_service_repository` — 예약 도메인 service / repository / rules /
schemas 후보 helper 분리. 라우터 본체 *완전 무수정* — byte-equivalent helper
만 신설.

## 작업 목표 (한 문장)

`api.py` 의 모든 예약 핸들러 (`create_appointment` / `update_appointment` /
`approve_appointment` / `cancel_appointment` / `revert_approve` /
`delete_appointment` / `change_assignment` / `split_appointment_code` /
`list_appointments` / `last_appointments` / `patient_manual_history_summary` /
`patient_history`) 의 *조회 query / 응답 dict / 상태 판정 / 메모 포맷* 을
`app/modules/appointments/` 후보 구조에 byte-equivalent helper 로 분리. 라우터
본체 / DB schema / API 응답 key *완전 무수정*.

## 변경 파일 목록

| 파일 | 변경 종류 | 줄 수 |
|---|---|---:|
| `app/modules/appointments/__init__.py` | 수정 (19-9 docstring 추가) | 42 |
| `app/modules/appointments/availability.py` | 무수정 (19-4 보존) | 369 |
| `app/modules/appointments/rules.py` | 신규 | 206 |
| `app/modules/appointments/repository.py` | 신규 | 205 |
| `app/modules/appointments/service.py` | 신규 | 233 |
| `app/modules/appointments/schemas.py` | 신규 | 156 |
| `tests/test_19_9_appointments.py` | 신규 (81 contract cases) | 945 |
| `dosu_clinic.spec` | 수정 (+8) | — |
| `tests/test_pyinstaller_hidden_imports.py` | 수정 (+5) | — |

## 파일별 변경 요약

### `app/modules/appointments/__init__.py` (수정, 19-4 → 19-9 docstring)

19-4 시점 docstring 에 19-9 본 세션 범위 / 범위 외 / COMPAT / SAFETY / NOTE /
RISK 추가. *코드 변경 ⊥*.

### `app/modules/appointments/rules.py` (신규, 206줄)

순수 도메인 규칙 (DB / ORM 미참조).

- **상태 상수** : `APPT_STATUS_RESERVED / APPROVED / CANCELED` —
  `app.models.models.APPT_STATUSES` 정합.
- **상태 전이 판정** :
  - `is_editable_status` (수정 가능) — `api.py:1686 / 1814` 정합.
  - `is_approvable_status` (승인 가능) — `api.py:1963~1966` 정합.
  - `is_revertable_status` (되돌림 가능) — `api.py:1989` 정합.
  - `is_cancelable_status` (취소 가능) — `api.py:2012` 정합.
  - `is_already_approved` / `is_canceled`.
- **한국어 사용자 노출 메시지** : `EDIT_BLOCKED_MESSAGE` /
  `ALREADY_APPROVED_MESSAGE` / `APPROVE_BLOCKED_CANCELED_MESSAGE` /
  `REVERT_BLOCKED_MESSAGE` / `CANCEL_BLOCKED_APPROVED_MESSAGE`.
- **취소 메모 포맷** : `append_cancel_memo` — `api.py:cancel_appointment`
  line 2016 인라인 패턴 byte-equivalent.
- **승인자 정규화** : `normalize_approved_by` — `api.py:approve_appointment`
  line 1970 정합.
- **카운트 clamp** : `clamp_count_at_zero` — `api.py:_bump_patient_count`
  line 1946 / 1952 정합.

### `app/modules/appointments/repository.py` (신규, 205줄)

read-only `Appointment` / `TreatmentAssignment` / `Treatment` /
`PatientTreatmentCount` 조회 helper (DB 세션 호출자 주입, lazy import).

- `get_appointment_by_id(db, aid)` — `db.get(Appointment, aid)` 정합.
- `list_appointments_in_range(db, start_naive, end_naive)` — `api.py:1615~1617` 정합.
- `list_active_appointments_for_patient(db, pid)` — canceled 제외 query 정합.
- `list_approved_appointments_for_patient_desc(db, pid)` — patient_history desc 정합.
- `last_appointment_per_patient(db)` — group_by max + canceled 제외 정합.
- `find_assignment_for_code(appointment, treatment_code)` — list scan helper.
- `find_treatment_by_code(db, code)` — `filter_by(code=...)` 정합.
- `get_patient_treatment_count_row(db, patient_id, treatment_id)` — lazy 사전 검사 정합.

### `app/modules/appointments/service.py` (신규, 233줄)

응답 dict 빌더 (모든 응답 dict byte-equivalent).

- `build_create_response` — 2키 `{id, status}`.
- `build_update_response` / `build_approve_response` / `build_revert_response` /
  `build_cancel_response` / `build_delete_response`.
- `build_split_no_split_response` / `build_split_real_response`.
- `build_last_appointments_response` — 환자별 ISO8601 dict.
- `build_manual_history_summary` / `build_patient_history_envelope`.
- `append_cancel_memo` — `rules` re-export (호출자 가독성).

### `app/modules/appointments/schemas.py` (신규, 156줄)

응답 dict *키 셋* contract 상수 (frozenset).

- `CREATE_RESPONSE_KEYS` / `UPDATE_RESPONSE_KEYS` / `ASSIGN_RESPONSE_KEYS` /
  `APPROVE_RESPONSE_KEYS` / `REVERT_RESPONSE_KEYS` / `CANCEL_RESPONSE_KEYS` /
  `DELETE_RESPONSE_KEYS`.
- `SPLIT_NO_SPLIT_RESPONSE_KEYS` / `SPLIT_REAL_RESPONSE_KEYS`.
- `APPOINTMENT_SERIALIZE_TOP_KEYS` (6키) / `APPOINTMENT_EXTENDED_PROPS_KEYS` (17키).
- `MANUAL_HISTORY_SUMMARY_KEYS` / `PATIENT_HISTORY_ENVELOPE_KEYS`.

### `tests/test_19_9_appointments.py` (신규, 945줄)

81 cases — contract 검증.

1. 상태 상수 / `app.models.models.APPT_STATUSES` 정합.
2. 상태 전이 판정 (10 parametrize cases).
3. `append_cancel_memo` byte-equivalent (8 parametrize).
4. `normalize_approved_by` (6 parametrize).
5. `clamp_count_at_zero` (7 parametrize).
6. repository 동작 — DB 격리 fixture (시드 환자 + 치료사 사용).
7. service 응답 빌더 byte-equivalent.
8. schemas contract 상수가 실제 응답 dict 키와 일치.
9. 단방향 경계 (D-4) — `app.routers` 미참조 / ORM lazy import.
10. 라우터 13개 핸들러 시그니처 무수정.
11. 기존 흐름 영향 없음 — `POST /api/appointments` / `GET /api/appointments` /
   `last_appointments` / `manual-history-summary` / `history` 응답 키 contract.

### `dosu_clinic.spec` (수정, +8줄)

`hidden` 리스트에 19-9 신규 4개 모듈 등록:

```
'app.modules.appointments.rules',
'app.modules.appointments.repository',
'app.modules.appointments.service',
'app.modules.appointments.schemas',
```

### `tests/test_pyinstaller_hidden_imports.py` (수정, +5줄)

`EXPECTED_19_X_MODULES_MODULES` 에 4개 모듈 추가 — spec 등록 + import 가능성을
parametrize 로 검증 (8 cases 추가).

## 의도 / 이유

- **byte-equivalent 분리** : `_serialize_appointment` 응답 / 모든 핸들러 응답 dict /
  상태 분기 / 메모 포맷이 `api.py` 안에 인라인으로 분산되어 있음 — 19-10+ 라우터
  채택 시점에 본 helper 가 채택될 후보.
- **계약 회귀 보호** : `schemas.py` 의 contract 상수가 응답 키 셋 *임의 변경* 을
  검출. UI / SMS / 통계 / AI 의존 키 보호.
- **라우터 / API 응답 무수정** : 본 19-9 가 *helper 만* 추가 — 라우터 본체 /
  CRUD 흐름 *완전 무수정*. 19-10+ 시점에 점진적 채택.
- **D-4 경계 보존** : `rules.py` 는 ORM / DB 미참조, `repository.py` / `service.py`
  만 함수 안 lazy import. `app.routers` 미참조.

## 보수적 1차 분리 — 19-10+ 미채택 helper 후보

본 19-9 시점에 *helper 만 신설*, 라우터 채택 ⊥ — 19-10 SMS / 19-11 통계 분리
이후 점진적으로 라우터에서 본 helper 호출로 전환. 이번 세션에서는 *대규모 본체
이동 ⊥* (사용자 지시문 정합).

## 라우팅 충돌 발견 (19-9 범위 외)

`/api/patients/last-appointments` (api.py:1487) 가 `/api/patients/{pid}`
(api.py:1348) 보다 *나중에 선언* 되어 라우팅 충돌 — `pid="last-appointments"` 로
매치되어 항상 404. 프론트 (`main.html:3421`) 의 `try/catch` 가 무음 처리 —
*기존 동작 보존*. 본 19-9 *수정 ⊥* — 라우터 선언 순서 변경은 예약 API URL 변경
범위 (수정 금지).

## compatibility wrapper / 라우터 무수정

- `app/routers/api.py` 본체 *완전 무수정* — 모든 예약 핸들러 그대로 동작.
- `tests/test_19_9_appointments.py` 의 13개 시그니처 테스트가 라우터 함수
  서명 무수정을 검증.
- 응답 dict 키 / 타입 *완전 보존*.

## 수정 금지 범위 준수

| 금지 항목 | 준수 |
|---|---|
| 예약 API 응답 key 변경 | ✅ schemas.py contract 보호 |
| 예약 생성/수정/삭제 동작 결과 변경 | ✅ 라우터 본체 무수정 |
| availability/leaves/treatments/patients/therapists 대규모 재작성 | ✅ 19-3~19-8 모듈 무수정 |
| 통계 집계 기준 변경 | ✅ 무수정 |
| 문자/SMS 로직 변경 | ✅ 무수정 |
| AI/RAG 로직 변경 | ✅ 무수정 |
| DB schema / migration | ✅ 무수정 |
| UI 디자인 | ✅ 무수정 |
| 운영 DB 접근 | ✅ 미접근 (`scripts/check_db_path.py` exit 0) |
| 외부 API 호출 | ✅ 미호출 |

## 자동 수정 루프 횟수

**2회**.
- 1회차: 82 cases → 80 passed / 2 failed (라우팅 충돌 + 다른 테스트 시드 충돌).
- 2회차: 라우팅 충돌은 *기존 동작 보존* 으로 핸들러 직접 호출 검증 변경,
  시드 충돌은 *상대적 비교* 로 변경. → 81 / 81 passed.

## 5회 실패 여부

**미해당** — 2회차 통과.

## 위반 / 우회 없음

- `pyproject.toml` per-file-ignores 무수정.
- 운영 DB 직접 open 없음.
- 외부 API 호출 없음.
- `app.routers` 본체 무수정.
- DB schema / migration 무수정.
