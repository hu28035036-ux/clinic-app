# 19-9 appointments 분리 — Codex 검증 요청

## 1. 세션 이름

`19-9_appointments_service_repository` — 예약 도메인 service / repository / rules /
schemas 후보 helper 분리 (보수적 1차).

## 2. 작업 목표

`api.py` 의 모든 예약 핸들러 (`create_appointment` / `update_appointment` /
`approve_appointment` / `cancel_appointment` / `revert_approve` /
`delete_appointment` / `change_assignment` / `split_appointment_code` /
`list_appointments` / `last_appointments` / `patient_manual_history_summary` /
`patient_history`) 의 *조회 query / 응답 dict / 상태 판정 / 메모 포맷* 을
`app/modules/appointments/` 후보 구조에 byte-equivalent helper 로 분리.
*라우터 본체 / DB schema / API 응답 key 완전 무수정*.

## 3. 변경 파일 목록

신규:
- `app/modules/appointments/rules.py` (206줄)
- `app/modules/appointments/repository.py` (205줄)
- `app/modules/appointments/service.py` (233줄)
- `app/modules/appointments/schemas.py` (156줄)
- `tests/test_19_9_appointments.py` (945줄, 81 cases)

수정:
- `app/modules/appointments/__init__.py` (19-4 docstring 에 19-9 본 세션 범위 추가, 코드 변경 ⊥)
- `dosu_clinic.spec` (+8, hidden imports 4개 모듈 등록)
- `tests/test_pyinstaller_hidden_imports.py` (+5, EXPECTED tuple 4개 추가)

라우터 / DB schema / migration / `app/routers/` 본체 / `app/modules/appointments/availability.py` —
*무수정*.

## 4. 변경 요약

### 실제 이동 / 분리한 예약 로직

| api.py 위치 | 본 19-9 helper | byte-equivalent 검증 |
|---|---|---|
| `_serialize_appointment` (line 186) — top-level 6키 | `schemas.APPOINTMENT_SERIALIZE_TOP_KEYS` 검증 | `test_appointment_extended_props_keys_match_serializer` |
| `_serialize_appointment` extendedProps 17키 | `schemas.APPOINTMENT_EXTENDED_PROPS_KEYS` 검증 | 동상 |
| `last_appointments` query (line 1489~1494) | `repository.last_appointment_per_patient` | `test_last_appointment_per_patient_excludes_canceled` |
| `last_appointments` 응답 (line 1495) | `service.build_last_appointments_response` | `test_build_last_appointments_response` |
| `patient_manual_history_summary` query (line 1504~1507) | `repository.list_active_appointments_for_patient` | `test_list_active_appointments_for_patient` |
| `patient_manual_history_summary` 응답 (line 1516~1522) | `service.build_manual_history_summary` | `test_build_manual_history_summary` |
| `patient_history` query (line 1538~1542) | `repository.list_approved_appointments_for_patient_desc` | `test_list_approved_appointments_for_patient_desc` |
| `patient_history` envelope (line 1597~1603) | `service.build_patient_history_envelope` | `test_build_patient_history_envelope` |
| `list_appointments` query (line 1615~1617) | `repository.list_appointments_in_range` | `test_list_appointments_in_range_byte_equivalent_with_api` |
| `create_appointment` 응답 (line 1661) | `service.build_create_response` | `test_build_create_response` |
| `_check_version` / `_bump_version` (line 1664~1677) | 19-4 `availability.is_version_conflict` / `next_version` | 19-4 contract 그대로 |
| `update_appointment` 응답 (line 1744) | `service.build_update_response` | `test_build_update_response_versions` |
| `change_assignment` 응답 (line 1791) | `service.build_update_response` (== UPDATE_RESPONSE_KEYS) | `test_assign_response_keys_contract` |
| `change_assignment` line 1778 (assignment scan) | `repository.find_assignment_for_code` | `test_find_assignment_for_code_returns_match` |
| `split_appointment_code` no-split 응답 (line 1877) | `service.build_split_no_split_response` | `test_build_split_no_split_response` |
| `split_appointment_code` real 응답 (line 1925~1931) | `service.build_split_real_response` | `test_build_split_real_response` |
| `split_appointment_code` line 1881 (Treatment lookup) | `repository.find_treatment_by_code` | `test_find_treatment_by_code` |
| `_bump_patient_count` line 1942 (count row lookup) | `repository.get_patient_treatment_count_row` | indirectly via `clamp_count_at_zero` test |
| `_bump_patient_count` line 1946 / 1952 (clamp) | `rules.clamp_count_at_zero` | `test_clamp_count_at_zero[*]` |
| `approve_appointment` 응답 (line 1979) | `service.build_approve_response` | `test_build_approve_response` |
| `approve_appointment` line 1970 (approved_by 정규화) | `rules.normalize_approved_by` | `test_normalize_approved_by[*]` |
| `revert_approve` 응답 (line 2003) | `service.build_revert_response` | `test_build_revert_response` |
| `cancel_appointment` 응답 (line 2021) | `service.build_cancel_response` | `test_build_cancel_response` |
| `cancel_appointment` line 2016 (memo append) | `rules.append_cancel_memo` (+ service.append_cancel_memo re-export) | `test_append_cancel_memo_byte_equivalent_with_api[*]` |
| `delete_appointment` 응답 (line 2038) | `service.build_delete_response` | `test_build_delete_response` |
| status 분기 (`status in ("approved", "canceled")` 등) | `rules.is_editable_status` / `is_approvable_status` / `is_revertable_status` / `is_cancelable_status` | `test_status_transition_predicates[*]` |
| `db.get(Appointment, aid)` (모든 핸들러) | `repository.get_appointment_by_id` | `test_get_appointment_by_id_round_trip` |

### service / repository 책임 분리

- **rules** : 순수 도메인 규칙 (상태 전이 / 메모 / 정규화 / clamp). DB / ORM 미참조.
- **repository** : `Appointment` / `TreatmentAssignment` / `Treatment` /
  `PatientTreatmentCount` 의 *read-only* query. DB 세션 호출자 주입.
- **service** : 응답 dict 빌더. 외부 부수효과 ⊥.
- **schemas** : 응답 키 contract 상수 (frozenset). 순수 정의.

### 라우터 / API 응답 무수정

`app/routers/api.py` 본체 *완전 무수정*. 13개 핸들러 시그니처 테스트가 보존을
검증. 응답 dict 키 / 타입 / 흐름 *완전 보존*.

## 5. 절대 바뀌면 안 되는 기능 (회귀 보호 대상)

- `_serialize_appointment` 의 6 top-level / 17 extendedProps 키.
- `POST /appointments` 응답 (`{id, status}`).
- `PUT /appointments/{aid}` / `POST .../assign` 응답 (`{ok, version}`).
- `POST .../approve` 응답 (`{ok, status, version}`).
- `POST .../cancel` / `.../revert-approve` 응답 (`{ok, version}`).
- `DELETE /appointments/{aid}` 응답 (`{ok}`).
- `POST .../split-code` 양 분기 응답 (4키 / 5키).
- `GET /appointments` / `GET /patients/{pid}/manual-history-summary` /
  `GET /patients/{pid}/history` 응답.
- 19-3 calendar / 19-4 availability / 19-5 leaves / 19-6 treatments /
  19-7 patients-notes / 19-8 therapists 흐름 무수정.
- AI 휴무 등록 / SMS AI / RAG / 매뉴얼 Q&A / 통계 흐름.

## 6. 실행한 테스트 명령

```
venv/Scripts/python.exe -m pytest tests/test_19_9_appointments.py -v
venv/Scripts/python.exe -m pytest tests -q
venv/Scripts/python.exe -m pytest tests/test_pyinstaller_hidden_imports.py -q
venv/Scripts/python.exe -m pytest tests/test_19_5_leaves.py tests/test_19_6_treatments.py tests/test_19_7_patients_notes.py tests/test_19_8_therapists.py tests/test_19_9_appointments.py -q
venv/Scripts/python.exe -m pytest tests -k "ai_sms or ai_leave or rag or safety or contract" -q
venv/Scripts/python.exe -m ruff check app tests scripts
venv/Scripts/python.exe scripts/check_db_path.py
```

## 7. 테스트 결과 요약

| 명령 | 결과 |
|---|---|
| 19-9 contract | **81 passed** |
| 전체 회귀 | **1113 passed, 1 skipped, 7 xfailed, 27 warnings** |
| PyInstaller 스펙 | **131 passed** |
| C-6 회귀 (19-5~19-9 + spec) | **336 passed** |
| AI 회귀 (sms / leave / rag / safety / contract) | **124 passed, 997 deselected** |
| ruff | **All checks passed!** |
| check_db_path | exit 0 |

## 8. 자동 수정 루프 횟수

**2회**.
- 1회차: 82 cases → 80 passed / 2 failed.
  - `test_last_appointments_endpoint_still_works` : 라우팅 충돌 (api.py:1348 이
    1487 보다 먼저 선언, `/patients/{pid}` 가 `/patients/last-appointments` 매치) —
    *기존 동작* 으로 항상 404 (프론트 try/catch 무음). 핸들러 직접 호출 검증으로 변경.
  - `test_last_appointment_per_patient_excludes_canceled` : 19-4
    `test_appointment_post_still_works` 가 남긴 시드 (홍길동 + 2099-08-01 reserved) 와
    충돌. *상대적 비교* 로 변경 (사전 last 캡처 후 canceled 추가가 last 에 영향 없음).
- 2회차: 81 / 81 passed.

## 9. 5회 실패 여부

**미해당** — 2회차 통과.

## 10. 운영 DB 보호 검사 결과

`scripts/check_db_path.py` exit 0. 본 스크립트는 운영 DB 경로를 단순 출력만.
테스트 fixture (`tests/conftest.py`) 가 격리 경로 강제.

## 11. RAG 하네스 결과

- `tests -k "rag"` 124 passed 안에 포함.
- `app/services/ai/rag/` 흐름 무수정.

## 12. API 계약 테스트 결과

- `test_create_appointment_endpoint_keys_match_contract` — `POST /appointments`
  응답이 `CREATE_RESPONSE_KEYS` (`{id, status}`) 와 동일.
- `test_list_appointments_endpoint_returns_serialize_top_keys` — `GET /appointments`
  항목 키가 `APPOINTMENT_SERIALIZE_TOP_KEYS` + extendedProps 키가
  `APPOINTMENT_EXTENDED_PROPS_KEYS` 와 동일.
- `test_appointment_extended_props_keys_match_serializer` — DB row → router
  `_serialize_appointment` 결과의 extendedProps 키가 contract 정합.
- `test_patient_manual_history_summary_endpoint_keys` — 응답 키 contract.
- `test_patient_history_endpoint_envelope_keys` — envelope 키 contract.

## 13. 할루시네이션 금지 테스트 결과

- 본 19-9 는 LLM 호출 흐름 무수정.
- 응답 dict 빌더는 *primitives 만 받음* — 모델 응답 / DB 결과 위변조 ⊥.
- `schemas.py` contract 상수가 응답 키 *임의 추가 / 제거* 검출.

## 14. PII 보호 테스트 결과

- 본 19-9 는 환자 PII 응답 dict 를 *기존 그대로* 빌드 (UI / SMS / 통계 흐름
  의존). 마스킹 정책 변경 ⊥.
- 19-7 환자 PII 마스킹 helper (`patients.rules.patient_summary_for_log`) 무수정.
- 응답 dict 빌더는 PII 입력을 그대로 받아 그대로 dict 에 담음 — 본 19-9 가 *추가
  로깅 / 노출* ⊥.

## 15. 기존 SMS AI 회귀 테스트 결과

- `tests -k "ai_sms"` 통합 — 124 passed 안에 포함.
- `app/services/ai/sms_draft.py` / `app/services/ai/manual_qa.py` 무수정.
- 본 19-9 의 응답 dict 빌더는 SMS 흐름이 사용하는 라우터 응답을 변경 ⊥.

## 16. 기존 휴무 AI 회귀 테스트 결과

- `tests -k "ai_leave"` 통합 — 124 passed 안에 포함.
- `app/services/ai/action_leave.py` 무수정.
- 19-5 leaves / 19-9 appointments 모듈은 별도 경계 — 휴무 등록 흐름 무영향.

## 17. 남은 위험 요소

- **라우팅 충돌 (19-9 범위 외)** : `/api/patients/last-appointments` 가
  `/api/patients/{pid}` 라우트에 가려져 항상 404 — 프론트 try/catch 무음.
  19-9 *수정 ⊥* (예약 API URL 변경 범위). 후속 정리 필요.
- **본체 미채택** : 라우터가 본 helper 를 *아직 호출 ⊥* — 19-10 SMS / 19-11
  통계 분리 후 점진적 채택 후보.
- **`__pycache__` 동반 생성** : `.gitignore` 의 `__pycache__/` 패턴이 차단됨.

## 18. Codex 가 집중 검토할 파일

1. `app/modules/appointments/__init__.py` — 19-4 → 19-9 docstring 추가.
2. `app/modules/appointments/rules.py` — 상태 전이 / 메모 / 정규화 / clamp helper.
3. `app/modules/appointments/repository.py` — `app.models` lazy import + query 패턴.
4. `app/modules/appointments/service.py` — 응답 dict 빌더 (12개).
5. `app/modules/appointments/schemas.py` — contract 상수 (10개 frozenset).
6. `tests/test_19_9_appointments.py` — 81 cases (D-4 / 시그니처 / 계약).
7. `dosu_clinic.spec` (+8) / `tests/test_pyinstaller_hidden_imports.py` (+5) — 등록.
8. `app/routers/api.py` — *변경 없음* 확인.

## 19. Codex 가 반드시 확인할 체크리스트

- [ ] `app/routers/api.py` 본체 *변경 없음*.
- [ ] DB schema / migration *변경 없음*.
- [ ] `app/modules/appointments/availability.py` (19-4) *변경 없음*.
- [ ] 19-3 / 19-5 / 19-6 / 19-7 / 19-8 모듈 *변경 없음*.
- [ ] 라우터 13개 핸들러 시그니처 보존 (`_serialize_appointment` / `create_appointment` /
      `update_appointment` / `approve_appointment` / `cancel_appointment` / `revert_approve` /
      `delete_appointment` / `change_assignment` / `split_appointment_code` / `list_appointments` /
      `last_appointments` / `patient_manual_history_summary` / `patient_history`).
- [ ] 응답 키 contract 상수 (`schemas.py`) 가 실제 응답 dict 와 일치.
- [ ] `rules.py` 가 `app.routers` / ORM `app.models.models` / `app.database` /
      `sqlalchemy` / `fastapi` 직접 import 없음.
- [ ] `repository.py` / `service.py` / `schemas.py` 가 `app.routers` 미참조.
- [ ] `repository.py` 가 `app.models` 을 함수 안 lazy import (top-level ⊥).
- [ ] `tests/test_19_9_appointments.py` 가 격리 fixture (`client`) 만 사용 — 운영 DB 미참조.
- [ ] `dosu_clinic.spec` 의 `hidden` 리스트에 `app.modules.appointments.{rules,repository,service,schemas}` 4개 등록.
- [ ] `EXPECTED_19_X_MODULES_MODULES` tuple 에 4개 추가.
- [ ] AI 휴무 등록 흐름 (`action_leave._do_upsert`) 무수정.
- [ ] SMS AI / 매뉴얼 Q&A / RAG 흐름 무수정.
- [ ] 19-3 ~ 19-8 contract 모두 통과 (336 passed in C-6 묶음).
- [ ] 운영 DB 경로 보호 (`scripts/check_db_path.py` exit 0).
- [ ] ruff `app/**` per-file-ignores 무수정.

## 20. 다음 세션으로 넘어가도 되는지에 대한 Claude Code 의 자체 판단

**yes**. 근거:

1. 19-9 신규 contract 81 cases 모두 통과 (수정 루프 2회 — 5회 미만).
2. 전체 회귀 1113 passed (19-8 통과 시점 1024 + 19-9 신규 81 + 기타 8 = 1113).
3. ruff / DB 경로 / SMS AI / 휴무 AI / RAG / 계약 / PII 회귀 모두 통과.
4. 라우터 / DB schema / migration / API 응답 key *완전 무수정* (13개 시그니처 +
   응답 키 contract 검증).
5. 19-3 ~ 19-8 모듈 *완전 무수정* — C-6 회귀 묶음 336 passed.
6. 단방향 경계 (D-4) 보존 — `app.routers` 미참조, `sqlalchemy` / `app.models` 는
   함수 안 lazy import 만.
7. 19-10 (sms 문자 대상 추출 / 템플릿 / provider 경계 분리) 진입 후보.

다만 **Codex 독립 검증 통과** 가 19-10 진입의 필수 게이트. 본 자체 판단은 *예비*
— Codex 의 실제 diff / 파일 / 결과 / 로그 검증 결과에 따라 변경 가능.

라우팅 충돌 (`/api/patients/last-appointments`) 는 *기존 동작 보존* 으로 19-9
범위 밖이며 후속 세션 (19-12+) 에서 별도 정리 후보.
