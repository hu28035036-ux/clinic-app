# 19-12 Codex 검증 결과

검증 시각: 2026-05-04, `latest_codex_review_request.md` 최신본 기준.

## 판정

**통과.** 19-12 admin / backup / audit / export_import boundary 분리는 실제 파일 구조, tracked diff, PyInstaller hidden import, 보안/PII/DB 보호 경계, 테스트 재실행 결과 기준으로 요청 내용과 일치한다. 이전 요청본에서 보였던 `dosu_clinic.spec +15` 표기 불일치는 최신 요청 문서에서 `+17`로 정정되어 실제 diff와도 일치한다.

따라서 **19-13 진입 가능**으로 판단한다.

## 직접 검증한 근거

- `reports/refactor/latest_codex_review_request.md`와 `reports/refactor/19-12_codex_review_request.md`가 동일함을 확인했다.
- `reports/refactor/latest_test_report.md`와 `reports/refactor/19-12_test_report.md`가 동일함을 확인했다.
- `reports/refactor/latest_fix_summary.md`와 `reports/refactor/19-12_fix_summary.md`가 동일함을 확인했다.
- Claude Code 요약 대신 실제 `git status`, `git diff --stat`, `git diff --numstat`, 파일 줄 수, import 경계, PyInstaller hidden import, pytest/ruff/check_db_path 결과를 직접 확인했다.

## 실제 파일 구조

줄 수는 `[System.IO.File]::ReadAllLines(...).Count` 기준이다.

| 파일 | 실제 줄 수 | 요청 문서 |
|---|---:|---:|
| `app/modules/admin/__init__.py` | 58 | 58 |
| `app/modules/admin/schemas.py` | 175 | 175 |
| `app/modules/admin/service.py` | 230 | 230 |
| `app/modules/backup/__init__.py` | 64 | 64 |
| `app/modules/backup/schemas.py` | 142 | 142 |
| `app/modules/backup/service.py` | 180 | 180 |
| `app/modules/audit/__init__.py` | 52 | 52 |
| `app/modules/audit/schemas.py` | 76 | 76 |
| `app/modules/audit/service.py` | 101 | 101 |
| `app/modules/export_import/__init__.py` | 63 | 63 |
| `app/modules/export_import/schemas.py` | 128 | 128 |
| `app/modules/export_import/service.py` | 129 | 129 |
| `tests/test_19_12_admin.py` | 869 | 869 |

요청 문서의 신규 파일 목록과 실제 파일 구조는 일치한다.

## 실제 diff

tracked diff 기준:

| 파일 | 실제 diff | 요청 문서 |
|---|---:|---:|
| `dosu_clinic.spec` | +17 | +17 |
| `tests/test_pyinstaller_hidden_imports.py` | +13 | +13 |

`app/routers/api.py`, `app/routers/ai.py`, `app/services/backup.py`, `app/services/auth.py`에는 diff가 없다. 신규 `app/modules/admin/`, `app/modules/backup/`, `app/modules/audit/`, `app/modules/export_import/`, `tests/test_19_12_admin.py`는 현재 untracked 신규 파일이다.

## PyInstaller hidden import

`dosu_clinic.spec`와 `tests/test_pyinstaller_hidden_imports.py` 모두 19-12 신규 모듈 12개를 포함한다.

- `app.modules.admin`
- `app.modules.admin.service`
- `app.modules.admin.schemas`
- `app.modules.backup`
- `app.modules.backup.service`
- `app.modules.backup.schemas`
- `app.modules.audit`
- `app.modules.audit.service`
- `app.modules.audit.schemas`
- `app.modules.export_import`
- `app.modules.export_import.service`
- `app.modules.export_import.schemas`

## 보안 / PII / DB 보호 경계

- 신규 helper 모듈 import 라인에는 `app.routers` 의존성이 없다.
- 신규 helper 모듈 import 라인에는 `urllib.request`, `requests`, `httpx`, `shutil`, `sqlite3`가 없다. 해당 문자열은 주석, docstring, 기존 router/service 본체 검증용 테스트에만 등장한다.
- 신규 helper 모듈에는 `db.commit(`, `db.add(`, `db.delete(`, `db.flush(` 실행 코드가 없다. 주석/docstring에 있는 설명 문자열은 contract test가 구분해 통과했다.
- `AI_SETTINGS_FORBIDDEN_KEYS`는 `api_key`를 포함하고 응답 key와 분리된다.
- `PUBLIC_CONFIG_DROP_KEYS`는 `admin_password_hash`, `sync_secret`를 포함한다.
- `AUDIT_DETAIL_CAP`은 500으로 유지된다.
- 기존 `api.py:restore`, `services/backup.py:restore_latest`, `restore_by_name`의 `engine.dispose()` 호출은 diff 없이 유지된다.
- `_backup_db_before_update`, `clinic_before_update_v*`, `clinic_before_restore_*` 안전망도 기존 본체에서 확인했다.

## 테스트 재실행 결과

venv launcher 문제가 있어 pytest는 Codex 번들 Python에 venv site-packages와 workspace를 `PYTHONPATH`로 연결해 실행했다.

| 검증 | 결과 |
|---|---|
| `pytest tests/test_19_12_admin.py -q` | 128 passed |
| `pytest tests/test_pyinstaller_hidden_imports.py -q` | 179 passed |
| `pytest tests/test_admin_auth_required.py tests/test_admin_ui_smoke.py tests/test_db_restore_safety.py -q` | 41 passed |
| `pytest tests -k "ai_sms or ai_leave or rag or safety or contract" -q` | 144 passed, 1351 deselected, 22 warnings |
| `pytest tests -q` | 1487 passed, 1 skipped, 7 xfailed, 27 warnings |
| `.\venv\Scripts\ruff.exe check app tests scripts` | All checks passed |
| `scripts/check_db_path.py` | exit 0 |

warnings는 기존 AI/SMS/manual QA 계열 `PytestReturnNotNoneWarning`와 일부 cache warning이며, 19-12 기능 실패로 보이지 않는다.

## 환경 이슈 / 잔여물

- `.\venv\Scripts\python.exe -m pytest ...` 형태는 한글 경로 launcher 문제로 신뢰하기 어려워, 이번 검증은 Codex 번들 Python + venv site-packages 방식으로 수행했다.
- `.codex-pytest-basetemp-19-9`는 이전 검증 중 생긴 권한 잔여물로 `git status` warning을 만들 수 있으나 기능 diff와 테스트 판정에는 영향이 없다.
- `docs/ai/`는 untracked 상태이며 19-12 기능 diff 범위 밖의 별도 계획 문서로 보인다.

## 종합

19-12는 관리자 응답/마스킹, 백업 응답/파일명 규칙, audit detail cap/직렬화, data-convert/export_import 응답 helper를 신규 후보 모듈로 분리했고, 기존 router/backup/auth 본체는 건드리지 않은 것으로 확인했다. API key, 문자나라 계정, sync_secret, admin_password_hash, audit detail/PII 관련 보호 contract도 통과했다.

결론: **19-13 진입 가능**.
