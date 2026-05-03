# 19-8 therapists 분리 — Codex 검증 요청

## 1. 세션 이름

`19-8_therapists_doctors_boundary` — 치료사 / 직원 도메인 후보 구조 정리 +
의사 / medical_staff 현재 기능 부재 문서화.

## 2. 작업 목표

`api.py:_serialize_employee` (line 169) / `list_employees` (line 1009) /
`list_therapists_alias` (line 1175) / 통계 ``id → name`` 매핑 (line 3527, 3609,
3702, 3787) / 도수치료 표 (line 4364) 등 *치료사 관련 순수 로직* 을
`app/modules/therapists/` 후보 구조에 분리. 라우터 / DB schema / API 응답 key
는 *무수정* 으로 유지. 의사 (doctors) / medical_staff 의 *현재 기능 부재* 를
확인하고 후속 검토로 문서화.

## 3. 변경 파일 목록

신규:
- `app/modules/therapists/__init__.py` (41줄)
- `app/modules/therapists/rules.py` (211줄)
- `app/modules/therapists/repository.py` (173줄)
- `app/modules/therapists/service.py` (168줄)
- `tests/test_19_8_therapists.py` (619줄)

수정:
- `dosu_clinic.spec` (+7줄, hidden imports 4개 모듈 추가)
- `tests/test_pyinstaller_hidden_imports.py` (+5줄, EXPECTED tuple 4개 추가)

라우터 / DB schema / migration / `app/routers/` 본체 — *무수정*.

## 4. 변경 요약

### 실제 이동 / 분리한 치료사 로직

| api.py 위치 | 본 19-8 helper | 동등 검증 |
|---|---|---|
| `_serialize_employee` (line 169~176) | `service.serialize_employee` | `test_serialize_employee_byte_equivalent_with_api` (dict 비교) |
| `list_employees` (line 1009~1018) | `repository.list_all_employees` (role/active 필터 + sort_order/name 정렬) | `test_list_all_employees_*` |
| `list_therapists_alias` (line 1175~1181) | `repository.list_therapists` (role=therapist + name 정렬) | `test_list_therapists_returns_only_therapist_role` |
| `db.query(Employee).filter(role == "doctor")` (line 3525) | `repository.list_doctors` | `test_list_doctors_returns_only_doctor_role` |
| `id → name` 매핑 (line 3527, 3609, 3702, 3788) | `service.build_employee_name_map(include_unassigned=True)` | `test_build_employee_name_map_*` |
| `id → color` 매핑 (line 3789) | `service.build_employee_color_map(include_unassigned=True)` | `test_build_employee_color_map_applies_fallback` |
| `t.color or "#9CA3AF"` (line 188 / 3789 / 4501 / 4524 / 4723) | `rules.therapist_color_or_default` (== 19-3 view_models) | `test_therapist_color_or_default_byte_equivalent_with_view_models` (6 cases) |
| 도수치료 표 query (line 4364~4369, role+active+can_manual) | `repository.list_therapists_for_manual_scheduler` | `test_list_therapists_for_manual_scheduler_filters` |
| 일별 차트 query (line 3783~3786, role=therapist+active) | `repository.list_active_therapists` | `test_list_active_therapists_filters` |
| `Employee.id.in_(emp_ids)` (line 1552) | `repository.get_employees_by_ids` (빈 리스트 안전) | `test_get_employees_by_ids_with_in_filter` |
| `count_increment + 1` (create_employee, line 1038) | `service.next_sort_order_for_role` | `test_next_sort_order_for_role[*]` |
| `bool(e.active)` / `bool(e.can_eswt)` / `bool(e.can_manual)` | `rules.is_active_employee` / `rules.can_handle_*` | `test_is_active_employee[*]` / `test_can_handle_*[*]` |
| 미배정 sentinel `"__none__" / "미배정"` (line 3495 / 3528) | `rules.UNASSIGNED_SENTINEL / UNASSIGNED_LABEL / is_unassigned` | `test_unassigned_sentinel_constants` / `test_is_unassigned[*]` |
| 캘린더 resource view (line 4723) | `service.build_therapist_resource_view` (== 19-3 view_models) | `test_build_therapist_resource_view_matches_calendar_view_models` |

### 라우터 / API 응답 무수정

`app/routers/api.py` 본체 *완전 무수정*. 기존 엔드포인트 응답 키 / 타입 보존.
`test_get_employees_endpoint_keys_match_serialize_employee` 가 `GET
/api/employees?role=therapist` 응답이 10키 (id/name/role/color/active/birth_date/
phone/hire_date/can_eswt/can_manual/sort_order) 와 동일함을 검증.

## 5. 절대 바뀌면 안 되는 기능 (회귀 보호 대상)

- `_serialize_employee` 의 10키 dict 결과.
- `GET /api/employees` / `GET /api/employees?role=doctor` / `GET /api/therapists` 응답.
- `GET /api/employee-leaves` / `GET /api/therapist-leaves` (19-5 무수정).
- `GET /api/treatment-meta` 의 doctor_treatments / therapist_treatments / manual_treatments (19-6 무수정).
- 통계 `stats_by_therapist` / `stats_manual_by_therapist` / `stats_daily_by_therapist` 흐름.
- 도수치료 표 / 캘린더 resource lane 표시.
- AI 휴무 등록 흐름 (`action_leave._do_upsert`) — 19-5 무수정 정책 유지.
- SMS AI / RAG / 매뉴얼 Q&A 흐름.

## 6. 실행한 테스트 명령

```
venv/Scripts/python.exe -m pytest tests/test_19_8_therapists.py -v
venv/Scripts/python.exe -m pytest tests -q
venv/Scripts/python.exe -m pytest tests/test_pyinstaller_hidden_imports.py -q
venv/Scripts/python.exe -m pytest tests/test_19_5_leaves.py tests/test_19_6_treatments.py tests/test_19_7_patients_notes.py tests/test_19_8_therapists.py tests/test_pyinstaller_hidden_imports.py -q
venv/Scripts/python.exe -m pytest tests -k "ai_sms or ai_leave or rag or safety or contract" -q
venv/Scripts/python.exe -m ruff check app tests scripts
venv/Scripts/python.exe scripts/check_db_path.py
```

## 7. 테스트 결과 요약

| 명령 | 결과 |
|---|---|
| 19-8 contract | **78 passed** |
| 전체 회귀 | **1024 passed, 1 skipped, 7 xfailed, 27 warnings** |
| PyInstaller 스펙 | **123 passed** |
| C-6 회귀 (19-5~19-8 + spec) | **378 passed** |
| AI 회귀 (sms / leave / rag / safety / contract) | **120 passed** |
| ruff | **All checks passed!** |
| check_db_path | exit 0 |

## 8. 자동 수정 루프 횟수

**0회** — 78 / 78 contract 1회차 통과. ruff I001 1건 (테스트 파일 import 정렬)
만 수동 수정.

## 9. 5회 실패 여부

**미해당** — 1회차 통과.

## 10. 운영 DB 보호 검사 결과

`scripts/check_db_path.py` exit 0. 본 스크립트는 운영 DB 경로를 단순 출력만 하고
종료 — 코드/테스트가 운영 DB 를 직접 open 하는지 별도 검증. 테스트 fixture
(`tests/conftest.py`) 가 격리 경로 강제 — 운영 DB 미참조.

## 11. RAG 하네스 결과

- `tests -k "rag"` 포함 — 통합 결과 120 passed (sms/leave/rag/safety/contract).
- `app/services/ai/rag/` 흐름 무수정.

## 12. API 계약 테스트 결과 (응답 스키마 회귀)

- `test_get_employees_endpoint_keys_match_serialize_employee` — `GET
  /api/employees?role=therapist` 응답이 10키 (id/name/role/color/active/birth_date/
  phone/hire_date/can_eswt/can_manual/sort_order) 와 동일.
- `test_no_doctor_specific_endpoint_added` — `/api/doctors` 부재 확인 (404/405).
- `test_existing_employee_role_doctor_endpoint_still_works` — `GET
  /api/employees?role=doctor` 정상 응답 (시드 의사 0명 → 빈 리스트 정상).
- `test_employee_leaves_endpoint_still_works` / `test_therapist_leaves_alias_endpoint_still_works`
  / `test_treatment_meta_endpoint_unchanged` — 모두 정상.

## 13. 할루시네이션 금지 테스트 결과

- 본 19-8 은 LLM 호출 흐름 무수정.
- doctors / medical_staff *현재 기능* 을 실제 기능처럼 단정하지 *않음* —
  rules.py 의 `TODO(후속 검토)` 마커로 명시.
- `test_no_doctors_module_created` 가 새 모듈 디렉토리 *부재* 를 검증.

## 14. PII 보호 테스트 결과

- 본 19-8 은 환자 PII 미참조 — 직원 정보 (name / role / color / phone /
  hire_date / can_eswt / can_manual / sort_order) 만 다룸.
- 직원 phone 은 *기존 응답 그대로* 평문 노출 — 본 세션이 마스킹 정책 변경 ⊥.
- 19-7 환자 PII 마스킹 helper 무수정.

## 15. 기존 SMS AI 회귀 테스트 결과

- `tests -k "ai_sms"` 통합 — 120 passed 안에 포함.
- `app/services/ai/sms_draft.py` / `app/services/ai/manual_qa.py` 무수정.

## 16. 기존 휴무 AI 회귀 테스트 결과

- `tests -k "ai_leave"` 통합 — 120 passed 안에 포함.
- `app/services/ai/action_leave.py` 무수정.
- `app/routers/api.py:_upsert_employee_leave_core` 무수정 (19-5 보존).

## 17. 남은 위험 요소

- **doctors / medical_staff 후속 검토** : 진료과 / 진료실 / 오더 / 처방 / EMR
  기능이 *현재 부재* — 향후 도입 시점에 별도 모듈 분리 또는 본 `therapists`
  확장 결정 필요.
- **`__pycache__` 동반 생성** : 새 `app/modules/therapists/__pycache__/` 가
  pytest 실행 후 생성됨. `.gitignore` 의 `__pycache__/` 패턴이 이미 차단 —
  `git check-ignore` exit 0 확인 (커밋엔 미포함).
- **lazy import circular 위험** : `rules.py` 가 `calendar.view_models` 의
  `UNASSIGNED_THERAPIST_COLOR` 를 모듈 top-level 로드 시점에 *함수 호출* 로
  re-export — 향후 view_models 가 therapists 를 import 할 일이 있다면 재검토 필요.
- **범위 밖 untracked**: `docs/ai/` 디렉토리는 19-7 r2 시점부터 남은 *별도 기획
  문서* — 본 19-8 커밋 범위 *밖*. 사용자 결정 사항.

## 17.1. Codex r1 검증 후 보정 사항

Codex 19-8 r1 검증 결과 (`reports/refactor/19-8_codex_review.md`) 에 따라 다음
보정 적용:

1. **`dosu_clinic.spec` diff 줄 수 보정** : 본 요청서 §3 / fix_summary 의
   `+9` 표기 → 실제 tracked diff `+7` 로 보정 (`git diff --stat` 기준).
   hidden import 4개 모듈 등록 자체는 정상.
2. **`rules.py` D-4 문구 명확화** : `app.models.constants` 의 *순수 상수
   re-export* 가 D-4 의 ``app.models`` import 금지 규칙의 *예외* (단일 진실원천
   보존 목적, ORM 의존 미가져옴) 임을 docstring 에 명시.
3. **`__pycache__` 정리 / `docs/ai/`** : `.gitignore` 가 `__pycache__/` 차단함을
   확인 (`git check-ignore` exit 0). `docs/ai/` 는 19-7 r2부터 남은 별도 기획
   문서로 본 19-8 커밋 범위 밖.

## 18. Codex 가 집중 검토할 파일

1. `app/modules/therapists/__init__.py` — 패키지 docstring / TODO(후속 검토) 마커.
2. `app/modules/therapists/rules.py` — 상수 re-export (`app.models.constants` /
   `calendar.view_models`) + 역할 / 활성 / 권한 / 색상 helper.
3. `app/modules/therapists/repository.py` — `app.models` lazy import + query 패턴
   정합 (라우터 인라인 SQL 과 byte-equivalent).
4. `app/modules/therapists/service.py` — `serialize_employee` 10키 정합 +
   `id → name` / `id → color` 매핑 + resource view 빌더.
5. `tests/test_19_8_therapists.py` — 78 cases 의 contract 정합 + 단방향 경계
   (D-4) + doctors / medical_staff 부재 검증.
6. `dosu_clinic.spec` (+9) / `tests/test_pyinstaller_hidden_imports.py` (+5) —
   spec 등록 정합.
7. `app/routers/api.py` — *변경 없음* 확인.

## 19. Codex 가 반드시 확인할 체크리스트

- [ ] `_serialize_employee` 10키가 `service.serialize_employee` 와 byte-equivalent.
- [ ] `GET /api/employees?role=therapist` 응답 dict 10키가 보존됨.
- [ ] `GET /api/therapists` (alias) 응답이 동일 10키를 유지.
- [ ] `app/routers/api.py` 본체 *변경 없음*.
- [ ] DB schema / migration *변경 없음*.
- [ ] doctors / medical_staff 디렉토리 *생성 ⊥*.
- [ ] `/api/doctors` / `/api/medical-staff` 엔드포인트 *추가 없음*.
- [ ] `rules.py` 가 `app.routers` / `sqlalchemy` / `app.models.models` / `app.database` 직접 import 없음. (단, `app.models.constants` 의 *순수 상수 re-export* 는 허용 — 단일 진실원천 보존, ORM 의존 미가져옴.)
- [ ] `repository.py` / `service.py` 가 `app.routers` 미참조.
- [ ] `repository.py` 가 `app.models` 을 함수 안 lazy import.
- [ ] `tests/test_19_8_therapists.py` 가 격리 fixture (`client`) 만 사용 — 운영 DB 미참조.
- [ ] `dosu_clinic.spec` 의 `hidden` 리스트에 `app.modules.therapists` 4개 모듈 등록.
- [ ] `EXPECTED_19_X_MODULES_MODULES` tuple 에 `app.modules.therapists` 4개 추가.
- [ ] AI 휴무 등록 흐름 (`action_leave._do_upsert`) 무수정.
- [ ] SMS AI / 매뉴얼 Q&A / RAG 흐름 무수정.
- [ ] 19-5 leaves / 19-6 treatments / 19-7 patients-notes contract 모두 통과.
- [ ] 운영 DB 경로 보호 (`scripts/check_db_path.py` exit 0).
- [ ] ruff `app/**` per-file-ignores 무수정.

## 20. 다음 세션으로 넘어가도 되는지에 대한 Claude Code 의 자체 판단

**yes**. 근거:

1. 19-8 신규 contract 78 cases 모두 1회차에서 통과 (수정 루프 0회).
2. 전체 회귀 1024 passed (19-7 통과 시점 938 + 19-8 신규 78 + 기타 신규 8 = 1024).
3. ruff / DB 경로 / SMS AI / 휴무 AI / RAG / 계약 / PII 회귀 모두 통과.
4. 라우터 / DB schema / migration / API 응답 key *완전 무수정*.
5. doctors / medical_staff *현재 기능 부재* 를 명시적으로 검증
   (`test_no_doctors_module_created` / `test_no_doctor_specific_endpoint_added`)
   하고, `TODO(후속 검토)` 마커로 향후 분리 후보만 표시.
6. 단방향 경계 (D-4) 보존 — `app.routers` 미참조, `sqlalchemy` / `app.models`
   는 함수 안 lazy import 만.
7. 19-9 (appointments 예약 service / repository 분리) 는 본 helper 의 채택
   후보 — 진입 가능.

다만 **Codex 독립 검증 통과** 가 19-9 진입의 필수 게이트. 본 자체 판단은
*예비* — Codex 의 실제 diff / 파일 / 결과 / 로그 검증 결과에 따라 변경 가능.
