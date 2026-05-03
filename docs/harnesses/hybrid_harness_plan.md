# Hybrid Harness 설계 (hybrid_harness_plan)

> keyword + vector 검색 결과 결합과 낮은 신뢰도에서 LLM 호출 차단 검증.

---

## 1. Harness Name
`hybrid_harness`

## 2. 목적
keyword와 vector를 결합한 hybrid retriever가 결정적이며, 한쪽 실패 시 안전한 fallback이 동작하고, 결합 신뢰도가 낮을 때 LLM 호출을 차단하는지 검증한다.

## 3. 시작 구현 세션
- **18-6**

## 4. 테스트 대상 모듈
- `app/services/ai/rag/retriever.py` (hybrid 모드)
- `app/services/ai/rag/reranker.py`
- `app/services/ai/rag/confidence.py` (final_score)
- `app/services/ai/vector/similarity.py`
- (간접) `app/services/ai/rag/pipeline.py`

## 5. 입력 케이스
1. keyword와 vector 모두 hit → 결합 점수
2. keyword만 hit (vector 0건) → keyword 결과 사용
3. vector만 hit (keyword 0건) → vector 결과 사용 가능
4. 둘 다 같은 chunk hit → dedup
5. 둘 다 hit + 다른 chunk → top_k 정렬
6. 둘 다 낮은 점수 → low_confidence
7. final_score 임계 미만 → LLM 호출 차단
8. vector backend 오류 → keyword fallback (vector_disabled or provider_error)
9. `AI_RAG_HYBRID_ENABLED=false` → keyword 단독 모드 (기존 동작)
10. `local_only` 모드 → vector 호출 차단, keyword만
11. α/β 가중 변경 시 순위 변화 (결정적)

## 6. 기대 출력
- `retrieve(query, mode="hybrid", top_k=5) -> [Chunk + final_score]`
- final_score = α·norm(keyword_score) + β·norm(vector_score)
- dedup 후 top_k 반환
- vector 비활성 시 자동 α=1.0, β=0.0

## 7. 외부 LLM 호출 허용 여부
❌ 금지 (FakeProvider만)

## 8. 외부 Embedding 호출 허용 여부
❌ 금지 (FakeEmbeddingProvider만 — 실제 외부 API 호출 절대 금지)

## 9. Provider call count 기대값 (측정: `len(provider.calls)`)
- 둘 다 낮은 점수 / final_score 임계 미만: 0
- `local_only`: 0
- 게이트 통과 + `ai_assist`: 1
- `local_first` + 자연어 합성 의도: 1

## 10. Embedding provider call count 기대값 (측정: `len(embedding_provider.calls)`)
- query 처리당 1회 (vector path 활성 시)
- `local_only`: 0
- vector_disabled: 0
- query 너무 짧음: 0
- hybrid disabled: 0

## 11. 사용할 Fake 객체
- `FakeProvider`
- `FakeEmbeddingProvider`
- 둘 다 `raise_on_call` 옵션 사용해서 호출 금지 케이스 검증

## 12. 운영 DB 사용 여부
❌ 금지

## 13. 사용해야 하는 테스트 DB 또는 fixture
- Full Harness `db_path`
- vector_harness의 `vector_store_fixture` 재사용
- chunk_harness의 `markdown_samples` 재사용
- `tests/harness/hybrid_harness.py`:
  - `hybrid_retriever(alpha=0.6, beta=0.4)` factory
  - `assert_retriever_deterministic(query, retriever)` 헬퍼

## 14. 반드시 검증할 reason_code
- `vector_disabled`
- `llm_skipped_low_confidence`
- `llm_skipped_local_only`
- `provider_error`
- (추가) `llm_skipped_no_sources` — 양쪽 다 0건일 때

## 15. 반드시 검증할 로그 필드
- `AiUsageLog.search_mode` ∈ `{keyword, vector, hybrid}` (신규 — 18-6 시점 결정)
- `AiUsageLog.embedding_called`
- `AiUsageLog.llm_called`
- `AiUsageLog.reason_code`
- `AiUsageLog.local_answer_type` (Local Composer로 응답 시)
- 어떤 로그에도 API key/PII 부재

## 16. fallback 기대 동작
- vector 실패 → keyword 단독 결과로 계속 진행
- 둘 다 실패 → no_sources + 안전 안내
- final_score 낮음 → low_confidence → LLM 호출 차단 → Local Composer
- hybrid disabled → keyword 모드와 동일 (회귀 0)

## 17. 실패하면 막아야 하는 회귀
- vector 실패 시 검색 전체 중단
- α/β 가중이 변경되지 않았는데 순위가 매번 다름 (비결정성)
- dedup 누락으로 같은 chunk 중복
- hybrid 활성 시 keyword-only 모드 결과보다 회귀 (eval set 비교)
- `local_only`에서 embedding 호출 발생
- final_score 정규화 누락으로 한 쪽 점수가 다른 쪽 압도

## 18. 실행 명령 후보
- `venv\Scripts\python.exe -m pytest tests/test_hybrid_retriever.py -v`
- `venv\Scripts\python.exe -m pytest tests -k hybrid -v`

## 19. 완료 조건
- [ ] §5 모든 입력 케이스 통과
- [ ] §9, §10 호출 카운트 단언 통과
- [ ] §14 모든 reason_code 발급 단언 통과
- [ ] hybrid disabled 시 keyword 모드와 동일 결과 회귀 0
- [ ] eval set 점수: keyword-only 대비 동등 또는 향상

## 20. Codex 검증 시 집중 확인 항목
- α/β 결합이 정규화된 점수에 적용되는가 (raw score 직결합 금지)
- vector 실패 fallback 경로가 정말 keyword 결과만으로 동작하는가
- dedup 키가 chunk_id 기반 명시적인가
- `AI_RAG_HYBRID_ENABLED=false` 분기가 keyword 단독 모드와 동등한가 (회귀 0)
- `local_only`에서 retriever가 vector 경로를 시도조차 하지 않는가
- final_score 임계가 confidence 모듈과 일관 정의되는가
