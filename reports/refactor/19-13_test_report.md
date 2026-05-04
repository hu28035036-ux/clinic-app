# 19-13 AI commands와 기존 예약/휴무/문자 연결부 정리 — 테스트 결과

## 세션 이름

`19-13_ai_commands_boundary` — AI commands Preview / Approval / Execute 경계 helper
(schemas / safety / preview / executor / service / adapters) 분리. 라우터 / 서비스
본체 *완전 무수정*.

## 실행 명령

```
venv\Scripts\python.exe -m pytest tests -q
venv\Scripts\python.exe -m pytest tests/test_19_13_ai_commands.py -v
venv\Scripts\python.exe -m pytest tests/test_pyinstaller_hidden_imports.py -v
venv\Scripts\python.exe -m pytest tests -k "ai_sms or ai_leave or rag or safety or contract or action_leave" -q
venv\Scripts\python.exe -m ruff check app tests scripts
venv\Scripts\python.exe scripts/check_db_path.py
```

## 환경

- OS: Windows 11
- Python: venv\Scripts\python.exe (한글 경로 venv)
- pytest: 8.4.2
- ruff: venv\Scripts\ruff.exe
- 시각: 2026-05-04

## 실행 결과 요약

| 검증 | 결과 |
|---|---|
| `tests -q` (전체) | **1659 passed, 1 skipped, 7 xfailed, 27 warnings** |
| `tests/test_19_13_ai_commands.py` (신규) | **156 passed** |
| `tests/test_pyinstaller_hidden_imports.py` | **195 passed** |
| `tests -k "ai_sms or ai_leave or rag or safety or contract or action_leave"` | **270 passed, 1397 deselected, 21 warnings** |
| `ruff check app tests scripts` | **All checks passed!** |
| `scripts/check_db_path.py` | **exit 0** |

19-12 baseline (1487 passed) → 19-13 (1659 passed). **172 케이스 증가**:

- `tests/test_19_13_ai_commands.py` — 156 cases (AI commands contract / safety
  / preview / executor / service / adapters)
- `tests/test_pyinstaller_hidden_imports.py` — 16 cases (8 신규 모듈 × 2 검증)

## 자동 수정 루프

| 회차 | 가설 | 변경 | 결과 |
|---|---|---|---|
| 1 | 신규 contract test 작성 후 1회차 실행 | 8 신규 파일 (ai/__init__ + commands/×6 + adapters) + spec / hidden imports + contract test 156 케이스 | 1 fail (`test_services_sms_draft_no_direct_send` — sms_draft.py 의 docstring 에 `/api/sms/send 호출 금지` 정책 문구가 검출 패턴에 매칭) |
| 2 | docstring 정책 문구가 매칭되는 문제 — 실제 호출 패턴으로 검증 | `httpx.post` / `httpx.Client` / `requests.post` / `urllib.request.Request` / `fetch(` 부재 검증 (실제 외부 호출 코드만 검사) | 156 / 156 통과 |
| (보정) | ruff 자동 보정 | import block 정렬 | All checks passed |

**총 1 회차 코드 수정** + ruff 자동 보정 1회. 5회 한도 내. **5회 실패 미해당**.

## 실패 / 우회 없음

- `pyproject.toml` per-file-ignores 무수정.
- 운영 DB (`%APPDATA%\도수치료예약\clinic.db`) 직접 open 부재.
- 외부 API 호출 부재 (8 파일 × urllib / requests / httpx / openai / anthropic /
  shutil / sqlite3 import 부재 단위 테스트 통과).
- LLM provider 호출 부재 (8 파일 × `provider.generate(` / `provider.chat(` / 
  `.chat.completions.create(` / `anthropic.messages.create(` 패턴 부재 검증).
- DB schema / migration 무수정.
- 라우터 / 서비스 본체 무수정 (라우터 시그니처 검증 13 케이스 + 서비스 본체 검증
  12 케이스 통과).

## 기존 회귀 보호

| 영역 | 결과 |
|---|---|
| AI action_leave (휴무 AI) — parse / preview / execute | 통과 |
| AI sms_draft (문자 AI) — make_draft / PII 가드 / 환각 가드 | 통과 |
| AI manual_qa (매뉴얼 Q&A) — search / ask | 통과 |
| AI sms_validate | 통과 |
| RAG / Safety / Full / Vector / Hybrid 하네스 | 통과 |
| API contract (manual/search 3키 + manual/ask 9키 + sources 3키 + health 9키 +
  status 9키 + sms/draft 7키 + action/parse 6키 + action/preview 11키 +
  action/execute 5키) | 통과 |
| 예약 / 휴무 / 치료항목 / 환자 / 치료사 / 통계 / 문자 (19-1~19-12) | 통과 |
| 관리자 인증 / 백업 / 복구 / audit / data-convert (19-12) | 통과 |

## 확인된 환경 잔여물 / 비-issue

- `tests/test_ai_sms_validate.py` 의 27 warnings (`PytestReturnNotNoneWarning`) —
  19-13 변경과 무관. 19-12 baseline 에서도 동일.
- `docs/ai/` untracked — 19-13 변경 범위 밖 (기존 계획 문서).
