# 19-9 Codex 검증 결과

## 판정

**통과.** `latest_codex_review_request.md`가 가리키는 19-9 appointments service / repository / rules / schemas 후보 분리는 실제 파일 구조, tracked diff, import 경계, hidden import 등록, 테스트 재실행 결과 기준으로 요청 내용과 일치한다. 19-10 SMS 분리로 진입 가능하다고 판단한다.

단, 검증 중 기존 venv launcher가 한글 경로를 깨진 경로로 재실행하는 문제가 있어, 테스트는 Codex 번들 Python 3.12.13에 `venv\Lib\site-packages`와 repo root를 `PYTHONPATH`로 연결해 실행했다. pytest 버전은 venv의 8.4.2를 사용했다.

## 직접 검증한 기준

- `reports/refactor/latest_codex_review_request.md`와 `reports/refactor/19-9_codex_review_request.md`가 동일함을 확인했다.
- `reports/refactor/latest_test_report.md`와 `reports/refactor/19-9_test_report.md`가 동일함을 확인했다.
- `reports/refactor/latest_fix_summary.md`와 `reports/refactor/19-9_fix_summary.md`가 동일함을 확인했다.
- Claude Code 요약 대신 실제 `git status`, `git diff --stat`, `git diff --numstat`, 파일 목록, import 경계, PyInstaller hidden import, pytest/ruff/check_db_path 실행 결과를 직접 확인했다.

## 실제 파일 구조

파일 줄 수는 `[System.IO.File]::ReadAllLines(...).Count` 기준이다.

| 파일 | 실제 줄 수 | 요청 문서 주장 |
|---|---:|---:|
| `app/modules/appointments/rules.py` | 206 | 206 |
| `app/modules/appointments/repository.py` | 205 | 205 |
| `app/modules/appointments/service.py` | 233 | 233 |
| `app/modules/appointments/schemas.py` | 156 | 156 |
| `tests/test_19_9_appointments.py` | 945 | 945 |

요청 문서의 신규 파일 목록과 실제 파일 구조가 일치한다. 기존 `app/modules/appointments/availability.py`는 존재하지만 diff가 없고, 19-4 범위 파일로 유지된다.

## 실제 diff

tracked diff 기준:

| 파일 | 실제 diff |
|---|---:|
| `app/modules/appointments/__init__.py` | +27 / -3 |
| `dosu_clinic.spec` | +8 |
| `tests/test_pyinstaller_hidden_imports.py` | +5 |

`app/routers/api.py`와 `app/modules/appointments/availability.py`에는 diff가 없다. 신규 `rules.py`, `repository.py`, `service.py`, `schemas.py`, `tests/test_19_9_appointments.py`는 현재 untracked 파일이다.

## 의존성 경계

- `rules.py`는 `app.routers`, `fastapi`, `sqlalchemy`, `app.database`, ORM 모델을 import하지 않는다.
- `schemas.py`는 응답 키 contract 상수만 정의하며 router/DB 의존성이 없다.
- `service.py`는 `app.modules.appointments.rules`와 primitive/dict 입력만 사용하며 router/FastAPI 의존성이 없다.
- `repository.py`는 `app.models.models`를 함수 내부 lazy import로 사용한다.
- `repository.py`의 `sqlalchemy.func` import는 count query helper 내부에서만 사용된다.
- `app/routers/api.py` 본체, 라우터 URL, DB schema, migration 변경은 확인되지 않았다.

## PyInstaller hidden import

`dosu_clinic.spec`와 `tests/test_pyinstaller_hidden_imports.py` 모두 19-9 신규 모듈 4개를 포함한다.

- `app.modules.appointments.rules`
- `app.modules.appointments.repository`
- `app.modules.appointments.service`
- `app.modules.appointments.schemas`

기존 19-4 항목인 `app.modules.appointments`, `app.modules.appointments.availability`도 유지된다.

## 테스트 재실행 결과

venv launcher 문제 때문에 아래 pytest 명령은 다음 실행 형태로 검증했다.

`PYTHONPATH = .\venv\Lib\site-packages;.`  
`C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest ...`

| 검증 | 결과 |
|---|---|
| `tests/test_19_9_appointments.py -q` | 81 passed |
| `tests/test_pyinstaller_hidden_imports.py -q` | 131 passed |
| `tests/test_19_5_leaves.py tests/test_19_6_treatments.py tests/test_19_7_patients_notes.py tests/test_19_8_therapists.py tests/test_19_9_appointments.py -q` | 336 passed |
| `tests -k "ai_sms or ai_leave or rag or safety or contract" -q` | 124 passed, 997 deselected, 22 warnings |
| `tests -q` | 1113 passed, 1 skipped, 7 xfailed, 27 warnings |
| `.\venv\Scripts\ruff.exe check app tests scripts` | All checks passed |
| `scripts/check_db_path.py` | exit 0 |

전체 테스트는 sandbox temp 권한 문제로 일반 실행이 한 번 실패했으나, 권한 상승 실행에서는 요청 문서와 같은 `1113 passed, 1 skipped, 7 xfailed, 27 warnings` 결과를 확인했다.

warnings는 기존 AI/SMS/manual QA 테스트에서 test 함수가 tuple을 return하는 `PytestReturnNotNoneWarning` 계열이며, 이번 19-9 변경 실패로 보이지 않는다.

## 확인된 환경 이슈 / 잔여물

- `.\venv\Scripts\python.exe -m pytest ...`는 `Unable to create process using ... Python312\python.exe` 오류로 실패한다. `.\venv\Scripts\python.exe --version`은 동작하지만 인자를 붙인 실행이 깨지는 launcher 문제다.
- 기본 `C:\Users\user\AppData\Local\Programs\Python\Python312\python.exe`에는 pytest가 설치되어 있지 않았다.
- 검증 중 만든 `.codex-pytest-basetemp-19-9` 임시 디렉터리는 권한 문제로 삭제가 실패했고, `git status`에서 접근 권한 warning을 만들 수 있다. 기능 변경과 테스트 판정에는 영향이 없다.
- `docs/ai/`는 untracked 상태이며 19-9 기능 diff 범위 밖의 별도 계획 문서로 보인다.

## 종합

19-9는 예약 상태 판정, 취소 메모, 응답 dict 빌더, read-only 조회 helper, 응답 키 contract를 `app.modules.appointments` 경계 안에 추가했고, 기존 router/API/schema/migration 본체는 건드리지 않은 것으로 확인된다. PyInstaller hidden import 등록과 contract/회귀/AI/RAG/전체 테스트도 통과했다.

따라서 **19-10 진입 가능**으로 결론낸다. 커밋 전에는 `docs/ai/`와 검증 임시 디렉터리 권한 잔여물을 별도로 정리할지 결정하면 된다.
