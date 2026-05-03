# 19-1 r2 Codex 검증 결과

- 검증 대상: `reports/refactor/latest_codex_review_request.md` / `reports/refactor/19-1_codex_review_request.md` / `reports/refactor/19-1_test_report.md` / `reports/refactor/19-1_fix_summary.md` / `app/core/*`
- 검증일: 2026-05-03
- 기준 브랜치: `ai-rag-v1-integration`
- 판정: **pass with caveat**
- 다음 단계: **yes — 19-2 settings / feature_flags / health 경계 정리 진입 가능**

## 1. 검증 방식

Claude Code 요약은 신뢰 근거로 사용하지 않고, 실제 파일 구조와 문서 본문을 직접 대조했다.

- `reports/refactor/19-1_codex_review_request.md` 와 `reports/refactor/latest_codex_review_request.md` 를 비교했다. 결과는 동일했다.
- `app/core/*.py` 8개 파일의 line count를 실제 파일 기준으로 재측정했다.
- `git diff --stat 09f49c1 -- dosu_clinic.spec tests/test_pyinstaller_hidden_imports.py` 로 spec/test 수정량을 확인했다.
- PyInstaller spec과 테스트의 `app.core*` 8개 모듈 등록 여부를 실제 문자열 기준으로 대조했다.
- 전체 테스트, ruff, DB 경로 체크, PyInstaller hidden imports 테스트를 현재 환경에서 직접 재실행했다.
- `app/core` 내부에서 `app.modules` 방향 import가 없는지 확인했다.

## 2. r2 보정 검증

| 항목 | 요청서 r2 주장 | 실제 확인 | 판정 |
|---|---:|---:|---:|
| `app/core/__init__.py` | 12 lines | 12 | pass |
| `app/core/config.py` | 41 lines | 41 | pass |
| `app/core/database.py` | 37 lines | 37 | pass |
| `app/core/security.py` | 47 lines | 47 | pass |
| `app/core/errors.py` | 77 lines | 77 | pass |
| `app/core/responses.py` | 109 lines | 109 | pass |
| `app/core/time_utils.py` | 100 lines | 100 | pass |
| `app/core/feature_flags.py` | 126 lines | 126 | pass |
| `app/core` 합계 | 549 lines | 549 | pass |
| `dosu_clinic.spec` diff | +10 | +10 | pass |
| `tests/test_pyinstaller_hidden_imports.py` diff | +42 | +42 | pass |
| spec/test diff 합계 | +52 | +52 | pass |

## 3. 명령 재실행 결과

| 명령 | 실제 결과 | 판정 |
|---|---|---:|
| `venv/Scripts/python.exe -m pytest tests -q` | **545 passed, 1 skipped, 7 xfailed, 27 warnings** (11.00초) | pass |
| `venv/Scripts/python.exe -m ruff check app tests scripts` | **All checks passed!** | pass |
| `venv/Scripts/python.exe scripts/check_db_path.py` | exit 0, 운영 DB 경로 감지 메시지 출력 | pass |
| `venv/Scripts/python.exe -m pytest tests/test_pyinstaller_hidden_imports.py -q` | **69 passed** (0.33초) | pass |

## 4. 구조 대조

| 항목 | 실제 확인 | 판정 |
|---|---:|---:|
| `app/core/*.py` 파일 수 | 8 | pass |
| re-export wrapper | `config.py`, `database.py`, `security.py` | pass |
| 신규 helper | `errors.py`, `responses.py`, `time_utils.py`, `feature_flags.py` | pass |
| `app.core*` spec hiddenimports 등록 | 8/8 | pass |
| `app.core*` PyInstaller 테스트 등록 | 8/8 | pass |
| `app.core` 실제 import 가능성 | PyInstaller importable tests 8개 통과 | pass |
| `app.modules` 방향 import | 0건 | pass |
| 주석 카테고리 | COMPAT/SAFETY/NOTE/RISK/TODO 확인 | pass |

## 5. Caveats

1. 요청서 §2 목표 표에는 아직 `dosu_clinic.spec hidden imports 갱신 — 9 lines 추가` 표현이 남아 있다. r2 보정 섹션과 실제 diff는 **+10 lines**가 맞다.
2. `git diff --stat 09f49c1 -- app ...` 는 untracked 신규 파일인 `app/core/*` 를 표시하지 않는다. `git status --short` 와 실제 파일 목록을 함께 봐야 19-1 신규 core 8개가 잡힌다.
3. `venv/Scripts/python.exe -c "..."` 직접 import 명령은 이 환경에서 이전과 같이 프로세스 생성 오류가 날 수 있다. 다만 PyInstaller `actually_importable` parametrized tests가 `app.core*` 8개 import를 검증해 69 passed로 통과했다.
4. 현재 변경은 아직 modified/untracked 상태다. 19-2 진입 전 커밋/유지 방침을 확정하는 것이 좋다.

## 6. 종합 판정

19-1 r2의 핵심 보정인 line count와 diff stat 정정은 실제 파일 구조와 일치한다. `app/core` 신설, compatibility wrapper 유지, spec/test 등록, PyInstaller 69 tests, 전체 테스트 545/1/7도 모두 확인됐다.

따라서 판정은 **pass with caveat** 이다. 남은 caveat는 문서 일부 stale 표현과 untracked 파일 표시 방식, 직접 `python -c` 명령 재현성 문제이며, 19-2 진입을 차단하지 않는다.

다음 단계는 **yes — 19-2 settings / feature_flags / health 경계 정리 진입 가능** 이다.
