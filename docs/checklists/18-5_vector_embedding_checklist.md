# 18-5 체크리스트 — Vector Store / Embedding (m013)

> 이 문서는 해당 세션에서 반드시 확인해야 하는 실행 체크리스트다.
> 공통 규칙은 `docs/AI_WORKING_RULES.md`와 `docs/ai_code_session_protocol.md`를 먼저 확인한다.
> 상세 설계는 관련 ai_rag 문서를 참조한다.

**메타**: 목적=18-5 실행 가이드 · 시점=18-5 시작 시 · 독자=Claude Code/Codex/사용자 · 관련=`harnesses/vector_harness_plan.md`, `ai_rag_migration_plan.md`, `ai_rag_quality_eval_plan.md` · 결정=embedding 추상/저장/검색·기본 OFF · 비결정=hybrid 결합(18-6).

## 세션 목표
임베딩 생성·저장·검색 도입. **기본 OFF**. 관리자 활성화 + API key 있을 때만 동작. 모든 단위 테스트는 FakeEmbeddingProvider만. SQLite 기반 (외부 vector DB 미도입 — ADR-006).

## 수정 가능 범위
`app/migrations/m013_knowledge_vectors.py` · `app/services/ai/vector/{embeddings,store,similarity}.py` · `knowledge/indexer.py` 확장(vector 단계, 부분 실패) · AiSetting flag 컬럼(필요 시 m014) · `tests/harness/vector_harness.py` · 신규 테스트 · `dosu_clinic.spec` hidden import · (옵션) requirements.txt · `docs/migrations_rollback/m013_rollback.sql`.

## 수정 금지 범위
기존 m001~m012 수정 · vector 기본 ON 출시 · `local_only`에서 embedding 호출 · 응답 키 변경 · 외부 vector DB(faiss/chromadb) 도입.

## 반드시 지킬 안전 원칙
실제 외부 embedding API 호출 0(테스트 100%) · `local_only`에서 factory 인스턴스 차단 · API key 없음 → vector_disabled, chunk indexing은 성공 · content_hash 동일 → 재생성 skip · vector 실패 → keyword fallback · API key/embedding key 로그 미노출.

## 외부 API 호출 가능/불가능 여부
**테스트에서 불가능.** 운영에서는 관리자 활성화 + key 있을 때만. monkeypatch로 실제 호출 차단.

## FakeProvider / FakeEmbeddingProvider 필요 여부
**FakeEmbeddingProvider 필수**(결정적 hash, dimension 설정, raise_on_call 옵션). FakeProvider는 호출되면 fail (vector_harness는 LLM 무관).

## 반드시 실행할 테스트
```
run_check.bat
venv\Scripts\python.exe -m pytest tests/test_vector_embeddings.py tests/test_vector_store.py tests/test_local_only_mode.py tests/test_ai_reindex.py tests/test_full_harness.py -v
```
+ 머지 직전 eval 측정 (`docs/ai_rag_quality_eval_plan.md` §4 Phase C — vector ON vs OFF)

## 완료 조건
- [ ] `run_check.bat` 통과 · 기존 모든 테스트 100% 통과
- [ ] m013 idempotent · rollback SQL 보관
- [ ] FakeEmbeddingProvider만 사용, 실제 외부 호출 0
- [ ] `local_only` `len(embedding_provider.calls) == 0`
- [ ] API key 없음 → vector_disabled, chunk indexing 성공
- [ ] content_hash 동일 → embedding skip
- [ ] vector 실패 → keyword fallback 단언 통과
- [ ] eval: vector ON ≥ keyword-only, 환각/PII 노출 0
- [ ] 5회 이내 통과 · `latest_*_report.md` 3종 작성

## Codex 검증 요청 문서에 꼭 적을 내용
m013 스키마/idempotent 입증, m001~m012 diff 0, FakeEmbeddingProvider만 사용 입증(grep), `local_only` factory 차단 입증, content_hash 비교 알고리즘 (chunk_harness와 동일), vector_disabled fallback 경로, API key/embedding key 로그 부재, eval 점수 표(vector ON/OFF), 다음 세션(18-6) 진입 yes/no.

## 참조해야 할 상세 문서 목록
**공통 베이스 5개**(`AI_WORKING_RULES`, `ai_code_session_protocol`, `ai_docs_index`, `ai_rag_current_state`, 본 체크리스트).
**18-5 추가 참조**: `docs/ai_rag_architecture_plan.md` §3-17~3-19 §11 · `docs/ai_rag_migration_plan.md` §3 §7 §8 · `docs/ai_rag_error_codes.md` (`embedding_skipped_*`, `vector_disabled`) · `docs/ai_rag_quality_eval_plan.md` · `docs/harnesses/vector_harness_plan.md`.
