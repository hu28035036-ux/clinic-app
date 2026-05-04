# 19-10 Codex 검증 결과

재검증 시각: 2026-05-04, latest 요청 문서 기준. 동일 19-10 요청에 대해 실제 diff와 테스트를 재확인했다.

## 판정

**통과.** `latest_codex_review_request.md`가 가리키는 19-10 SMS target / template / provider boundary 후보 분리는 실제 파일 구조, tracked diff, import 경계, hidden import 등록, 테스트 재실행 결과 기준으로 요청 내용과 일치한다. 19-11 stats 분리로 진입 가능하다고 판단한다.

단, 이전 검증에서 확인된 venv launcher 문제가 계속 있어, pytest는 Codex 번들 Python 3.12.13에 `venv\Lib\site-packages`와 repo root를 `PYTHONPATH`로 연결해 실행했다. pytest 버전은 venv의 8.4.2를 사용했다.

## 직접 검증한 기준

- `reports/refactor/latest_codex_review_request.md`와 `reports/refactor/19-10_codex_review_request.md`가 동일함을 확인했다.
- `reports/refactor/latest_test_report.md`와 `reports/refactor/19-10_test_report.md`가 동일함을 확인했다.
- `reports/refactor/latest_fix_summary.md`와 `reports/refactor/19-10_fix_summary.md`가 동일함을 확인했다.
- Claude Code 요약 대신 실제 `git status`, `git diff --stat`, `git diff --numstat`, 파일 목록, import 경계, PyInstaller hidden import, pytest/ruff/check_db_path 실행 결과를 직접 확인했다.

## 실제 파일 구조

파일 줄 수는 `[System.IO.File]::ReadAllLines(...).Count` 기준이다.

| 파일 | 실제 줄 수 | 요청 문서 주장 |
|---|---:|---:|
| `app/modules/sms/__init__.py` | 48 | 48 |
| `app/modules/sms/rules.py` | 174 | 174 |
| `app/modules/sms/templates.py` | 144 | 144 |
| `app/modules/sms/service.py` | 229 | 229 |
| `app/modules/sms/provider.py` | 225 | 225 |
| `app/modules/sms/schemas.py` | 106 | 106 |
| `tests/test_19_10_sms.py` | 881 | 881 |

요청 문서의 신규 파일 목록과 실제 파일 구조가 일치한다.

## 실제 diff

tracked diff 기준:

| 파일 | 실제 diff |
|---|---:|
| `dosu_clinic.spec` | +9 |
| `tests/test_pyinstaller_hidden_imports.py` | +7 |

`app/routers/api.py`와 `app/services/ai/sms_draft.py`에는 diff가 없다. 신규 `app/modules/sms/`와 `tests/test_19_10_sms.py`는 현재 untracked 파일이다.

## 의존성 / 외부 호출 경계

- SMS 신규 모듈 import 라인에는 `app.routers`, `fastapi`, `sqlalchemy`, `app.database`, `app.models` 의존성이 없다.
- `service.py`는 `app.modules.sms.rules`만 참조한다.
- `provider.py`는 `SmsProvider` Protocol, `ProviderResult`, `FakeSmsProvider`, `NotConfiguredProvider`를 제공하며 실제 외부 발송 구현은 없다.
- SMS 신규 모듈 import 라인에는 `urllib.request`, `requests`, `httpx`가 없다.
- `urllib.request` 문자열은 주석과 테스트 검증 문구에만 등장한다. 운영 발송 흐름은 기존 `app/routers/api.py` inline 흐름을 건드리지 않은 상태다.
- `app/routers/api.py`, DB schema, migration, AI SMS draft 본체 변경은 확인되지 않았다.

## PyInstaller hidden import

`dosu_clinic.spec`와 `tests/test_pyinstaller_hidden_imports.py` 모두 19-10 신규 모듈 6개를 포함한다.

- `app.modules.sms`
- `app.modules.sms.rules`
- `app.modules.sms.templates`
- `app.modules.sms.service`
- `app.modules.sms.provider`
- `app.modules.sms.schemas`

## 테스트 재실행 결과

venv launcher 문제 때문에 pytest 명령은 다음 실행 형태로 검증했다.

`PYTHONPATH = .\venv\Lib\site-packages;.`  
`C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest ...`

| 검증 | 결과 |
|---|---|
| `tests/test_19_10_sms.py -q` | 108 passed |
| `tests/test_pyinstaller_hidden_imports.py -q` | 143 passed |
| `tests -k "ai_sms or ai_leave or rag or safety or contract" -q` | 130 passed, 1111 deselected, 22 warnings |
| `tests -q` | 1233 passed, 1 skipped, 7 xfailed, 27 warnings |
| `.\venv\Scripts\ruff.exe check app tests scripts` | All checks passed |
| `scripts/check_db_path.py` | exit 0 |

전체 테스트는 pytest cache/temp 권한 문제가 반복되어 권한 상승 실행으로 확인했고, 요청 문서와 같은 `1233 passed, 1 skipped, 7 xfailed, 27 warnings` 결과를 얻었다.

warnings는 기존 AI/SMS/manual QA 테스트에서 test 함수가 tuple을 return하는 `PytestReturnNotNoneWarning` 계열이며, 이번 19-10 변경 실패로 보이지 않는다.

## 보안 / PII 검증 관찰

- `serialize_sms_setting_masked`, password/API key masking helper, `sanitize_secrets` 경계가 테스트에 포함되어 있고 통과했다.
- `GET /api/sms/setting` 응답에서 평문 비밀값이 노출되지 않는 contract가 19-10 테스트에 포함되어 있다.
- 환자 전화번호/이름 등 SMS 대상 응답의 PII 평문 유지 여부는 기존 UI/SMS 발송 흐름 호환을 위한 것으로, 이번 19-10에서 마스킹 정책을 바꾸지 않은 것으로 확인했다.
- 신규 SMS 모듈 자체는 추가 로깅을 만들지 않는다.

## 확인된 환경 이슈 / 잔여물

- `.\venv\Scripts\python.exe -m pytest ...` 형태는 한글 경로 launcher 문제로 신뢰하기 어렵다. 이번 검증은 Codex 번들 Python + venv site-packages 방식으로 수행했다.
- `.codex-pytest-basetemp-19-9` 임시 디렉터리는 이전 검증에서 생긴 권한 잔여물이며, 여전히 `git status`에서 접근 권한 warning을 만든다. 기능 변경과 테스트 판정에는 영향이 없다.
- `docs/ai/`는 untracked 상태이며 19-10 기능 diff 범위 밖의 별도 계획 문서로 보인다.

## 종합

19-10은 SMS 전화번호/비밀값 규칙, 템플릿 조립, 응답 dict 빌더, provider stub, 응답 키 contract를 `app.modules.sms` 경계 안에 추가했고, 기존 router/API/schema/migration/AI SMS draft 본체는 건드리지 않은 것으로 확인된다. 실제 외부 문자 발송 구현도 추가되지 않았다.

따라서 **19-11 진입 가능**으로 결론낸다. 커밋 전에는 `docs/ai/` 포함 여부와 `.codex-pytest-basetemp-19-9` 권한 잔여물 정리를 별도로 결정하면 된다.
