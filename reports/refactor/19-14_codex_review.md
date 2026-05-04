# 19-14 Codex 검증 결과

검증 시각: 2026-05-04, `latest_codex_review_request.md` 최신본 기준.

## 판정

**조건부 통과.** 전체 pytest, 19-14 smoke, ruff, DB 경로 검사, 격리 경로 PyInstaller 빌드, 격리 산출물 exe 기동은 통과했다. 따라서 19-1 ~ 19-13 리팩터링 1차 회귀 검증 자체는 성공으로 본다.

다만 요청 문서의 두 주장은 현재 워크트리에서 그대로 재현되지 않았다.

- `tests/test_19_14_smoke_workflow.py`는 요청 문서상 266줄이지만 실제는 336줄이다.
- 기본 명령 `PyInstaller --noconfirm dosu_clinic.spec`는 기존 `dist\도수치료예약\_internal\anthropic\lib` 제거 단계에서 `WinError 5 Access denied`로 실패했다. 같은 spec을 별도 `--distpath` / `--workpath` 격리 경로로 실행하면 성공했다.

## 직접 검증한 근거

- `reports/refactor/latest_codex_review_request.md`와 `reports/refactor/19-14_codex_review_request.md`가 동일함을 확인했다.
- `reports/refactor/latest_test_report.md`와 `reports/refactor/19-14_test_report.md`가 동일함을 확인했다.
- `reports/refactor/latest_fix_summary.md`와 `reports/refactor/19-14_fix_summary.md`가 동일함을 확인했다.
- Claude Code 요약 대신 실제 `git status`, `git diff --stat`, 파일 줄 수, 테스트 실행 로그, ruff, DB 경로 검사, PyInstaller 빌드 로그, 산출물 구조, exe 기동을 직접 확인했다.

## 실제 파일 구조

줄 수는 `[System.IO.File]::ReadAllLines(...).Count` 기준이다.

| 파일 | 실제 줄 수 | 요청 문서 |
|---|---:|---:|
| `tests/test_19_14_smoke_workflow.py` | 336 | 266 |
| `docs/refactor/19_refactor_final_test_result.md` | 188 | 약 200 |

smoke 테스트는 줄 수 표기가 불일치하지만, 수집된 15개 케이스의 실행 결과는 요청 문서와 일치한다.

## 실제 diff

`git diff --stat` 기준 tracked 변경은 다음 2개뿐이다.

| 파일 | 실제 diff |
|---|---:|
| `dosu_clinic.spec` | +29 |
| `tests/test_pyinstaller_hidden_imports.py` | +22 |

`app/routers`, `app/services`, `app/models.py`, `app/db.py`, `app/config.py`, `migrations`, `requirements.txt`에는 diff가 없다. 19-14 신규 `tests/test_19_14_smoke_workflow.py`와 `docs/refactor/19_refactor_final_test_result.md`는 untracked 신규 파일이다.

## 테스트 재실행 결과

venv launcher 문제가 있어 pytest는 Codex 번들 Python에 venv site-packages와 workspace를 `PYTHONPATH`로 연결해 실행했다.

| 검증 | 결과 |
|---|---|
| `pytest tests/test_19_14_smoke_workflow.py -q` | 12 passed, 3 xfailed |
| `pytest tests -q` | 1671 passed, 1 skipped, 10 xfailed, 27 warnings |
| `.\venv\Scripts\ruff.exe check app tests scripts` | All checks passed |
| `scripts/check_db_path.py` | exit 0 |

warnings는 기존 AI/SMS/manual QA 계열 `PytestReturnNotNoneWarning`이며 19-14 smoke 실패는 아니다. 비상승 targeted pytest에서는 `.pytest_cache` 접근 권한 warning도 발생했다.

## PyInstaller 검증

기본 산출물 경로 재빌드:

- `.\venv\Scripts\pyinstaller.exe --noconfirm dosu_clinic.spec`: venv launcher가 한글 경로를 깨뜨려 실행 실패.
- Codex 번들 Python + venv site-packages로 `python -m PyInstaller --noconfirm dosu_clinic.spec`: spec 분석, hidden import 분석, EXE 생성까지 진행됐으나 기존 `dist\도수치료예약\_internal\anthropic\lib` 제거 단계에서 `WinError 5 Access denied`로 실패.
- 같은 명령을 외부 권한으로 재실행해도 같은 위치에서 실패했다.

격리 경로 재빌드:

```powershell
python -m PyInstaller --noconfirm --distpath .codex-pyinstaller-dist-19-14 --workpath .codex-pyinstaller-build-19-14 dosu_clinic.spec
```

결과:

- exit 0
- migration auto-register 13 modules 확인
- 19-12 / 19-13 신규 hidden import 분석 로그 확인
- `warn-dosu_clinic.txt`에서 `app.modules.*` 누락 warning 없음
- 산출물 exe: `.codex-pyinstaller-dist-19-14\도수치료예약\도수치료예약.exe`, 16,020,729 bytes
- `_internal` 존재, 내부 directory 22개 확인
- 격리 산출물에서는 `updater.bat`이 루트가 아니라 `_internal\updater.bat`에 존재한다. 기본 기존 `dist\도수치료예약`에는 루트 `updater.bat`이 존재한다.

## 산출물 실행 확인

격리 산출물 exe에 `DOSU_DB_PATH=.test-build-tmp\test_clinic.db`를 지정해 `Start-Process -WindowStyle Hidden`으로 실행했다.

- 8초 후 프로세스가 살아 있음을 확인했다.
- 검증 후 `Stop-Process -Force`로 종료했다.
- 즉 binary 진입과 초기 기동은 확인했다. 요청 문서의 “단일 인스턴스 메시지 후 exit 0” 형태는 이번 직접 실행에서는 재현하지 못했고, 대신 기동 지속 상태를 확인했다.

## 종합

19-14의 핵심인 전체 회귀 테스트와 smoke workflow는 요청 문서 수치와 일치한다. 기능 코드, router/service/model/db/migration/requirements 변경도 확인되지 않았다. PyInstaller spec 자체는 격리 경로에서 정상 빌드되고 신규 hidden import도 누락되지 않았으며 산출물 exe도 기동한다.

남은 주의점은 기본 `dist` 폴더 교체가 현재 환경에서 `Access denied`로 재현 실패한다는 점과 smoke 테스트 줄 수 표기 불일치다. 기본 산출물 폴더 잠금/권한을 정리한 뒤 기본 PyInstaller 명령을 다시 돌리면 요청 문서의 “기본 빌드 exit 0”까지 재확인할 수 있다.

결론: **기능/회귀 기준 19-14 통과, PyInstaller 기본 경로 재빌드는 환경 잠금 해소 후 재확인 필요**.
