# 19-4 r2 Codex 검증 결과

## 판정

**통과.** 19-4 r2 요청서는 r1에서 지적했던 주요 수치 오류를 대부분 보정했고, 실제 파일 구조와 테스트 결과도 요청 취지와 맞는다. 따라서 **19-5 leaves 휴무 규칙 분리로 진입 가능**하다고 판단한다.

단, 검증 중 실행한 pytest/import 과정으로 `app/modules/appointments/__pycache__`가 현재 작업 트리에 다시 존재한다. 커밋 전 제외 또는 정리가 필요하다.

## 직접 검증한 기준

- `reports/refactor/latest_codex_review_request.md`와 `reports/refactor/19-4_codex_review_request.md`가 동일함을 확인했다.
- `reports/refactor/latest_test_report.md`와 `reports/refactor/19-4_test_report.md`, `reports/refactor/latest_fix_summary.md`와 `reports/refactor/19-4_fix_summary.md`가 동일함을 확인했다.
- Claude Code 요약이 아니라 실제 `app/modules/appointments`, `dosu_clinic.spec`, `tests/test_pyinstaller_hidden_imports.py`, `tests/test_19_4_availability.py`를 직접 대조했다.

## 실제 파일 구조 대조

파일 줄 수는 `[System.IO.File]::ReadAllLines(...).Count` 기준으로 확인했다.

| 파일 | 실제 줄 수 | r2 요청서 주장 |
|---|---:|---:|
| `app/modules/appointments/__init__.py` | 18 | 18 |
| `app/modules/appointments/availability.py` | 369 | 369 |
| `tests/test_19_4_availability.py` | 607 | 607 |

`availability.py`의 top-level helper 함수는 14개이고, `Final` 상수는 9개로 확인된다. r2 요청서의 보정값과 일치한다.

`app/modules/appointments` 내부 소스에서 `app.models`, `app.database`, `app.services`, `app.routers`, `sqlalchemy`, `fastapi`, 외부 AI/API 클라이언트(`openai`, `anthropic`, `requests`, `httpx`) 직접 의존은 발견되지 않았다. `HTTPException` 문자열은 주석/docstring에만 등장하며, helper가 직접 raise하지 않는다는 경계 취지와 맞다.

## PyInstaller 등록 대조

`dosu_clinic.spec`에는 다음 hidden import가 포함되어 있다.

- `app.modules.appointments`
- `app.modules.appointments.availability`

`tests/test_pyinstaller_hidden_imports.py`의 `EXPECTED_19_X_MODULES_MODULES`에도 같은 두 모듈이 포함되어 있고, 두 모듈 모두 import 가능하다.

tracked diff 수치도 요청서와 일치한다.

| 파일 | 실제 tracked diff | r2 요청서 주장 |
|---|---:|---:|
| `dosu_clinic.spec` | +5 | +5 |
| `tests/test_pyinstaller_hidden_imports.py` | +3 | +3 |

## 테스트 재실행 결과

| 명령 | 결과 |
|---|---|
| `.\venv\Scripts\python.exe -m pytest tests -q` | **731 passed, 1 skipped, 7 xfailed, 27 warnings** |
| `.\venv\Scripts\python.exe -m pytest tests/test_pyinstaller_hidden_imports.py -q` | **85 passed** |
| `.\venv\Scripts\python.exe -m ruff check app tests scripts` | **All checks passed!** |
| `.\venv\Scripts\python.exe scripts/check_db_path.py` | exit 0 |

전체 테스트 결과와 PyInstaller 테스트 수치는 r2 요청서/테스트 리포트와 일치한다. `tests/test_19_4_availability.py`도 전체 suite 안에서 79개 테스트가 통과한 것으로 확인된다.

별도 단일 파일 실행인 `pytest tests/test_19_4_availability.py -q`는 이 환경에서 venv launcher가 Python 프로세스를 만들지 못해 실행 전 실패했다. 그러나 전체 `tests -q` 실행에서 해당 테스트들이 포함되어 통과했으므로 기능 실패로 보지는 않는다.

## 남은 확인 사항

1. `app/modules/appointments/__pycache__`가 현재 작업 트리에 존재한다. 검증 과정의 import/test 실행으로 다시 생성될 수 있으므로 커밋 전 정리 또는 ignore 확인이 필요하다.
2. 단일 파일 pytest 실행은 여전히 venv launcher 문제로 재현되지 않는다. 전체 suite가 같은 테스트를 포함해 통과하므로 기능 gate는 통과로 본다.

## 종합

19-4 r2의 실제 구현 방향은 요청 취지와 맞는다. availability 판정 helper가 신규 `app.modules.appointments` 경계 안에 들어갔고, 기존 router/service/DB/ORM 경계를 직접 끌어오지 않는다. r1에서 지적했던 PyInstaller 총합, 신규 파일 줄 수, helper/상수 수치도 r2 문서에서 보정되어 실제와 일치한다.

따라서 **19-5 진입 가능**으로 판정한다.
