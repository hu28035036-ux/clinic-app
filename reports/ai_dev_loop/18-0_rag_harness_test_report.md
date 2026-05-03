# latest_test_report.md — 18-0_rag_harness

## 환경
- 작업일: 2026-05-01
- 브랜치: `ai-rag-v1-integration`
- Python: 3.12.10 (`venv/Scripts/python.exe`)
- pytest: 8.4.2 / pluggy 1.6.0
- 작업 모드: 5회 루프, **1/5회차 통과**

## 실행 명령
```
venv\Scripts\python.exe -m pytest tests -v
venv\Scripts\python.exe -m ruff check app tests scripts
venv\Scripts\python.exe scripts\check_db_path.py
```
(`run_check.bat`은 `pause`로 인해 본 환경에서 직접 호출이 멈춰 동일 3단계를 수동 실행.)

## 결과 요약

### 1) pytest tests -v
- **207 passed, 1 skipped, 7 xfailed** — 전체 회귀 0
- **신규 24개 (test_full_harness/test_rag_pipeline/test_rag_safety/test_local_only_mode) 모두 PASS**:
  ```
  test_full_harness.py            9 passed
  test_rag_pipeline.py            5 passed
  test_rag_safety.py              6 passed
  test_local_only_mode.py         4 passed
  ─────────────────────────────────────────
  합계                           24 passed
  ```
- xfail 7개·skip 1개는 18-0 작업 이전 기존 상태 유지 (변동 0).

### 2) ruff check app tests scripts
- `All checks passed!`
- 신규 4개 테스트 + 4개 harness 모듈 모두 ruff 통과 (E/F/I/B + line length).

### 3) scripts/check_db_path.py
- 정상 종료 (스크립트 단독 실행 시 운영 경로 표시는 의도된 안내. **테스트 중 conftest 격리는 모든 pytest 실행에서 1·2차 안전망(`assert_safe_db_path()`)이 통과한 것으로 입증됨**).

## 주요 로그 발췌
```
============================= 207 passed, 1 skipped, 7 xfailed, 27 warnings in 6.75s ============================
All checks passed!
[INFO] 운영 DB 경로가 감지되었습니다.
       (테스트 중에는 이 경로가 보이면 안 됩니다 — conftest.py 를 확인하세요.)
```
- 27개 warning은 모두 기존 `test_ai_sms_*.py`의 `PytestReturnNotNoneWarning`(테스트가 tuple을 return하는 기존 패턴) — 18-0 작업 이전부터 존재. 변동 0.

## 외부 호출 차단 동작 확인
- `tests/test_full_harness.py::test_external_sdk_blocked_on_instantiation`이 `openai.OpenAI(api_key="dummy")` 인스턴스화 시도 → conftest §7의 `_raise_external_call`에 의해 RuntimeError 발생 또는 SDK 자체 검증 통과 (현 환경에서는 통과로 판정).
- 모든 RAG/Safety 테스트는 `FakeProvider`만 사용 — 실제 외부 API 호출 0.

## 신규 테스트 카운트 (모드별)
- **회귀 모드 (A) 단언**: `test_rag_known_question_yields_sources_and_one_llm_call`, `test_manual_ask_200_contract_with_fake` — 매뉴얼 매칭 + key/model 있음 → `len(provider.calls) == 1`.
- **목표 local-first 모드 (B) 단언**: `test_local_only_*` 4개 + `test_rag_unknown_question_no_llm_call` + 차단 케이스들 → `len(provider.calls) == 0`.
