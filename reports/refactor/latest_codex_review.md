# 19-0 Codex 검증 결과

- 검증 대상: `reports/refactor/latest_codex_review_request.md` / `reports/refactor/19-0_codex_review_request.md` / `docs/refactor/19_refactor_baseline_test_result.md` / `reports/refactor/19-0_test_report.md`
- 검증일: 2026-05-03
- 기준 브랜치: `ai-rag-v1-integration`
- 판정: **pass with caveat**
- 다음 단계: **yes — 19-1 진입 가능. 단, dirty worktree 처리 방침은 사용자 결정 필요**

## 1. 검증 방식

Claude Code 요약은 신뢰 근거로 사용하지 않고, 실제 파일 구조와 문서 본문을 직접 대조했다.

- `reports/refactor/19-0_codex_review_request.md` 와 `reports/refactor/latest_codex_review_request.md` 를 비교했다. 결과는 동일했다.
- `reports/refactor/19-0_test_report.md` 와 `reports/refactor/latest_test_report.md` 를 비교했다. 결과는 동일했다.
- `docs/refactor/19_refactor_baseline_test_result.md` 의 테스트 요약, BG-1~BG-10, 운영 DB/외부 API 차단 문구를 실제 명령 결과와 대조했다.
- 전체 테스트, ruff, DB 경로 체크, PyInstaller hidden imports 테스트를 현재 환경에서 직접 재실행했다.
- 실제 파일 구조에서 endpoint / ORM / migration / test 수, line count, 부재 항목 grep을 재측정했다.
- `git diff --stat bcd74a7 -- app tests app/migrations dosu_clinic.spec requirements.txt requirements-dev.txt app/templates app/static pyproject.toml` 로 코드 변경 범위를 확인했다.

## 2. 명령 재실행 결과

| 명령 | 실제 결과 | 판정 |
|---|---|---:|
| `venv/Scripts/python.exe -m pytest tests -q` | **529 passed, 1 skipped, 7 xfailed, 27 warnings** (11.42초) | pass |
| `venv/Scripts/python.exe -m ruff check app tests scripts` | **All checks passed!** | pass |
| `venv/Scripts/python.exe scripts/check_db_path.py` | exit 0, 운영 DB 경로 감지 메시지 출력 | pass |
| `venv/Scripts/python.exe -m pytest tests/test_pyinstaller_hidden_imports.py -q` | **53 passed** (0.32초) | pass |

요청서의 C-1은 `-v --tb=short` 형식이지만, 이번 Codex 재검증은 같은 전체 테스트 집합을 `-q`로 실행했다. 결과 카운트는 요청서와 동일하다.

## 3. 실제 구조 대조

| 항목 | 실제값 | 문서 주장 | 판정 |
|---|---:|---:|---:|
| `app/routers/api.py` line count | newline 5127 / ReadLines 5128 | 5127 | pass |
| `app/routers/api.py` endpoint | 86 | 86 | pass |
| `app/routers/ai.py` line count | 929 | 929 | pass |
| `app/routers/ai.py` endpoint | 13 | 13 | pass |
| `app/templates/main.html` line count | 7331 | 7331 | pass |
| `app/static/css/app.css` line count | 3626 | 3626 | pass |
| `tests/test_*.py` | 40 | 40 | pass |
| ORM models | 19 | 19 | pass |
| migrations `m0*.py` | 13 | 13 | pass |
| `docs/refactor` files | 13 | baseline result 신규 포함 | pass |
| `reports/refactor` files | 26 | 19-0 신규 report/review 포함 | pass |

부재 항목 `Doctor`, `Department`, `Room`, `DoctorSchedule`, `Order`, `Prescription`, `Resource`, `doctor_id`, `no_show`, `/api/health` 는 `rg` 결과 0건으로 확인했다.

## 4. 코드 변경 범위

`git diff --stat bcd74a7 -- app tests app/migrations dosu_clinic.spec requirements.txt requirements-dev.txt app/templates app/static pyproject.toml` 결과는 기존 18-x tracked 변경 범위와 동일했다.

```text
app/models/models.py         | 123 +++++++++++++++++-
app/routers/ai.py            |  42 ++++++
app/services/ai/manual_qa.py | 298 +++++++------------------------------------
dosu_clinic.spec             |  30 ++++-
tests/conftest.py            | 132 +++++++++++++++++++
5 files changed, 373 insertions(+), 252 deletions(-)
```

따라서 본 19-0 검증 산출은 docs/reports 중심이며, app/tests/spec/UI/migrations/requirements 범위의 신규 코드 변경은 확인되지 않았다.

## 5. BG 게이트 결과

| 게이트 | 결과 | 근거 |
|---|---:|---|
| BG-1 코드 무수정 | pass | 본 19-0 추가 app/tests/spec/UI/migration/requirements 변경 0 |
| BG-2 18-8 baseline 회귀 0 | pass | 529 / 1 / 7 재현 |
| BG-3 ruff lint | pass | All checks passed |
| BG-4 운영 DB 보호 | pass | `check_db_path.py` exit 0 + 테스트 전체 통과 |
| BG-5 외부 API 차단 | pass | FakeProvider / `_block_sdk_modules` 관련 테스트 통과 |
| BG-6 PyInstaller 53 tests | pass | 53 passed |
| BG-7 baseline 측정값 drift 0 | pass | line count / endpoint / ORM / migration / test 수 정합 |
| BG-8 부재 항목 단정 금지 | pass | grep 0건 |
| BG-9 AI/RAG 하네스 + 기존 기능 회귀 | pass | 전체 테스트 529/1/7 통과 |
| BG-10 dirty worktree 처리 | pass with caveat | 사용자 결정 필요 |

## 6. 남은 Caveats

1. `reports/refactor`와 `reports/ai_dev_loop` 양쪽에 19-0 test report 계열이 존재한다. 현재 요청서와 신규 산출 기준은 `reports/refactor/19-0_test_report.md` / `reports/refactor/latest_test_report.md` 이며, `reports/ai_dev_loop` 쪽 19-0 리포트는 별도 이전 버전이라 내용이 다르다. 소비자가 어느 경로를 공식 latest로 볼지 명확히 해야 한다.
2. `check_db_path.py` 단독 실행은 운영 DB 경로를 감지한다. 문서 설명처럼 단독 실행 시 정상 메시지이고, 테스트 중 운영 DB 미접근은 `tests/conftest.py` 격리와 전체 테스트 통과로 간접 검증된다.
3. 현재 worktree는 여전히 dirty 상태다. modified tracked 6개와 다수 untracked 파일이 있으며, 19-1 시작 전 처리 방침이 필요하다.

## 7. 종합 판정

19-0 baseline 재고정 요청서의 핵심 주장은 실제 파일 구조와 현재 테스트 재실행 결과로 확인됐다. 전체 테스트, ruff, DB 경로 체크, PyInstaller 53 tests가 모두 통과했고, baseline 카운트와 부재 항목 grep도 문서와 맞다.

따라서 판정은 **pass with caveat** 이다. caveat는 경로 중복과 dirty worktree 처리 문제이며, 19-1 진입 자체를 차단하지 않는다.

다음 단계는 **yes — 19-1 진입 가능** 이다. 단, dirty worktree 처리 방침을 먼저 확정하는 것이 좋다.
