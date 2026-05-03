# 19-7 r2 Codex 검증 결과

## 판정

**조건부 통과.** 19-7 r2 요청서는 r1에서 지적했던 contract 테스트 줄 수를 실제와 맞게 보정했고, 전체 테스트/ruff/DB 경로 가드는 통과했다. 따라서 **19-8 staff / therapists / doctors 경계 정리로 진입 가능**하다고 판단한다.

다만 r2 요청서는 `__pycache__`가 정리됐다고 적고 있지만, 현재 작업 트리에는 `app/modules/patients/__pycache__`와 `app/modules/notes/__pycache__`가 다시 존재한다. 검증 중 import/pytest 실행으로 재생성될 수 있는 항목이라 기능 실패는 아니지만, 커밋 전 정리 또는 제외가 필요하다.

## 직접 검증한 기준

- `reports/refactor/latest_codex_review_request.md`와 `reports/refactor/19-7_codex_review_request.md`가 동일함을 확인했다.
- `reports/refactor/latest_test_report.md`와 `reports/refactor/19-7_test_report.md`, `reports/refactor/latest_fix_summary.md`와 `reports/refactor/19-7_fix_summary.md`가 동일함을 확인했다.
- Claude Code 요약이 아니라 실제 `app/modules/patients`, `app/modules/notes`, `dosu_clinic.spec`, `tests/test_pyinstaller_hidden_imports.py`, `tests/test_19_7_patients_notes.py`를 직접 대조했다.

## 실제 파일 구조 대조

파일 줄 수는 `[System.IO.File]::ReadAllLines(...).Count` 기준으로 확인했다.

| 파일 | 실제 줄 수 | r2 요청서 주장 |
|---|---:|---:|
| `app/modules/patients/__init__.py` | 30 | 30 |
| `app/modules/patients/rules.py` | 239 | 239 |
| `app/modules/patients/repository.py` | 120 | 120 |
| `app/modules/patients/service.py` | 173 | 173 |
| `app/modules/notes/__init__.py` | 31 | 31 |
| `app/modules/notes/rules.py` | 137 | 137 |
| `tests/test_19_7_patients_notes.py` | 662 | 662 |

r1에서 지적한 `tests/test_19_7_patients_notes.py` 줄 수 불일치는 r2 문서에서 보정되어 실제와 일치한다.

## 의존성 경계 대조

`patients.rules`와 `notes.rules`는 `re` / `typing` 중심의 순수 helper로 유지되어 있고, `app.models`, `app.database`, `sqlalchemy`, `fastapi`, 외부 AI/API 클라이언트 직접 의존은 발견되지 않았다.

`patients.repository`에는 `app.models` lazy import가 함수 내부에 존재한다. 이는 요청서의 "DB 세션 호출자 주입 / lazy import" 설명과 맞다. `patients.service`는 `app.routers`나 `fastapi`를 import하지 않는다. `patients.__init__`와 `notes.__init__`도 ORM/DB 계층을 직접 끌어오지 않는다.

## PyInstaller 등록 대조

`dosu_clinic.spec`에는 다음 hidden import가 포함되어 있다.

- `app.modules.patients`
- `app.modules.patients.rules`
- `app.modules.patients.repository`
- `app.modules.patients.service`
- `app.modules.notes`
- `app.modules.notes.rules`

`tests/test_pyinstaller_hidden_imports.py`의 `EXPECTED_19_X_MODULES_MODULES`에도 같은 여섯 모듈이 포함되어 있고, 모두 import 가능하다.

tracked diff 수치도 요청서와 일치한다.

| 파일 | 실제 tracked diff | r2 요청서 주장 |
|---|---:|---:|
| `dosu_clinic.spec` | +9 | +9 |
| `tests/test_pyinstaller_hidden_imports.py` | +7 | +7 |

## 테스트 재실행 결과

| 명령 | 결과 |
|---|---|
| `.\venv\Scripts\python.exe -m pytest tests -q` | **938 passed, 1 skipped, 7 xfailed, 27 warnings** |
| `.\venv\Scripts\python.exe -m pytest tests/test_pyinstaller_hidden_imports.py -q` | **115 passed** |
| `.\venv\Scripts\python.exe -m pytest tests/test_19_7_patients_notes.py -q` | **80 passed** |
| C-6 회귀 묶음 | **262 passed, 1 skipped, 3 xfailed, 21 warnings** |
| `.\venv\Scripts\python.exe -m ruff check app tests scripts` | **All checks passed!** |
| `.\venv\Scripts\python.exe scripts/check_db_path.py` | exit 0 |

전체 테스트 결과, PyInstaller, 19-7 contract, C-6 회귀 묶음 모두 r2 요청서/테스트 리포트와 일치한다.

## 범위 밖 변경 확인

현재 `git status`에는 요청서 변경 목록에 없는 `docs/ai/` untracked 문서들이 존재한다. r2 요청서가 설명한 대로 별도 기획 문서이며 19-7 커밋 범위 밖으로 보는 것이 타당하다.

## 남은 확인 사항

1. `app/modules/patients/__pycache__`, `app/modules/notes/__pycache__`가 현재 작업 트리에 존재한다. r2 요청서의 "정리됨" 상태는 현재 검증 실행 후 유지되지 않는다.
2. `docs/ai/` untracked 문서들은 19-7 커밋 범위 밖으로 분리할지 별도 판단이 필요하다.

## 종합

19-7 r2의 실제 구현 방향은 요청 취지와 맞는다. 환자 중복/직렬화/검색 응답/PII 로그 마스킹 helper와 메모 분류/취소 prefix helper가 신규 `app.modules.patients` 및 `app.modules.notes` 경계 안에 들어갔고, 기존 router/SMS/AI/통계 흐름은 유지된다. r1에서 지적했던 테스트 파일 줄 수도 보정되었다.

따라서 **19-8 진입 가능**으로 판정한다. 단, 커밋 전 `__pycache__` 정리와 범위 밖 `docs/ai/` 처리 여부 확인이 필요하다.
