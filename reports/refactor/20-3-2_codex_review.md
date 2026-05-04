# 20-3-2 Codex 검증 결과

## 1. 검증 대상

- 요청서: `reports/refactor/latest_codex_review_request.md`
- 세션 요청서: `reports/refactor/20-3-2_codex_review_request.md`
- 세션명: `20-3-2_permission_level`
- 검증 일시: 2026-05-04

## 2. 결론

**통과.**

Claude Code 요약만 보지 않고 실제 변경 파일, diff, 테스트 결과, 로그를 직접 비교했다. 20-P-2 §4-6 권장값에 맞춰 F-11 권한 다중 등급이 백엔드 범위로 구현되어 있으며, 기존 `Employee.role`, 관리자 로그인/PBKDF2/5회 잠금/8시간 세션/`require_admin` 흐름은 유지한 상태에서 `permission_level` 과 변경 endpoint 만 추가됐다.

다음 세션은 `20-3-3 F-1 doctors` 이며, 진입 전 사용자 §5-7 EMR 도입 범위 결정이 필요하다.

## 3. 실제 변경 파일 확인

### 신규 파일

- `app/migrations/m015_employee_permission_level.py`
- `tests/test_20_3_2_permission_level.py`
- `reports/refactor/20-3-2_fix_summary.md`
- `reports/refactor/20-3-2_test_report.md`
- `reports/refactor/20-3-2_codex_review_request.md`

### 수정 파일

- `app/models/models.py`
- `app/models/schemas.py`
- `app/modules/therapists/service.py`
- `app/routers/api.py`
- `tests/test_19_8_therapists.py`
- `reports/refactor/latest_fix_summary.md`
- `reports/refactor/latest_test_report.md`
- `reports/refactor/latest_codex_review_request.md`

`git diff --stat` 의 tracked 범위에서는 신규 untracked 파일이 제외되므로, 실제 파일 목록은 `git status` 와 `Get-ChildItem` 으로 별도 확인했다.

## 4. 구현 검증

- `Employee.permission_level` 컬럼이 `String(20), nullable=False, default="staff"` 로 추가됨.
- m015 마이그레이션은 `employees` 테이블 존재 여부와 `permission_level` 컬럼 존재 여부를 확인한 뒤 `ALTER TABLE employees ADD COLUMN permission_level VARCHAR(20) DEFAULT 'staff' NOT NULL` 을 수행하므로 idempotent 하다.
- `EmployeePermissionIn` 스키마가 추가됨.
- `_serialize_employee()` 와 `app.modules.therapists.service.serialize_employee()` 가 모두 `permission_level` 을 포함하며 기본 fallback 은 `"staff"` 이다.
- `EMPLOYEE_PERMISSION_LEVELS = ("staff", "admin", "super")` 로 3등급만 허용하며 `viewer` 는 포함하지 않는다.
- `POST /api/admin/employees/{eid}/permission` endpoint 는 `Depends(require_admin)` 을 사용하고, 허용 등급 외 값은 400으로 차단한다.
- endpoint 성공 시 employee `permission_level` 을 갱신하고 `_log()` 및 `audit("employee.permission_update", eid, "level=...")` 를 남긴다. audit detail 은 등급명만 포함해 PII 노출은 없다.
- 기존 직원 응답 key 는 보존되고 `permission_level` 만 추가되어 12키 계약으로 갱신됐다.

## 5. 테스트/로그 재실행 결과

직접 재실행한 결과:

```text
ruff check app tests scripts
All checks passed!
```

```text
pytest tests/test_20_3_2_permission_level.py tests/test_19_8_therapists.py tests/test_pyinstaller_hidden_imports.py tests/test_migration_spec_discovery.py -q
306 passed, 1 warning in 0.85s
```

```text
pytest tests -q
1748 passed, 1 skipped, 10 xfailed, 27 warnings in 13.85s
```

```text
scripts/check_db_path.py
exit 0
```

추가로 테스트 격리 DB에서 실제 성공 경로를 직접 확인했다.

```text
POST /api/admin/login -> 200
POST /api/admin/employees/{eid}/permission {"permission_level":"super"} -> 200
response.permission_level == "super"
```

전체 테스트 결과는 `reports/refactor/20-3-2_test_report.md` 의 reported result 와 일치한다. 경고는 기존 테스트 함수 return warning 및 pytest cache 경로 warning 이며, 이번 permission_level 구현 실패는 아니다.

## 6. 보고서 정합성

- `latest_fix_summary.md` 와 `20-3-2_fix_summary.md` 는 동일했다.
- `latest_test_report.md` 와 `20-3-2_test_report.md` 는 동일했다.
- `latest_codex_review_request.md` 와 `20-3-2_codex_review_request.md` 는 동일했다.
- test report 의 `1748 passed / 1 skipped / 10 xfailed` 는 직접 재실행 결과와 일치했다.

## 7. Caveat

- PyInstaller 실제 exe build 는 실행하지 않았다. 대신 hidden import/spec discovery 테스트 215개가 통과해 m015 발견과 import 가능성은 확인했다.
- UI 등급 select, 직원 관리 화면 분기, 등급별 화면 접근 정책은 이번 백엔드 v1 범위 밖이다.
- F-15 의사 가드와 `permission_level` 결합 정책은 후속 결정이 필요하다.
- 직접 endpoint 성공 호출은 별도 테스트 격리 DB(`tests/temp/...`)에서 수행했다. 단독 앱 import 시 운영 DB 경로를 쓰면 환경에 따라 `unable to open database file` 이 날 수 있으므로, 실제 검증 판정은 pytest conftest 격리 환경과 별도 격리 DB 호출을 기준으로 했다.
- `git status` 의 `C:\Users\user/.config/git/ignore` permission warning 은 기존 환경 경고로 보이며 검증 판정에는 영향이 없다.

## 8. 최종 판정

**20-3-2 검증 통과.**

백엔드 F-11 권한 다중 등급 구현은 요청서 범위와 테스트 결과에 부합한다. 다음 단계는 `20-3-3 F-1 doctors` 이며, 시작 전 사용자 §5-7 EMR 도입 범위 결정이 필요하다.
