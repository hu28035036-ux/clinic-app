# 19-5 Codex 검증 결과

## 판정

**통과.** 19-5 leaves 휴무 규칙 분리는 실제 파일 기준으로 `app.modules.leaves` 경계 안에 추가되어 있고, 전체 테스트/ruff/DB 경로 가드는 통과했다. 따라서 **19-6 treatments / completion_rules 분리로 진입 가능**하다고 판단한다.

단, 검증 중 실행한 pytest/import 과정으로 `app/modules/leaves/__pycache__`가 현재 작업 트리에 존재한다. 커밋 전 제외 또는 정리가 필요하다.

## 직접 검증한 기준

- `reports/refactor/latest_codex_review_request.md`와 `reports/refactor/19-5_codex_review_request.md`가 동일함을 확인했다.
- `reports/refactor/latest_test_report.md`와 `reports/refactor/19-5_test_report.md`, `reports/refactor/latest_fix_summary.md`와 `reports/refactor/19-5_fix_summary.md`가 동일함을 확인했다.
- Claude Code 요약이 아니라 실제 `app/modules/leaves`, `dosu_clinic.spec`, `tests/test_pyinstaller_hidden_imports.py`, `tests/test_19_5_leaves.py`를 직접 대조했다.

## 실제 파일 구조 대조

파일 줄 수는 `[System.IO.File]::ReadAllLines(...).Count` 기준으로 확인했다.

| 파일 | 실제 줄 수 | 요청서 주장 |
|---|---:|---:|
| `app/modules/leaves/__init__.py` | 35 | 35 |
| `app/modules/leaves/rules.py` | 212 | 212 |
| `app/modules/leaves/repository.py` | 100 | 100 |
| `app/modules/leaves/service.py` | 135 | 135 |
| `tests/test_19_5_leaves.py` | 589 | 589 |

`rules.py`에는 휴무 타입/종류/반차 경계/차단 메시지 helper가 있고, `repository.py`는 DB 세션 호출자 주입 및 함수 내부 lazy import 구조이며, `service.py`는 `_upsert_employee_leave_core` 동등 helper와 응답 dict serializer를 제공한다. 요청서의 분리 범위와 일치한다.

## 의존성 경계 대조

`app/modules/leaves/rules.py`는 `datetime` / `typing` 중심의 순수 helper로 유지되어 있고, `app.models`, `app.database`, `sqlalchemy`, `fastapi`, 외부 AI/API 클라이언트 직접 의존은 발견되지 않았다.

`repository.py`와 `service.py`에는 `app.models` lazy import가 함수 내부에 존재한다. 이는 요청서의 "read-only repository + DB 호출자 주입" 및 "repository / service conditional reference" 설명과 맞다. `service.py`는 `app.routers`나 `fastapi`를 import하지 않는다.

기존 `app/routers/api.py`의 `_upsert_employee_leave_core`, `list_employee_leaves`, `list_therapist_leaves_alias`는 존재하며, `app/services/ai/action_leave.py`의 `_do_upsert`는 여전히 `app.routers.api._upsert_employee_leave_core`를 import한다. 즉 19-5 helper는 아직 후보 구조이고 기존 라우터/AI 흐름은 유지된다.

## PyInstaller 등록 대조

`dosu_clinic.spec`에는 다음 hidden import가 포함되어 있다.

- `app.modules.leaves`
- `app.modules.leaves.rules`
- `app.modules.leaves.repository`
- `app.modules.leaves.service`

`tests/test_pyinstaller_hidden_imports.py`의 `EXPECTED_19_X_MODULES_MODULES`에도 같은 네 모듈이 포함되어 있고, 모두 import 가능하다.

tracked diff 수치도 요청서와 일치한다.

| 파일 | 실제 tracked diff | 요청서 주장 |
|---|---:|---:|
| `dosu_clinic.spec` | +6 | +6 |
| `tests/test_pyinstaller_hidden_imports.py` | +5 | +5 |

## 테스트 재실행 결과

| 명령 | 결과 |
|---|---|
| `.\venv\Scripts\python.exe -m pytest tests -q` | **793 passed, 1 skipped, 7 xfailed, 27 warnings** |
| `.\venv\Scripts\python.exe -m pytest tests/test_pyinstaller_hidden_imports.py -q` | **93 passed** |
| `.\venv\Scripts\python.exe -m ruff check app tests scripts` | **All checks passed!** |
| `.\venv\Scripts\python.exe scripts/check_db_path.py` | exit 0 |

전체 테스트 결과와 PyInstaller 테스트 수치는 요청서/테스트 리포트와 일치한다. `tests/test_19_5_leaves.py`도 전체 suite 안에서 54개 테스트가 통과한 것으로 확인된다.

별도 단일 파일 실행인 `pytest tests/test_19_5_leaves.py -q`와 C-6 묶음 실행은 이 환경에서 venv launcher가 Python 프로세스를 만들지 못해 실행 전 실패했다. 그러나 전체 `tests -q` 실행에서 해당 테스트들이 포함되어 통과했으므로 기능 실패로 보지는 않는다.

## 남은 확인 사항

1. `app/modules/leaves/__pycache__`가 현재 작업 트리에 존재한다. 검증 과정의 import/test 실행으로 생성될 수 있으므로 커밋 전 정리 또는 ignore 확인이 필요하다.
2. 단일 파일/일부 묶음 pytest 실행은 여전히 venv launcher 문제로 재현되지 않는다. 전체 suite가 같은 테스트를 포함해 통과하므로 기능 gate는 통과로 본다.

## 종합

19-5의 실제 구현 방향은 요청 취지와 맞는다. 휴무 도메인 규칙, repository 후보, service 후보가 신규 `app.modules.leaves` 경계 안에 들어갔고, 기존 router/AI action 흐름은 유지된다. 전체 테스트, PyInstaller, ruff, DB path gate도 통과했다.

따라서 **19-6 진입 가능**으로 판정한다.
