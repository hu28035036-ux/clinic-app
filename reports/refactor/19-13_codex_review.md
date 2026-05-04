# 19-13 Codex 검증 결과

검증 시각: 2026-05-04, `latest_codex_review_request.md` 최신본 기준.

## 판정

**통과.** `19-13_ai_commands_boundary`는 실제 파일 구조, tracked diff, PyInstaller hidden import, AI commands 응답 contract, Preview / Approval / Execute 경계, provider/DB/PII 보호 경계, 테스트 재실행 결과 기준으로 요청 내용과 일치한다.

따라서 **19-14 진입 가능**으로 판단한다.

## 직접 검증한 근거

- `reports/refactor/latest_codex_review_request.md`와 `reports/refactor/19-13_codex_review_request.md`가 동일함을 확인했다.
- `reports/refactor/latest_test_report.md`와 `reports/refactor/19-13_test_report.md`가 동일함을 확인했다.
- `reports/refactor/latest_fix_summary.md`와 `reports/refactor/19-13_fix_summary.md`가 동일함을 확인했다.
- Claude Code 요약 대신 실제 `git status`, `git diff --stat`, `git diff --numstat`, 파일 줄 수, import/호출 금지 패턴, PyInstaller hidden import, pytest/ruff/check_db_path 결과를 직접 확인했다.

## 실제 파일 구조

줄 수는 `[System.IO.File]::ReadAllLines(...).Count` 기준이다.

| 파일 | 실제 줄 수 | 요청 문서 |
|---|---:|---:|
| `app/modules/ai/__init__.py` | 70 | 70 |
| `app/modules/ai/commands/__init__.py` | 46 | 46 |
| `app/modules/ai/commands/schemas.py` | 304 | 304 |
| `app/modules/ai/commands/safety.py` | 207 | 207 |
| `app/modules/ai/commands/preview.py` | 165 | 165 |
| `app/modules/ai/commands/executor.py` | 84 | 84 |
| `app/modules/ai/commands/service.py` | 81 | 81 |
| `app/modules/ai/commands/adapters.py` | 100 | 100 |
| `tests/test_19_13_ai_commands.py` | 797 | 797 |

요청 문서의 신규 파일 목록과 실제 파일 구조는 일치한다.

## 실제 diff

tracked diff 기준:

| 파일 | 실제 diff | 요청 문서 |
|---|---:|---:|
| `dosu_clinic.spec` | +29 | +29 |
| `tests/test_pyinstaller_hidden_imports.py` | +22 | +22 |

`app/routers/ai.py`, `app/services/ai/`, `app/services/rag/`에는 diff가 없다. 신규 `app/modules/ai/`와 `tests/test_19_13_ai_commands.py`는 현재 untracked 신규 파일이다.

## PyInstaller hidden import

`dosu_clinic.spec`와 `tests/test_pyinstaller_hidden_imports.py` 모두 19-13 신규 모듈 8개를 포함한다.

- `app.modules.ai`
- `app.modules.ai.commands`
- `app.modules.ai.commands.schemas`
- `app.modules.ai.commands.safety`
- `app.modules.ai.commands.preview`
- `app.modules.ai.commands.executor`
- `app.modules.ai.commands.service`
- `app.modules.ai.commands.adapters`

## AI commands 경계 / 보호 검증

- 신규 helper에서 `app.routers` import는 발견되지 않았다.
- `app.services.ai.*` 문자열은 `commands/adapters.py`의 흐름 후보 상수에만 존재하며, 직접 import 문은 아니다.
- 신규 helper에는 `urllib`, `requests`, `httpx`, `openai`, `anthropic`, `shutil`, `sqlite3` import가 없다. `openai_client`, `anthropic_client`는 package docstring의 기존 파일명 언급으로만 잡힌다.
- 신규 helper에는 `provider.generate(`, `provider.chat(`, `.chat.completions.create(`, `anthropic.messages.create(` 호출 패턴이 없다.
- 신규 helper에는 `db.commit(`, `db.add(`, `db.delete(`, `db.flush(` 실행 패턴이 없다.
- `REASON_CODES_PROVIDER_BLOCKED`, `REASON_CODES_APPROVAL_REQUIRED`, `SMS_DRAFT_FORBIDDEN_RESPONSE_KEYS`, `SMS_DRAFT_RESPONSE_KEYS`, `TOKEN_TTL_SEC = 120`, `TOKEN_VERSION = 1`, `INTENT_NAMES_*` contract가 테스트와 실제 파일에서 확인됐다.
- `SMS_DRAFT_FORBIDDEN_RESPONSE_KEYS`는 `prompt_text`, `response_text`를 포함하고 응답 key와 분리된다.
- provider 차단 reason과 approval required reason 집합은 테스트에서 disjoint 검증을 통과했다.

## 테스트 재실행 결과

venv launcher 문제가 있어 pytest는 Codex 번들 Python에 venv site-packages와 workspace를 `PYTHONPATH`로 연결해 실행했다.

| 검증 | 결과 |
|---|---|
| `pytest tests/test_19_13_ai_commands.py -q` | 156 passed |
| `pytest tests/test_pyinstaller_hidden_imports.py -q` | 195 passed |
| `pytest tests -k "ai_sms or ai_leave or rag or safety or contract or action_leave" -q` | 270 passed, 1397 deselected, 22 warnings |
| `pytest tests -q` | 1659 passed, 1 skipped, 7 xfailed, 27 warnings |
| `.\venv\Scripts\ruff.exe check app tests scripts` | All checks passed |
| `scripts/check_db_path.py` | exit 0 |

warnings는 기존 AI/SMS/manual QA 계열 `PytestReturnNotNoneWarning`와 일부 cache warning이며, 19-13 기능 실패로 보이지 않는다.

## 환경 이슈 / 잔여물

- `.\venv\Scripts\python.exe -m pytest ...` 형태는 한글 경로 launcher 문제로 신뢰하기 어려워, 이번 검증은 Codex 번들 Python + venv site-packages 방식으로 수행했다.
- `.pytest_cache` 접근 권한 warning은 비상승 targeted pytest에서 발생했지만 테스트 판정에는 영향이 없다.
- `git status`의 `C:\Users\user/.config/git/ignore` permission warning은 이전부터 보이는 환경 warning이며 기능 diff와 무관하다.
- 기존 untracked `docs/ai/`, 19-12 신규 파일들은 19-13 검증 범위 밖 잔여 상태다.

## 종합

19-13은 AI commands의 응답 key contract, reason_code 분류, read-only Preview, 확인 기반 Execute, provider 호출 차단, 승인 없는 DB write 차단 정책을 신규 후보 모듈로 분리했다. 기존 `app/routers/ai.py`, `app/services/ai/*`, `app/services/rag/*` 본체에는 diff가 없고, PyInstaller hidden import와 contract 테스트도 요청 문서와 일치한다.

결론: **19-14 진입 가능**.
