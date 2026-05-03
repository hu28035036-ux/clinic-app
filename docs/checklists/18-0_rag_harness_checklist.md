# 18-0 체크리스트 — RAG/Safety/전체 하네스 최소 버전

> 이 문서는 해당 세션에서 반드시 확인해야 하는 실행 체크리스트다.
> 공통 규칙은 `docs/AI_WORKING_RULES.md`와 `docs/ai_code_session_protocol.md`를 먼저 확인한다.
> 상세 설계는 관련 ai_rag 문서를 참조한다.

**메타**: 목적=18-0 실행 가이드 · 시점=18-0 시작 시 · 독자=Claude Code/Codex/사용자 · 관련=`ai_harness_overview.md`, `harnesses/{full,rag,safety}_harness_plan.md` · 결정=실행 범위/완료 조건 · 비결정=하네스 세부 기준(harnesses/* 참조)·세션 절차 일반(`ai_code_session_protocol.md` 참조).

## 세션 목표
모든 후속 세션이 의지할 하네스 골격을 만든다. v1.3.3 회귀 0을 보장하면서 FakeProvider/FakeEmbeddingProvider · 외부 SDK monkeypatch · RAG/Safety fixture · API 계약 단언을 도입한다.

## 수정 가능 범위
`tests/conftest.py` 보강 / `tests/harness/{rag_harness,safety_harness,fake_provider,contract}.py` 신규 / `tests/test_full_harness.py`·`test_rag_pipeline.py`·`test_rag_safety.py`·`test_local_only_mode.py` 신규 / 선택 `docs/eval/rag_eval_v1/questions.jsonl` 초안.

## 수정 금지 범위
`app/**` 전체. 기존 `tests/conftest.py` 4단계 격리 약화. 기존 `test_ai_*` 수정. DB 마이그레이션 / requirements.txt / `dosu_clinic.spec` / 응답 키.

## 반드시 지킬 안전 원칙
운영 DB 미접근. 외부 LLM/Embedding 호출 0. PII 원문 prompt 미도달. API key 로그 미노출. 응답 키 9개 보존. `local_only`에서 provider/embedding `call_count == 0`.

## 외부 API 호출 가능/불가능 여부
**불가능.** 모든 시나리오에서 0회. conftest가 `openai.OpenAI` / `anthropic.Anthropic`을 monkeypatch해서 호출 시 즉시 RuntimeError.

## FakeProvider / FakeEmbeddingProvider 필요 여부
**FakeProvider 재사용** — 현재 `tests/conftest.py:112` `class FakeProvider` 그대로 사용. **억지로 크게 바꾸지 않는다.**
- 호출 카운트: `len(provider.calls)` (현재 구현 기준, `self.calls: list`)
- 응답 결정: `__init__(return_text=...)` 또는 callable 주입 (기존 사용 패턴 유지)
- **추가 후보 (필요 시점에만 도입, 18-0 필수 아님)**:
  - `last_prompt` / `last_system` helper — 기존 `self.calls[-1]["prompt"]`/`["system"]`로 동일 정보 접근 가능. 가독성 helper만 옵션.
  - `responses_queue` — 다중 호출 케이스에서 응답을 순차로 다르게 주고 싶을 때만. 18-0에서는 단일 응답으로 충분.
  - `call_count` property — 추가 시 반드시 `len(.calls)`와 동일 값.
- **FakeEmbeddingProvider**는 18-5에서 신규 작성. 18-0에서는 stub만(호출되면 fail). `len(embedding_provider.calls)` 컨벤션 사전 합의.

> 위 추가 후보는 `docs/ai_rag_current_state.md` §14 18-0 전 선행 TODO §1·§2와 동일 항목.

## 반드시 실행할 테스트
```
run_check.bat
venv\Scripts\python.exe -m pytest tests/test_full_harness.py tests/test_rag_pipeline.py tests/test_rag_safety.py tests/test_local_only_mode.py tests/test_ai_manual_qa.py tests/test_ai_hallucination.py tests/test_ai_sms_draft.py tests/test_ai_action_leave.py -v
```

## 완료 조건
- [ ] `run_check.bat` 통과 (pytest + ruff + check_db_path)
- [ ] 기존 SMS AI / 휴무 AI / 매뉴얼 Q&A / hallucination / logging 테스트 100% 통과
- [ ] 신규 테스트 6~12개 통과
- [ ] FakeProvider/FakeEmbeddingProvider `call_count` 단언 동작
- [ ] `manual/{search,ask}` 응답 키 9개 그대로
- [ ] 5회 이내 통과
- [ ] `latest_test_report.md` / `latest_fix_summary.md` / `latest_codex_review_request.md` 작성

## Codex 검증 요청 문서에 꼭 적을 내용
신규 하네스 모듈 목록, conftest 4단계 격리 우회 없음 입증 방법, SDK monkeypatch가 lazy import 경로까지 막는지, 기존 18개 테스트 변경 0 diff, `manual/{search,ask}` 계약 단언 위치, 5회 루프 횟수, 다음 세션 진입 yes/no.

## 참조해야 할 상세 문서 목록
**공통 베이스 5개**(`AI_WORKING_RULES`, `ai_code_session_protocol`, `ai_docs_index`, `ai_rag_current_state`, 본 체크리스트)는 항상 먼저.
**18-0 추가 참조**: `docs/ai_harness_overview.md`, `docs/harnesses/full_harness_plan.md`, `docs/harnesses/rag_harness_plan.md`, `docs/harnesses/safety_harness_plan.md`, `docs/ai_rag_test_plan.md`, `docs/ai_rag_error_codes.md`, `docs/ai_codex_review_protocol.md` (세션 종료 시).
