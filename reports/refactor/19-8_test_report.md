# 19-8 therapists 분리 — 테스트 리포트

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
| `venv/Scripts/python.exe -m pytest tests/test_19_8_therapists.py -v` | **78 passed** |
| `venv/Scripts/python.exe -m pytest tests -q` | **1024 passed, 1 skipped, 7 xfailed, 27 warnings** |
| `venv/Scripts/python.exe -m pytest tests/test_pyinstaller_hidden_imports.py -q` | **123 passed** |
| `venv/Scripts/python.exe -m pytest tests/test_19_5_leaves.py tests/test_19_6_treatments.py tests/test_19_7_patients_notes.py tests/test_19_8_therapists.py tests/test_pyinstaller_hidden_imports.py -q` | **378 passed** |
| `venv/Scripts/python.exe -m pytest tests -k "ai_sms or ai_leave or rag or safety or contract" -q` | **120 passed, 912 deselected, 21 warnings** |
| `venv/Scripts/python.exe -m ruff check app tests scripts` | **All checks passed!** |
| `venv/Scripts/python.exe scripts/check_db_path.py` | exit 0 (운영 DB 직접 접근 미발생) |

## 테스트 통과 카운트

- 19-8 전용 contract: **78 passed** (1회차 통과 — 수정 루프 0회).
- 전체 회귀: **1024 passed, 1 skipped, 7 xfailed**.
- PyInstaller 스펙: **123 passed** (19-8 신규 4개 모듈 등록 검증 포함).
- C-6 회귀 묶음 (19-5~19-8 + spec): **378 passed**.
- AI 회귀 (SMS / Leave / RAG / Safety / contract): **120 passed**.

## 자동 수정 루프

- 1회차 = 테스트 작성 + 실행 → 78 / 78 통과.
- ruff 1회 — `tests/test_19_8_therapists.py` 의 `import` 정렬 (I001) 1건 수정.
- **총 0회 코드 수정 루프** (모든 contract 가 1회차에서 통과).

## 핵심 신규 테스트 (78 cases)

### 1. 역할 상수 정합 (2개)
- `test_role_constants_match_models_constants` : `ROLE_DOCTOR` / `ROLE_THERAPIST` / `ROLES` 가 `app.models.constants` 와 byte-equivalent.
- `test_roles_tuple_is_immutable` : `ROLES` 가 `tuple` 으로 노출.

### 2. 역할 판정 helper (11개 — parametrize 포함)
- `is_therapist_role` / `is_doctor_role` / `is_valid_role` : 6 케이스 × 3 함수.
- `normalize_role` : None / 빈값 / "therapist" / "doctor" / unknown 5 케이스.

### 3. 색상 상수 정합 (1개) + helper 동등 (6개)
- `test_default_therapist_color_matches_calendar_view_models` : 19-3 `UNASSIGNED_THERAPIST_COLOR` 와 동일 값 (`#9CA3AF`).
- `test_therapist_color_or_default_byte_equivalent_with_view_models` : 19-3 `calendar.view_models.therapist_color` 와 byte-equivalent (None / "" / "#FF0000" / "#9CA3AF" / "#abc" / "rgb(0,0,0)").

### 4. 활성 / 권한 정규화 (15개)
- `is_active_employee` / `can_handle_eswt` / `can_handle_manual` 각 5 케이스.

### 5. 미배정 sentinel (6개)
- `UNASSIGNED_SENTINEL == "__none__"` / `UNASSIGNED_LABEL == "미배정"`.
- `is_unassigned` 5 케이스.

### 6. repository — DB 격리 fixture (10개)
- `list_all_employees` / `list_therapists` / `list_doctors` / `get_employee_by_id` (round-trip + 미존재) / `list_therapists_for_manual_scheduler` / `list_active_therapists` / `get_employees_by_ids` / `count_employees_by_role`.

### 7. service — serialize_employee 동등 (3개)
- `test_serialize_employee_byte_equivalent_with_api` : `api.py:_serialize_employee` 와 dict 비교 일치 (10키).
- `test_serialize_employees_list` : list comprehension 정합.
- `test_get_employees_endpoint_keys_match_serialize_employee` : `GET /api/employees?role=therapist` 응답 키 = serialize_employee 키 (계약 회귀 보호).

### 8. id → name / color 매핑 (3개)
- `build_employee_name_map` : 미배정 sentinel 합산 / 비합산 모두 검증.
- `build_employee_color_map` : `t.color or "#9CA3AF"` fallback 정합.

### 9. resource view 동등 (2개)
- `test_build_therapist_resource_view_matches_calendar_view_models` : 19-3 `calendar.view_models.employee_to_resource_view` 와 동일 결과.
- `test_build_therapist_resource_views_list` : list 빌더.

### 10. next_sort_order_for_role (4개)
- 0 → 1, 1 → 2, 5 → 6, 99 → 100.

### 11. 단방향 경계 D-4 (6개)
- `rules.py` / `repository.py` / `service.py` 가 `app.routers` 미참조.
- `rules.py` 가 SQLAlchemy / DB 미참조.
- `repository.py` 가 `app.models` 을 함수 안 lazy import.
- `app.modules.therapists` import 가능.

### 12. doctors / medical_staff 부재 검증 (3개)
- `test_no_doctors_module_created` : `app/modules/doctors/` / `app/modules/medical_staff/` 디렉토리 부재.
- `test_no_doctor_specific_endpoint_added` : `/api/doctors` 가 404/405.
- `test_existing_employee_role_doctor_endpoint_still_works` : `GET /api/employees?role=doctor` 정상 응답.

### 13. 라우터 시그니처 무수정 (3개)
- `_serialize_employee` / `list_employees` / `list_therapists_alias` 시그니처 보존.

### 14. 기존 흐름 영향 없음 (3개)
- `/api/employee-leaves` / `/api/therapist-leaves` / `/api/treatment-meta` 정상 응답.

## 운영 DB 보호 검사 결과

`scripts/check_db_path.py` exit 0 — 본 스크립트가 운영 DB 경로를 단순 출력만 하고 종료. 테스트 실행 중 운영 DB 경로 접근 *없음* (conftest.py 격리 fixture 가 `.test-tmp/` 로 강제).

## RAG / SMS AI / Leave AI / Safety 회귀

| 테스트 | 결과 |
|---|---|
| `tests -k "rag or safety"` (RAG 하네스) | passed (전체 1024 passed 안에 포함) |
| `tests -k "ai_sms"` | passed (전체 1024 passed 안에 포함) |
| `tests -k "ai_leave"` | passed (전체 1024 passed 안에 포함) |
| `tests -k "contract"` | passed (전체 1024 passed 안에 포함) |
| 종합 `tests -k "ai_sms or ai_leave or rag or safety or contract"` | **120 passed** |

## 주요 로그 발췌

```
============================= 78 passed in 0.20s ==============================
========== 1024 passed, 1 skipped, 7 xfailed, 27 warnings in 11.76s ===========
============================= 123 passed in 0.46s =============================
============================= 378 passed in 1.20s =============================
============== 120 passed, 912 deselected, 21 warnings in 2.12s ===============
All checks passed!
```

## 결론

- 19-8 신규 contract 78 cases 모두 통과 (수정 루프 0회).
- 전체 회귀 1024 passed (19-7 통과 시점 938 → 19-8 추가 78 = **1016 + 기타 신규 6 = 1024**).
- ruff / DB 경로 / 기존 SMS AI / 휴무 AI / RAG / 계약 테스트 모두 통과.
- **19-8 → 19-9 진입 후보** (Codex 검증 후 최종 결정).
