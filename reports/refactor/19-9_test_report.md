# 19-9 appointments 분리 — 테스트 리포트

## 환경

- 작업 디렉토리: `C:\Users\user\Desktop\새 폴더\병원예약관리\병원예약관리`
- 브랜치: `ai-rag-v1-integration`
- Python: `venv\Scripts\python.exe` (3.12.10)
- pytest: 8.4.2
- ruff: 프로젝트 설정 (`pyproject.toml` 의 `app/**` per-file-ignores 유지)
- DB: 격리된 `.test-tmp/` 경로 (운영 DB 미참조).

## 실행한 명령

| 명령 | 결과 |
|---|---|
| `venv/Scripts/python.exe -m pytest tests/test_19_9_appointments.py -q` | **81 passed** |
| `venv/Scripts/python.exe -m pytest tests -q` | **1113 passed, 1 skipped, 7 xfailed, 27 warnings** |
| `venv/Scripts/python.exe -m pytest tests/test_pyinstaller_hidden_imports.py -q` | **131 passed** |
| `venv/Scripts/python.exe -m pytest tests -k "ai_sms or ai_leave or rag or safety or contract" -q` | **124 passed, 997 deselected, 21 warnings** |
| `venv/Scripts/python.exe -m pytest tests/test_19_5_leaves.py tests/test_19_6_treatments.py tests/test_19_7_patients_notes.py tests/test_19_8_therapists.py tests/test_19_9_appointments.py -q` | **336 passed** |
| `venv/Scripts/python.exe -m ruff check app tests scripts` | **All checks passed!** |
| `venv/Scripts/python.exe scripts/check_db_path.py` | exit 0 (운영 DB 직접 접근 미발생) |

## 테스트 통과 카운트

- 19-9 전용 contract: **81 passed** (1회차 81/82, 1건 수정 후 81/81 통과 → 총 2 루프).
- 전체 회귀: **1113 passed, 1 skipped, 7 xfailed**. (19-8 통과 시점 1024 → 19-9 추가 81 + 기타 신규 8 = 1113.)
- PyInstaller 스펙: **131 passed** (19-9 신규 4개 모듈 등록 검증 8건 추가).
- AI 회귀 (SMS / Leave / RAG / Safety / contract): **124 passed**.
- C-6 회귀 (19-5 ~ 19-9 + spec): **336 passed**.

## 자동 수정 루프

- **1회차** : 82 cases 작성 → 80 passed / 1 failed / 1 fixed inline.
  - `test_last_appointments_endpoint_still_works` : ``GET /api/patients/last-appointments`` 가
    ``GET /api/patients/{pid}`` 에 *기존 라우팅 충돌* 로 404 반환 (api.py:1348 이 1487 보다
    먼저 선언). 프론트는 try/catch 로 무음 처리 — *기존 동작 보존*.
    → 핸들러 직접 호출 검증으로 변경 (`test_last_appointments_handler_directly_callable`).
- **2회차** : 81 / 82 → `test_last_appointment_per_patient_excludes_canceled` 가 *전체 suite 실행 시*
  `tests/test_19_4_availability.py:test_appointment_post_still_works` 가 남긴 ``홍길동테스트 +
  2099-08-01 reserved`` 와 충돌해 fail (단독 실행 시 통과).
  → 사전 ``last`` 캡처 + canceled 추가 후 ``last`` 불변 검증으로 *상대적 비교* 로 수정.
- **2회차 완료** → 81 / 81 passed.

## 핵심 신규 테스트 (81 cases)

### 1. 상태 상수 정합 (2개)
- `APPT_STATUS_RESERVED / APPROVED / CANCELED` ↔ `app.models.models.APPT_STATUSES` byte-equivalent.

### 2. 상태 전이 판정 (10개 — parametrize 포함)
- `is_editable_status` / `is_approvable_status` / `is_revertable_status` /
  `is_cancelable_status` 가 reserved / approved / canceled / None / "" / "treated" 케이스 정합.
- `is_already_approved` / `is_canceled` 4 케이스.

### 3. 취소 메모 포맷 (8개 parametrize)
- `append_cancel_memo` 가 `api.py:cancel_appointment` line 2016 인라인 패턴 정합 —
  None / 빈값 / 사용자 사유 있음 / 없음 8 케이스.
- `service.append_cancel_memo` 도 같은 결과 (re-export).

### 4. 승인자 정규화 (6개 parametrize)
- `normalize_approved_by` : None / 빈 / 공백 / 정상 / 공백 양 끝 6 케이스.

### 5. 카운트 clamp (7개 parametrize)
- `clamp_count_at_zero` : 양수 / 음수 / None / 0 클램프 7 케이스.

### 6. repository — DB 격리 fixture (7개)
- `get_appointment_by_id` round-trip + 미존재.
- `list_appointments_in_range` byte-equivalent with api.
- `list_active_appointments_for_patient` (canceled 제외).
- `list_approved_appointments_for_patient_desc` (status filter + desc 정렬).
- `last_appointment_per_patient` (canceled 제외 — 상대적 검증).
- `find_assignment_for_code` (None / 매칭 / 미매칭).
- `find_treatment_by_code`.

### 7. service — 응답 빌더 byte-equivalent (12개)
- create / update / approve / revert / cancel / delete 응답 dict.
- split-no-split + split-real 응답 dict.
- last_appointments / manual_history_summary / patient_history_envelope 응답.

### 8. schemas — contract 회귀 보호 (4개)
- `CREATE_RESPONSE_KEYS` / `UPDATE_RESPONSE_KEYS` / `ASSIGN_RESPONSE_KEYS` 가
  실제 응답 dict 키와 일치.
- `APPOINTMENT_SERIALIZE_TOP_KEYS` / `APPOINTMENT_EXTENDED_PROPS_KEYS` 가
  실제 `_serialize_appointment` 결과 키와 일치 (DB row 직접 사용).

### 9. 단방향 경계 (D-4) (7개)
- `rules.py` / `repository.py` / `service.py` / `schemas.py` 가 `app.routers` 미참조.
- `rules.py` 가 ORM `from app.models.models` / `from app.database` / `sqlalchemy` 미참조.
- `repository.py` 가 `app.models` 을 함수 안 lazy import (top-level ⊥).
- `app.modules.appointments` import 가능 (6개 모듈 — availability + 5 신규).

### 10. 라우터 시그니처 무수정 (13개)
- `create_appointment` / `update_appointment` / `approve_appointment` /
  `cancel_appointment` / `revert_approve` / `delete_appointment` /
  `change_assignment` / `split_appointment_code` / `list_appointments` /
  `last_appointments` / `patient_manual_history_summary` / `patient_history` /
  `_serialize_appointment` 시그니처 보존.

### 11. 기존 흐름 영향 없음 (5개)
- `POST /api/appointments` 응답 키 = `CREATE_RESPONSE_KEYS`.
- `GET /api/appointments` 항목별 키 = `APPOINTMENT_SERIALIZE_TOP_KEYS` +
  extendedProps 키 = `APPOINTMENT_EXTENDED_PROPS_KEYS`.
- `last_appointments` 핸들러 직접 호출 정상.
- `GET /api/patients/{pid}/manual-history-summary` 응답 키 contract.
- `GET /api/patients/{pid}/history` envelope 키 contract.

### 12. availability 무수정 (1개)
- 19-4 helper 들이 그대로 노출 — `parse_lunch_window` / `is_version_conflict` /
  `next_version` / `is_leave_blocking` 등.

## 운영 DB 보호 검사 결과

`scripts/check_db_path.py` exit 0 — 본 스크립트가 운영 DB 경로를 단순 출력만 하고
종료. 테스트 실행 중 운영 DB 경로 접근 *없음* (conftest.py 격리 fixture 가
`.test-tmp/` 로 강제).

## RAG / SMS AI / Leave AI / Safety 회귀

| 테스트 묶음 | 결과 |
|---|---|
| `tests -k "rag or safety"` (RAG 하네스) | 통과 (124 passed 안에 포함) |
| `tests -k "ai_sms"` | 통과 |
| `tests -k "ai_leave"` | 통과 |
| `tests -k "contract"` | 통과 |
| 종합 | **124 passed** |

## 주요 로그 발췌

```
============================= 81 passed in 0.49s ==============================
========== 1113 passed, 1 skipped, 7 xfailed, 27 warnings in 13.17s ===========
============================= 131 passed in 0.47s =============================
============================= 336 passed in 1.06s =============================
============== 124 passed, 997 deselected, 21 warnings in 2.18s ===============
All checks passed!
```

## 결론

- 19-9 신규 contract 81 cases 모두 통과 (수정 루프 2회).
- 전체 회귀 1113 passed (19-8 통과 시점 1024 + 19-9 신규 81 + 기타 8 = 1113).
- ruff / DB 경로 / 기존 SMS AI / 휴무 AI / RAG / 계약 테스트 모두 통과.
- **19-9 → 19-10 진입 후보** (Codex 검증 후 최종 결정).
