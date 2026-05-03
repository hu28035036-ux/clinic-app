# 19-3 Codex 검증 결과

## 판정

**조건부 통과.** 19-3 calendar / schedule_view 표시용 view-model 분리는 실제 파일 기준으로 `app.modules.calendar` 경계 안에 추가되어 있고, 전체 테스트/ruff/DB 경로 가드는 통과했다. 따라서 **19-4 availability 예약 가능 여부 / 충돌 검증 분리로 진입 가능**하다고 판단한다.

다만 Claude Code 요청서와 테스트 리포트의 일부 수치는 실제 저장소와 맞지 않는다. 기능 실패는 아니지만, 다음 세션 진입 전 기록 보정이 필요하다.

## 직접 검증한 기준

- `reports/refactor/latest_codex_review_request.md`와 `reports/refactor/19-3_codex_review_request.md`가 동일함을 확인했다.
- `reports/refactor/latest_test_report.md`와 `reports/refactor/19-3_test_report.md`, `reports/refactor/latest_fix_summary.md`와 `reports/refactor/19-3_fix_summary.md`가 동일함을 확인했다.
- Claude Code 요약이 아니라 실제 `app/modules/calendar`, `dosu_clinic.spec`, `tests/test_pyinstaller_hidden_imports.py`, `tests/test_19_3_calendar_view_model.py`를 직접 대조했다.

## 실제 파일 구조 대조

19-3 신규 calendar 모듈은 다음 파일로 존재한다.

| 파일 | 실제 줄 수 | 요청서 주장 |
|---|---:|---:|
| `app/modules/calendar/__init__.py` | 39 | 38 |
| `app/modules/calendar/view_models.py` | 336 | 288 |
| `tests/test_19_3_calendar_view_model.py` | 523 | 373 |

요청서의 줄 수는 현재 파일과 다르다. 특히 contract 테스트 파일은 실제로 훨씬 크며, 이 때문에 요청서의 테스트 개수 설명도 함께 틀어진 것으로 보인다.

`app/modules/calendar` 내부 소스에서 `app.models`, `app.database`, `app.services`, 외부 AI/API 클라이언트(`openai`, `anthropic`, `requests`, `httpx`) 직접 의존은 발견되지 않았다. 현재 구현은 `typing` 중심의 표시용 helper/facade로 유지되어 D-4 경계 취지와 맞다.

## PyInstaller 등록 대조

`dosu_clinic.spec`에는 다음 hidden import가 포함되어 있다.

- `app.modules.calendar`
- `app.modules.calendar.view_models`

`tests/test_pyinstaller_hidden_imports.py`의 `EXPECTED_19_X_MODULES_MODULES`에도 같은 두 모듈이 포함되어 있고, 두 모듈 모두 import 가능하다.

다만 diff 수치는 요청서와 다르다.

| 파일 | 실제 tracked diff | 요청서 주장 |
|---|---:|---:|
| `dosu_clinic.spec` | +11 | +5 |
| `tests/test_pyinstaller_hidden_imports.py` | +35 | +3 |

또한 현재 PyInstaller hidden import 테스트 결과는 **81 passed**가 맞다. 요청서/테스트 리포트의 **89 passed**는 실제 실행 결과와 일치하지 않는다. 현재 `EXPECTED_19_X_MODULES_MODULES`는 총 6개 모듈이며, 두 개의 parametrized 테스트가 돌아서 해당 묶음은 12건으로 계산된다. 19-2의 77건 대비 실제 증가는 +4건이다.

## 테스트 재실행 결과

| 명령 | 결과 |
|---|---|
| `.\venv\Scripts\python.exe -m pytest tests -q` | **648 passed, 1 skipped, 7 xfailed, 27 warnings** |
| `.\venv\Scripts\python.exe -m pytest tests/test_pyinstaller_hidden_imports.py -q` | **81 passed** |
| `.\venv\Scripts\python.exe -m ruff check app tests scripts` | **All checks passed!** |
| `.\venv\Scripts\python.exe scripts/check_db_path.py` | exit 0 |

전체 테스트 결과는 요청서의 전체 수치와 일치한다. 따라서 기능 회귀 관점의 핵심 gate는 통과했다.

별도 단일 파일 실행인 `pytest tests/test_19_3_calendar_view_model.py -q`는 이 환경에서 venv launcher가 Python 프로세스를 만들지 못해 실행 전 실패했다. 그러나 전체 `tests -q` 실행에서 `tests/test_19_3_calendar_view_model.py`가 포함되어 통과했으므로 기능 실패로 보지는 않는다.

요청서의 contract 테스트 **51 passed** 주장도 현재 실제 파일/전체 실행 흐름과 맞지 않는다. 현재 파일의 parametrization 기준으로 전체 테스트 증가분을 대조하면 19-3 contract 파일은 51건이 아니라 약 59건으로 반영된 것으로 보인다.

## 확인된 위험 / 보정 필요 사항

1. `reports/refactor/19-3_test_report.md`와 `latest_test_report.md`의 PyInstaller 테스트 수치가 실제 실행 결과와 다르다. `89 passed`가 아니라 `81 passed`다.
2. 요청서의 신규 파일 줄 수와 tracked diff 수치가 현재 저장소와 다르다.
3. 단일 파일/일부 묶음 pytest 명령은 venv launcher 문제로 직접 재현되지 않았다. 전체 suite는 정상 통과했다.
4. `app/modules/calendar/__pycache__`가 작업 트리에 존재한다. 커밋 전 제외 또는 정리가 필요하다.

## 종합

19-3의 실제 구현 방향은 요청 취지와 맞는다. calendar/schedule_view 표시용 view-model이 신규 `app.modules.calendar` 경계 안에 들어갔고, 기존 router/service/DB 경계를 직접 끌어오지 않는다. 전체 테스트, ruff, DB path gate도 통과했다.

따라서 **19-4 진입은 가능**하다. 단, 다음 세션 시작 전 Claude Code 산출물의 수치 불일치, 특히 PyInstaller `89 passed` 표기는 `81 passed`로 보정하는 편이 안전하다.
