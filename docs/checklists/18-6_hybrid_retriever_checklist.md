# 18-6 체크리스트 — Hybrid Retriever (α/β + cache)

> 이 문서는 해당 세션에서 반드시 확인해야 하는 실행 체크리스트다.
> 공통 규칙은 `docs/AI_WORKING_RULES.md`와 `docs/ai_code_session_protocol.md`를 먼저 확인한다.
> 상세 설계는 관련 ai_rag 문서를 참조한다.

**메타**: 목적=18-6 실행 가이드 · 시점=18-6 시작 시 · 독자=Claude Code/Codex/사용자 · 관련=`harnesses/hybrid_harness_plan.md`, `ai_rag_architecture_plan.md` §15, `ai_rag_quality_eval_plan.md` · 결정=keyword+vector 결합과 LLM 차단 게이트 · 비결정=라우터/UI 통합(18-7).

## 세션 목표
keyword + vector 결과를 정규화 가중 결합. **기본 OFF**(`AI_RAG_HYBRID_ENABLED=false`). final_score 낮으면 LLM 호출 차단. vector 실패 시 keyword 단독 fallback.

## 수정 가능 범위
`app/services/ai/rag/{retriever,reranker,confidence}.py` 확장 · `rag/cache.py` 신규(옵션) · `tests/harness/hybrid_harness.py` · 신규 테스트 (`test_hybrid_retriever`, `test_ai_assist_mode`) · (옵션) m014 — AiSetting α/β/flag 컬럼 · 관리자 UI 검색 모드 표시·토글 · `dosu_clinic.spec` hidden import.

## 수정 금지 범위
기존 m001~m013 수정 · requirements.txt · hybrid 기본 ON 출시 · vector 실패 시 검색 중단 · 응답 키 변경.

## 반드시 지킬 안전 원칙
α/β는 정규화된 점수에 적용(raw 직결합 금지) · dedup(chunk_id 기준) · hybrid OFF 시 keyword 단독 모드와 결과 동등(회귀 0) · `local_only`에서 vector/LLM 호출 0 · final_score 임계 미만 → LLM 호출 차단.

## 외부 API 호출 가능/불가능 여부
**테스트에서 불가능.** 운영에서는 게이트 통과 + flag ON일 때만 LLM 1회.

## FakeProvider / FakeEmbeddingProvider 필요 여부
**둘 다 필수.** `raise_on_call` 옵션으로 호출 금지 케이스 검증.

## 반드시 실행할 테스트
```
run_check.bat
venv\Scripts\python.exe -m pytest tests/test_hybrid_retriever.py tests/test_ai_assist_mode.py tests/test_local_first_mode.py tests/test_local_only_mode.py tests/test_full_harness.py -v
```
+ 머지 직전 eval 측정 (hybrid ON vs vector ON vs keyword-only)

## 완료 조건
- [ ] `run_check.bat` 통과 · 기존 모든 테스트 100% 통과
- [ ] hybrid OFF 시 keyword 단독 결과와 동등 (회귀 0)
- [ ] α/β 변경 시 순위 변화 결정적
- [ ] vector 실패 → keyword fallback 단언 통과
- [ ] dedup 누락 0
- [ ] final_score 낮음 → `len(provider.calls) == 0`
- [ ] `local_only` → vector/LLM 호출 0
- [ ] eval: hybrid ON ≥ vector-only/keyword-only, 환각/PII 0
- [ ] 5회 이내 통과 · `latest_*_report.md` 3종 작성

## Codex 검증 요청 문서에 꼭 적을 내용
점수 정규화 알고리즘, α/β 적용 위치, dedup 키 정의, hybrid OFF=keyword 동등 입증(eval), vector 실패 fallback 경로, `local_only`에서 vector 경로 시도 0 입증, final_score 임계와 confidence 모듈 일관성, eval 점수 표, 다음 세션(18-7) 진입 yes/no.

## 참조해야 할 상세 문서 목록
**공통 베이스 5개**(`AI_WORKING_RULES`, `ai_code_session_protocol`, `ai_docs_index`, `ai_rag_current_state`, 본 체크리스트).
**18-6 추가 참조**: `docs/ai_rag_architecture_plan.md` §15 · `docs/ai_rag_error_codes.md` (`vector_disabled`, `llm_skipped_low_confidence`) · `docs/ai_rag_quality_eval_plan.md` · `docs/harnesses/hybrid_harness_plan.md`.
