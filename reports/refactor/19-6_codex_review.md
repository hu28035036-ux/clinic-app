# 19-6 Codex 검증 결과

## 판정

**통과.** 19-6 treatments / completion_rules 분리는 실제 파일 기준으로 `app.modules.treatments` 경계 안에 추가되어 있고, 전체 테스트/ruff/DB 경로 가드는 통과했다. 따라서 **19-7 patients / notes / data-convert 분리로 진입 가능**하다고 판단한다.

단, 현재 작업 트리에 요청서 변경 목록에 없는 `docs/ai/` untracked 문서들이 존재한다. 19-6 기능 검증 실패는 아니지만, 커밋 범위 결정 전 별도 확인이 필요하다. 또한 검증 중 실행한 pytest/import 과정으로 `app/modules/treatments/__pycache__`가 생성되어 있어 커밋 전 제외 또는 정리가 필요하다.

## 직접 검증한 기준

- `reports/refactor/latest_codex_review_request.md`와 `reports/refactor/19-6_codex_review_request.md`가 동일함을 확인했다.
- `reports/refactor/latest_test_report.md`와 `reports/refactor/19-6_test_report.md`, `reports/refactor/latest_fix_summary.md`와 `reports/refactor/19-6_fix_summary.md`가 동일함을 확인했다.
- Claude Code 요약이 아니라 실제 `app/modules/treatments`, `dosu_clinic.spec`, `tests/test_pyinstaller_hidden_imports.py`, `tests/test_19_6_treatments.py`를 직접 대조했다.

## 실제 파일 구조 대조

파일 줄 수는 `[System.IO.File]::ReadAllLines(...).Count` 기준으로 확인했다.

| 파일 | 실제 줄 수 | 요청서 주장 |
|---|---:|---:|
| `app/modules/treatments/__init__.py` | 33 | 33 |
| `app/modules/treatments/rules.py` | 198 | 198 |
| `app/modules/treatments/repository.py` | 92 | 92 |
| `app/modules/treatments/service.py` | 173 | 173 |
| `app/modules/treatments/completion_rules.py` | 114 | 114 |
| `tests/test_19_6_treatments.py` | 575 | 575 |

`rules.py`에는 치료항목 role/ESWT/manual 분류 helper가 있고, `repository.py`는 DB 세션 호출자 주입 및 함수 내부 lazy import 구조이며, `service.py`는 serialize/meta/incentive helper를 제공한다. `completion_rules.py`는 `_bump_patient_count` 동등 helper와 `manual60=1` 정합 상수를 제공한다. 요청서의 분리 범위와 일치한다.

## 의존성 경계 대조

`app/modules/treatments/rules.py`는 `typing` 중심의 순수 helper로 유지되어 있고, `app.models`, `app.database`, `sqlalchemy`, `fastapi`, 외부 AI/API 클라이언트 직접 의존은 발견되지 않았다.

`repository.py`와 `completion_rules.py`에는 `app.models` lazy import가 함수 내부에 존재한다. 이는 요청서의 "DB 세션 호출자 주입 / lazy import" 설명과 맞다. `service.py`는 `app.routers`나 `fastapi`를 import하지 않고, `IncentiveValidationError`로 호출자 변환 책임을 분리한다.

## PyInstaller 등록 대조

`dosu_clinic.spec`에는 다음 hidden import가 포함되어 있다.

- `app.modules.treatments`
- `app.modules.treatments.rules`
- `app.modules.treatments.repository`
- `app.modules.treatments.service`
- `app.modules.treatments.completion_rules`

`tests/test_pyinstaller_hidden_imports.py`의 `EXPECTED_19_X_MODULES_MODULES`에도 같은 다섯 모듈이 포함되어 있고, 모두 import 가능하다.

tracked diff 수치도 요청서와 일치한다.

| 파일 | 실제 tracked diff | 요청서 주장 |
|---|---:|---:|
| `dosu_clinic.spec` | +8 | +8 |
| `tests/test_pyinstaller_hidden_imports.py` | +6 | +6 |

## 테스트 재실행 결과

| 명령 | 결과 |
|---|---|
| `.\venv\Scripts\python.exe -m pytest tests -q` | **846 passed, 1 skipped, 7 xfailed, 27 warnings** |
| `.\venv\Scripts\python.exe -m pytest tests/test_pyinstaller_hidden_imports.py -q` | **103 passed** |
| `.\venv\Scripts\python.exe -m pytest tests/test_19_6_treatments.py -q` | **43 passed** |
| C-6 정확한 회귀 묶음 | **160 passed, 1 skipped, 3 xfailed** |
| `.\venv\Scripts\python.exe -m ruff check app tests scripts` | **All checks passed!** |
| `.\venv\Scripts\python.exe scripts/check_db_path.py` | exit 0 |

전체 테스트 결과, PyInstaller, 19-6 contract, C-6 회귀 묶음 모두 요청서/테스트 리포트와 일치한다.

## 범위 밖 변경 확인

현재 `git status`에는 요청서 변경 목록에 없는 `docs/ai/` untracked 문서들이 존재한다.

- `docs/ai/AI_CODEX_VERIFICATION_PLAN.md`
- `docs/ai/AI_COMMAND_ARCHITECTURE.md`
- `docs/ai/AI_CURRENT_DECISIONS.md`
- `docs/ai/AI_FEATURE_MASTER_PLAN.md`
- `docs/ai/AI_HARNESS_PLAN.md`
- `docs/ai/AI_IMPLEMENTATION_PHASES.md`
- `docs/ai/AI_REQUIREMENTS_OVERRIDES.md`
- `docs/ai/AI_SAFETY_POLICY.md`
- `docs/ai/verification/AI_PHASE_VERIFICATION_SKILL.md`

이 파일들은 `latest_codex_review_request.md`, `latest_fix_summary.md`, `latest_test_report.md`에서 19-6 변경 범위로 언급되지 않는다. 19-6 treatments 기능 검증에는 영향이 없지만, 커밋 전 포함 여부를 명확히 해야 한다.

## 남은 확인 사항

1. `app/modules/treatments/__pycache__`가 현재 작업 트리에 존재한다. 검증 과정의 import/test 실행으로 생성될 수 있으므로 커밋 전 정리 또는 ignore 확인이 필요하다.
2. `docs/ai/` untracked 문서들이 이번 19-6 커밋 범위인지 별도 판단이 필요하다.

## 종합

19-6의 실제 구현 방향은 요청 취지와 맞는다. 치료항목 분류, repository 후보, service 후보, completion rules 후보가 신규 `app.modules.treatments` 경계 안에 들어갔고, 기존 router/통계/SMS/AI 흐름은 유지된다. 전체 테스트, PyInstaller, ruff, DB path gate도 통과했다.

따라서 **19-7 진입 가능**으로 판정한다.
