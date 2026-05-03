# 18-2 체크리스트 — 기존 keyword RAG 구조 분리

> 이 문서는 해당 세션에서 반드시 확인해야 하는 실행 체크리스트다.
> 공통 규칙은 `docs/AI_WORKING_RULES.md`와 `docs/ai_code_session_protocol.md`를 먼저 확인한다.
> 상세 설계는 관련 ai_rag 문서를 참조한다.

**메타**: 목적=18-2 실행 가이드 · 시점=18-2 시작 시 · 독자=Claude Code/Codex/사용자 · 관련=`ai_rag_architecture_plan.md`, `ai_rag_migration_plan.md`, `ai_rag_quality_eval_plan.md`, `harnesses/rag_harness_plan.md` · 결정=분리 모듈 경계와 wrapper 유지 · 비결정=chunker/vector(18-3 이후).

## 세션 목표
현행 `app/services/rag/search.py` + `manual_qa.ask_manual_question`을 `app/services/ai/rag/{retriever,confidence,answer_composer,answer_validator,pipeline}.py` + `knowledge/{keyword_index,synonyms}.py`로 분리한다. **외형 동작 v1.3.3과 100% 동일**.

## 수정 가능 범위
신규 RAG/Knowledge 모듈 (위) · `manual_qa.py` wrapper로 축소(시그니처 유지) · `app/services/rag/search.py` shim 유지 · 신규 테스트 (`test_rag_pipeline`/`test_rag_answer_validator`/`test_local_first_mode`).

## 수정 금지 범위
라우터(`app/routers/ai.py`) · 응답 키 · DB 마이그레이션 · requirements.txt · 외부 의존성 · `manual_qa.ask_manual_question` 시그니처 · `LOW_SCORE_THRESHOLD=2`.

## 반드시 지킬 안전 원칙
응답 9개 키 보존 · `_NOT_FOUND_*`/`_BLOCKED_ANSWER` 문구 보존 · `category="manuals"` 단일 검색 정책 · PII 마스킹/할루시네이션 가드 위치 보존 · 운영 DB 미접근.

## 외부 API 호출 가능/불가능 여부
**기본 불가능.** 게이트 통과 시(테스트는 FakeProvider) 1회 허용. 실제 외부 SDK 호출은 0.

## FakeProvider / FakeEmbeddingProvider 필요 여부
**FakeProvider 필수.** FakeEmbeddingProvider는 호출되면 fail (vector 미사용).

## 반드시 실행할 테스트
```
run_check.bat
venv\Scripts\python.exe -m pytest tests/test_rag_pipeline.py tests/test_rag_answer_validator.py tests/test_rag_safety.py tests/test_ai_manual_qa.py tests/test_ai_hallucination.py tests/test_local_first_mode.py tests/test_local_only_mode.py -v
```
+ 머지 직전 baseline eval 측정 (`docs/ai_rag_quality_eval_plan.md` §4 Phase B)

## 완료 조건
- [ ] `run_check.bat` 통과
- [ ] 기존 매뉴얼/SMS/휴무 AI 테스트 100% 통과
- [ ] `manual/{search,ask}` 응답 9개 키 그대로 + reason_code 정확히 1개 발급
- [ ] provider call count 모드별 단언 통과 (`len(provider.calls)`)
- [ ] eval baseline 회귀 0
- [ ] 5회 이내 통과
- [ ] `latest_*_report.md` 3종 작성

## Codex 검증 요청 문서에 꼭 적을 내용
분리된 모듈/책임 매핑, `manual_qa` wrapper diff, 응답 키 회귀 0 입증, FakeProvider가 받는 prompt가 v1.3.3과 동등, eval baseline 점수 표, `_NOT_FOUND_*`/`_BLOCKED_ANSWER` 문구 보존 위치, 다음 세션(18-3) 진입 yes/no.

## 참조해야 할 상세 문서 목록
**공통 베이스 5개**(`AI_WORKING_RULES`, `ai_code_session_protocol`, `ai_docs_index`, `ai_rag_current_state`, 본 체크리스트).
**18-2 추가 참조**: `docs/ai_rag_architecture_plan.md` · `docs/ai_rag_migration_plan.md` · `docs/ai_rag_quality_eval_plan.md` · `docs/ai_rag_error_codes.md` · `docs/harnesses/rag_harness_plan.md`.
