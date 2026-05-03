# latest_test_report.md — 18-1_structure_refactor

## 환경
- 작업일: 2026-05-01
- 브랜치: `ai-rag-v1-integration`
- Python: 3.12.10 (`venv/Scripts/python.exe`)
- pytest: 8.4.2 / pluggy 1.6.0
- 작업 모드: 5회 루프, **2회 수정 후 통과**

## 실행 명령
```
venv\Scripts\python.exe -m pytest tests/test_ai_full_harness.py tests/test_ai_manual_rag_harness.py tests/test_ai_manual_rag_contract.py tests/test_ai_safety_harness.py -v
venv\Scripts\python.exe -m pytest tests -v
venv\Scripts\python.exe -m ruff check app tests scripts
venv\Scripts\python.exe scripts\check_db_path.py
```

## 결과 요약

### 1) 18-1 신규 테스트 4개 파일 (사용자 명시 명령)
- **48 passed in 0.40s**
  ```
  tests/test_ai_full_harness.py            9 passed
  tests/test_ai_manual_rag_harness.py     19 passed
  tests/test_ai_manual_rag_contract.py     9 passed
  tests/test_ai_safety_harness.py         11 passed
  ─────────────────────────────────────────────────
  합계                                    48 passed
  ```

### 2) `pytest tests -v` (전체 회귀)
- **255 passed, 1 skipped, 7 xfailed, 27 warnings in 6.84s**
- 18-0 결과 (207) 대비 +48 = 255 (모두 신규 18-1 테스트). **회귀 0**.

### 3) `ruff check app tests scripts`
- 1차: 4 errors (I001 import 정렬 — 신규 4개 테스트 파일)
- `--fix` 적용 → **All checks passed!**

### 4) `scripts/check_db_path.py`
- 정상 종료 (스크립트 단독 실행 시 운영 경로 안내는 의도된 동작 — 테스트 중에는 conftest 4단계 격리 작동)

## 5회 루프 기록
| 회차 | 결과 | 원인 / 수정 |
|---|---|---|
| 1 | 1 fail | `from app.services.rag import search` 가 함수 export — `search.search` 접근 불가 |
| 2 | 1 fail | `import app.services.rag.search as M` 도 동명 attribute 우선 — 모듈 객체 아님 |
| 3 | 48 pass | `importlib.import_module(...)` + `sys.modules` 사용으로 모듈 객체 명시 획득 |
| 4 | ruff 4 err | I001 (신규 테스트 import 정렬) — `--fix` 자동 적용 |
| (최종) | **통과** | 255 passed / All checks passed / check_db_path OK |

## 외부 호출 차단 동작 확인
- `tests/test_ai_full_harness.py::test_no_circular_import_when_loading_skeleton` — 14개 신규 모듈 모두 독립 import 가능 + 기존 `manual_qa` / `rag.search` 도 import 그대로
- 18-0 의 conftest §7 SDK monkeypatch 그대로 동작 → 18-1 신규 모듈은 SDK 호출 경로 부재

## 신규 18-1 테스트 카운트
- **회귀 검증** (기존 동작 보존): test_ai_full_harness 9 + test_ai_manual_rag_harness 8 (manual_qa unchanged + 5 schemas + 3 prompts/safety) + test_ai_manual_rag_contract 9 + test_ai_safety_harness 8 (PII/blocked/key)
- **신규 골격 검증**: schemas 8 (Source/Answer/reason_code/AI mode) + prompts 4 + safety stub 2 + pipeline/retriever NotImplementedError 2

## 주요 로그 발췌
```
============================= 48 passed in 0.40s ==============================
============================= 255 passed, 1 skipped, 7 xfailed, 27 warnings in 6.84s ============================
All checks passed!
```
- 27개 warning 은 18-0 이전부터 존재하던 기존 `test_ai_sms_*.py` 의 `PytestReturnNotNoneWarning`. 18-1 작업과 무관, 변동 0.
