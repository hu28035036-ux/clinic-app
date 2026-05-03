# Vector Harness 설계 (vector_harness_plan)

> embedding 저장/검색/fallback/API key 없음/비용 방지 정책 검증.

---

## 1. Harness Name
`vector_harness`

## 2. 목적
임베딩 생성·저장·검색이 local-first 정책(불필요 호출 없음, key 없으면 disabled, local_only에서 0회)을 깨지 않으며 키워드 RAG로 안전하게 fallback되는지 검증한다.

## 3. 시작 구현 세션
- **18-5**

## 4. 테스트 대상 모듈
- `app/services/ai/vector/embeddings.py`
- `app/services/ai/vector/store.py`
- `app/services/ai/vector/similarity.py`
- `app/migrations/m013_knowledge_vectors.py`
- (간접) `app/services/ai/knowledge/indexer.py`

## 5. 입력 케이스
1. FakeEmbeddingProvider 주입 → embed_documents 정상
2. 실제 외부 embedding API monkeypatch → 호출 시도 자체 fail 검증
3. API key 없음 → vector_disabled 상태로 indexer 진행 (chunk만 생성)
4. `local_only` 모드 → embedding factory 차단 (`len(embedding_provider.calls) == 0`)
5. 동일 chunk 재인덱싱 (`content_hash` 동일) → embedding 재생성 없음
6. chunk content 변경 (hash 변경) → embedding 재생성 대상에 포함
7. query 길이 < 임계 → query embedding 생성 없음
8. embedding provider 호출 도중 예외 → keyword fallback + reason_code
9. dimension mismatch (저장된 dim != provider dim) → 안전 실패, 기존 벡터 보존
10. top_k vector search → 정해진 top_k 개수 반환
11. cosine similarity 계산 정확성 (단위 벡터·정규화)
12. vector 결과 source metadata 유지 (title/path/heading/chunk_index/score/search_mode)

## 6. 기대 출력
- `embed_documents([...]) -> list[list[float]]` 결정적 (FakeEmbeddingProvider)
- `embed_query(str) -> list[float]`
- `vector_store.upsert(chunk_id, provider, model, dim, embedding, content_hash)`
- `vector_store.search(query_vec, top_k) -> [(chunk_id, score), ...]`
- 모든 응답에 source metadata 보존

## 7. 외부 LLM 호출 허용 여부
❌ 금지

## 8. 외부 Embedding 호출 허용 여부
❌ 금지 (FakeEmbeddingProvider만)

## 9. Provider call count 기대값 (측정: `len(provider.calls)`)
모든 시나리오: 0 (vector 단위에서는 LLM 무관)

## 10. Embedding provider call count 기대값 (측정: `len(embedding_provider.calls)`)
- FakeEmbeddingProvider 정상 시드: 입력 청크 수만큼 (또는 same_hash skip 후 잔여 수)
- `local_only` 모드: 0
- API key 없음 환경: 0
- query 너무 짧음: 0 (해당 호출에서)
- content_hash 동일: 0 (해당 청크에서)

## 11. 사용할 Fake 객체
- `FakeEmbeddingProvider`:
  - 결정적 hash → 고정 차원 벡터
  - `call_count`, `last_inputs` 노출
  - `dimension` 설정 가능 (기본 16, 테스트용)
  - `raise_on_call=True` 옵션 (호출 차단 검증용)
- `FakeProvider` (호출되면 fail — vector_harness는 LLM 무관)

## 12. 운영 DB 사용 여부
❌ 금지

## 13. 사용해야 하는 테스트 DB 또는 fixture
- Full Harness `db_path` (격리)
- `tests/harness/vector_harness.py`:
  - `vector_store_fixture` (격리 DB + m013 적용)
  - `fake_embedding_provider(dimension=16)` factory
  - `chunks_fixture` (chunk_harness와 공유 또는 자체 생성)
  - `assert_no_embedding_call(provider)` 헬퍼

## 14. 반드시 검증할 reason_code
- `embedding_skipped_local_only`
- `embedding_skipped_same_hash`
- `embedding_skipped_short_query`
- `embedding_skipped_disabled`
- `embedding_skipped_api_key_missing`
- `provider_api_key_missing`
- `provider_error`
- `vector_disabled`

## 15. 반드시 검증할 로그 필드
- `AiUsageLog.embedding_called` (true/false)
- `AiUsageLog.skipped_embedding_reason`
- `AiUsageLog.embedding_tokens` (호출 시)
- `AiUsageLog.reason_code`
- `knowledge_index_runs.total_vectors`
- `knowledge_index_runs.failed_paths`
- 어떤 로그에도 embedding API key 부재

## 16. fallback 기대 동작
- API key 없음 → vector_disabled, chunk indexing은 성공 진행
- provider 오류 → 5분 circuit breaker (또는 즉시) + keyword 검색 사용
- dimension mismatch → 신규 model로 인식, 별도 row 생성 (UNIQUE에 model 포함)
- `local_only` → factory 인스턴스화 차단

## 17. 실패하면 막아야 하는 회귀
- 외부 embedding API 호출 누출 (cost 폭증)
- `local_only`에서 embedding 생성
- content_hash 같은데 재생성 (불필요 비용)
- vector 실패 시 검색 자체 중단 (keyword fallback 누락)
- vector 결과에 source metadata 손실
- m013 마이그레이션 idempotency 깨짐
- API key 로그 노출

## 18. 실행 명령 후보
- `venv\Scripts\python.exe -m pytest tests/test_vector_embeddings.py tests/test_vector_store.py -v`
- `venv\Scripts\python.exe -m pytest tests -k vector -v`

## 19. 완료 조건
- [ ] §5 모든 입력 케이스 통과
- [ ] §10 호출 카운트 단언 통과
- [ ] §14 모든 reason_code 발급 단언 통과
- [ ] §17 모든 회귀 0건
- [ ] m013 idempotent + rollback SQL 보관

## 20. Codex 검증 시 집중 확인 항목
- 실제 OpenAI/Anthropic embedding API 호출 경로가 정말 차단되는가 (monkeypatch 우회 없음)
- `local_only` 모드에서 embedding factory가 인스턴스 자체를 만들지 않는가
- content_hash 비교가 정확한 알고리즘으로 일관 적용되는가 (chunk_harness와 동일)
- vector 검색 실패 시 keyword fallback 경로가 항상 활성화되는가
- m013 스키마가 `chunk_id+provider+model` UNIQUE를 정확히 강제하는가
- circuit breaker가 일시 장애를 영구 disable로 만들지 않는가
