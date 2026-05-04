# 19-11 Codex 검증 결과

재검증 시각: 2026-05-04, latest 요청 문서 기준. 동일 19-11 요청에 대해 실제 diff와 테스트를 재확인했다.

## 판정

**통과.** `latest_codex_review_request.md`가 가리키는 19-11 stats aggregation boundary 후보 분리는 실제 파일 구조, tracked diff, import 경계, hidden import 등록, 테스트 재실행 결과 기준으로 요청 내용과 일치한다. 19-12 admin / backup / audit / export_import 분리로 진입 가능하다고 판단한다.

단, pytest는 기존 venv launcher 한글 경로 문제 때문에 Codex 번들 Python 3.12.13에 `venv\Lib\site-packages`와 repo root를 `PYTHONPATH`로 연결해 실행했다. pytest 버전은 venv의 8.4.2를 사용했다.

## 직접 검증한 기준

- `reports/refactor/latest_codex_review_request.md`와 `reports/refactor/19-11_codex_review_request.md`가 동일함을 확인했다.
- `reports/refactor/latest_test_report.md`와 `reports/refactor/19-11_test_report.md`가 동일함을 확인했다.
- `reports/refactor/latest_fix_summary.md`와 `reports/refactor/19-11_fix_summary.md`가 동일함을 확인했다.
- Claude Code 요약 대신 실제 `git status`, `git diff --stat`, `git diff --numstat`, 파일 목록, import 경계, PyInstaller hidden import, pytest/ruff/check_db_path 실행 결과를 직접 확인했다.

## 실제 파일 구조

파일 줄 수는 `[System.IO.File]::ReadAllLines(...).Count` 기준이다.

| 파일 | 실제 줄 수 | 요청 문서 주장 |
|---|---:|---:|
| `app/modules/stats/__init__.py` | 43 | 43 |
| `app/modules/stats/rules.py` | 182 | 182 |
| `app/modules/stats/repository.py` | 201 | 201 |
| `app/modules/stats/aggregators.py` | 271 | 271 |
| `app/modules/stats/service.py` | 272 | 272 |
| `app/modules/stats/schemas.py` | 170 | 170 |
| `tests/test_19_11_stats.py` | 776 | 776 |

요청 문서의 신규 파일 목록과 실제 파일 구조가 일치한다.

## 실제 diff

tracked diff 기준:

| 파일 | 실제 diff |
|---|---:|
| `dosu_clinic.spec` | +9 |
| `tests/test_pyinstaller_hidden_imports.py` | +6 |

`app/routers/api.py`에는 diff가 없다. 신규 `app/modules/stats/`와 `tests/test_19_11_stats.py`는 현재 untracked 파일이다.

## 의존성 / read-only 경계

- `app.modules.stats` 신규 모듈 import 라인에는 `app.routers`, `fastapi`, `app.database`, 외부 HTTP 호출 라이브러리 의존성이 없다.
- `repository.py`는 `app.models.models`와 `app.models.constants`를 함수 내부 lazy import로 사용한다.
- `rules.py`도 `app.models.constants`를 함수 내부에서만 참조한다. ORM 모델 직접 import는 확인되지 않았다.
- `aggregators.py`는 DB 세션을 받지 않고 caller가 넘긴 row만 집계한다.
- stats 신규 파일들에서 `db.commit`, `db.add(`, `db.delete(`, `db.flush` 사용은 확인되지 않았다.
- `urllib.request`, `requests`, `httpx` import 라인은 stats 신규 모듈에서 확인되지 않았다.

## 시간 가중치 회귀 방지

- `rules.MANUAL_COUNT_INCREMENT_PER_APPT = 1`과 `rules.TIME_WEIGHTED_COUNT_DENIED = True`가 존재한다.
- `aggregators.py`는 `MANUAL_COUNT_INCREMENT_PER_APPT`를 통해 count를 증가시키며, `+= 2`, `* 2`, `*= 2` 패턴은 테스트에서 금지된다.
- `test_aggregate_summary_unit_increment_only`로 manual30 + manual60 = total 2 정책을 검증한다.

## PyInstaller hidden import

`dosu_clinic.spec`와 `tests/test_pyinstaller_hidden_imports.py` 모두 19-11 신규 모듈 6개를 포함한다.

- `app.modules.stats`
- `app.modules.stats.rules`
- `app.modules.stats.repository`
- `app.modules.stats.aggregators`
- `app.modules.stats.service`
- `app.modules.stats.schemas`

## 테스트 재실행 결과

venv launcher 문제 때문에 pytest 명령은 다음 실행 형태로 검증했다.

`PYTHONPATH = .\venv\Lib\site-packages;.`  
`C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest ...`

| 검증 | 결과 |
|---|---|
| `tests/test_19_11_stats.py -q` | 90 passed |
| `tests/test_pyinstaller_hidden_imports.py -q` | 155 passed |
| `tests -k "ai_sms or ai_leave or rag or safety or contract" -q` | 142 passed, 1201 deselected, 22 warnings |
| `tests -q` | 1335 passed, 1 skipped, 7 xfailed, 27 warnings |
| `.\venv\Scripts\ruff.exe check app tests scripts` | All checks passed |
| `scripts/check_db_path.py` | exit 0 |

요청 문서의 전체 테스트 표에는 warnings가 생략되어 있으나, 실제 전체 pytest 로그에는 기존 AI/SMS/manual QA 테스트의 `PytestReturnNotNoneWarning` 27개가 표시된다. 이번 19-11 stats 변경 실패로 보이지 않는다.

## 확인된 환경 이슈 / 잔여물

- `.\venv\Scripts\python.exe -m pytest ...` 형태는 한글 경로 launcher 문제로 신뢰하기 어렵다. 이번 검증은 Codex 번들 Python + venv site-packages 방식으로 수행했다.
- `.codex-pytest-basetemp-19-9` 임시 디렉터리는 이전 검증에서 생긴 권한 잔여물이며, 여전히 `git status`에서 접근 권한 warning을 만든다. 기능 변경과 테스트 판정에는 영향이 없다.
- `docs/ai/`는 untracked 상태이며 19-11 기능 diff 범위 밖의 별도 계획 문서로 보인다.

## 종합

19-11은 stats 규칙, read-only 조회, 순수 집계 함수, 응답 dict 빌더, 응답 키 contract를 `app.modules.stats` 경계 안에 추가했고, 기존 router/API/schema/migration 본체는 건드리지 않은 것으로 확인된다. count 정책은 예약 1건 = count 1로 보호되고, 시간 가중치 회귀 방지 테스트도 통과했다.

따라서 **19-12 진입 가능**으로 결론낸다. 커밋 전에는 `docs/ai/` 포함 여부와 `.codex-pytest-basetemp-19-9` 권한 잔여물 정리를 별도로 결정하면 된다.
