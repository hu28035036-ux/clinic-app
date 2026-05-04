# 20-1 Codex 검증 결과

검증 시각: 2026-05-04, `latest_codex_review_request.md` 최신본 기준.

## 판정

**통과.** `20-1_group_a`는 F-15 AI 의사 가드, F-7 privacy retention, F-8 audit retention 후보 함수를 추가했고, RAG pipeline 통합, PyInstaller hidden import 등록, 전용/전체 테스트 결과가 요청 문서의 핵심 주장과 일치한다.

다음 세션 진입은 가능하다. 단, retention 함수는 아직 helper 단계라 admin endpoint/cron 등 실제 트리거 설계가 후속으로 필요하고, PyInstaller 실제 빌드 smoke는 이번 직접 검증에서 수행하지 않았다.

## 직접 검증한 근거

- `reports/refactor/latest_codex_review_request.md`와 `reports/refactor/20-1_codex_review_request.md`가 동일함을 확인했다.
- Claude Code 요약 대신 실제 `git status`, `git diff --numstat`, 파일 줄 수, 핵심 패턴 검색, pytest/ruff/check_db_path 결과를 직접 확인했다.
- pytest는 venv launcher 한글 경로 문제를 피하기 위해 Codex 번들 Python + venv site-packages `PYTHONPATH` 방식으로 실행했다.

## 요청 문서와 실제 파일 비교

| 파일 | 요청 문서 주장 | 실제 확인 |
|---|---:|---:|
| `app/modules/ai/safety/__init__.py` | 16 | 16 |
| `app/modules/ai/safety/doctor_guard.py` | 78 | 77 |
| `app/modules/privacy/__init__.py` | 22 | 22 |
| `app/modules/privacy/retention.py` | 132 | 127 |
| `app/modules/audit/retention.py` | 60 | 60 |
| `tests/test_20_1_group_a.py` | 218 | 244 |

줄 수 표기는 일부 불일치하지만 파일은 모두 존재하고 테스트가 통과한다.

tracked diff:

| 파일 | 실제 diff |
|---|---:|
| `app/services/ai/rag/pipeline.py` | +10 |
| `dosu_clinic.spec` | +8 |
| `tests/test_pyinstaller_hidden_imports.py` | +6 |

삭제 파일은 없다.

## 구현 검증

- `app.modules.ai.safety.doctor_guard`에 `has_doctor_claim`, `block_doctor_claims`, 의사 이름/일정/진단 차단 reason 3종이 존재한다.
- `app/services/ai/rag/pipeline.py:validate_answer()`는 기존 PII, medical claim, execution claim, unsupported claim 차단 뒤 doctor guard를 호출한다.
- 기존 `validate_answer` 응답 key `{blocked, reason, cleaned, guard_hits}`는 유지된다.
- `app.modules.privacy.retention`에 `PATIENT_INACTIVE_MASK_MONTHS = 18`, `AI_LOG_RETENTION_MONTHS = 6`이 존재한다.
- `app.modules.audit.retention`에 `AUDIT_LOG_RETENTION_YEARS = 5`가 존재한다.
- retention 함수들은 `dry_run`을 지원하고, 실제 실행 시 DB commit을 수행한다.
- 20-1 신규 모듈 5개가 PyInstaller hidden import 대상에 추가됐고 hidden import 테스트가 통과했다.

## 테스트 재실행 결과

| 검증 | 결과 |
|---|---|
| `pytest tests/test_20_1_group_a.py -q` | 15 passed |
| `pytest tests/test_pyinstaller_hidden_imports.py -q` | 205 passed |
| `pytest tests -q` | 1696 passed, 1 skipped, 10 xfailed, 27 warnings |
| `.\venv\Scripts\ruff.exe check app tests scripts` | All checks passed |
| `scripts/check_db_path.py` | exit 0 |

warnings는 기존 AI/SMS/manual QA 계열 `PytestReturnNotNoneWarning`이며, 20-1 실패로 보이지 않는다. targeted pytest에서는 `.pytest_cache` 접근 권한 warning이 발생했다.

## Caveat

- 요청 문서의 일부 줄 수가 실제 파일 줄 수와 맞지 않는다. 기능/테스트 판정에는 영향이 없지만 문서 동기화가 필요하다.
- retention helper는 실제 운영 trigger가 아직 없다. 요청서도 v1 helper 함수 단계로 기록하고 있으므로 범위 내에서는 적절하다.
- F-15 의사 가드는 현재 RAG `validate_answer`에만 통합됐다. manual_qa / sms_draft / action_leave 등 다른 AI 응답 경계에 적용할지는 후속 결정이 필요하다.
- PyInstaller hidden import 테스트는 통과했지만, 실제 PyInstaller 빌드와 exe smoke는 이번 직접 검증에서 수행하지 않았다.

## 종합

20-1 그룹 A는 낮은 위험의 정책/가드/helper 도입으로 범위가 잘 제한되어 있다. 기존 API URL, 기존 응답 dict, DB schema, UI, migration은 변경하지 않았고, 신규 동작은 전용 테스트와 전체 회귀에서 통과했다.

결론: **20-1 통과, 다음 세션 진입 가능**.
