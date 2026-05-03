# 18-5 Vector / Embedding 변경 요약

## 메타

- **세션 이름**: 18-5_vector_embedding
- **작성일**: 2026-05-02
- **루프 회차**: 1/5 (1회차에 통과)
- **기준 베이스라인**: 18-4 통과본 (313 passed)

## 목적

선행 세션 18-4 chunk 영속화 위에 **embedding 생성/저장/검색 기반**을 추가:
- `knowledge_vectors` 테이블 (m013) — chunk 별 vector 영속화
- `vector/embeddings.py` 추상 + `FakeEmbeddingProvider` (테스트 100%)
- `vector/store.py` upsert/find/list with content_hash skip + dim 안전 필터
- `vector/similarity.py` cosine + top_k 안정 정렬
- indexer optional 훅 (default=None → 18-4 회귀 0)
- reason_code 6개 정의 (응답 노출은 18-7 시점)

## 변경 파일 목록

### 신규 (10)

1. `app/migrations/m013_knowledge_vectors.py`
   - `knowledge_vectors` 인덱스 보강. 테이블은 ORM `create_all` 책임 — m012 패턴 100% 동일.
   - UNIQUE (chunk_id, provider, model) + content_hash idx + chunk_id idx.
   - `_table_exists` 가드로 단독 호출 안전.

2. `app/services/ai/vector/__init__.py`
   - 패키지 docstring + 의존 규칙 명시 (rag.pipeline / manual_qa 역의존 금지).

3. `app/services/ai/vector/embeddings.py` (~270줄)
   - `EmbeddingProvider` 추상 + `_UnavailableEmbeddingProvider` stub
   - `FakeEmbeddingProvider` (sha256 결정적, dim 인자, raise_on_call)
   - `EmbeddingUnavailable(kind=...)` 예외 + `VectorDimensionMismatch`
   - `get_embedding_provider` factory — local_only / disabled / api_key_missing /
     unknown_provider / sdk_missing 차단 우선순위
   - `is_embeddable_query` (QUERY_MIN_CHARS=2) — 짧은 query/invalid 차단
   - `safe_embed_documents` — 안전 호출 helper (예외 → fallback 신호)

4. `app/services/ai/vector/store.py` (~190줄)
   - `encode_embedding` / `decode_embedding` (JSON list[float])
   - `upsert_vector` — (chunk_id, provider, model) 키 + content_hash skip
   - `find_vector` / `get_vector_with_hash` (same_hash 판정용)
   - `list_vectors_for_query` — JOIN with KnowledgeChunk + dim 일치 필터
   - `delete_orphan_vectors` (admin tool 슬롯, indexer 호출 안 함)
   - `count_vectors` — 통계

5. `app/services/ai/vector/similarity.py` (~80줄)
   - `cosine_similarity` — 빈 벡터/0 벡터/dim mismatch 모두 0.0 안전 반환
   - `top_k` — sorted DESC + 안정 정렬 (Python sorted stable)
   - `is_zero_vector` helper

6. `tests/harness/vector_harness.py` (~150줄)
   - `make_fake_embedding_provider` factory
   - `assert_no_embedding_call` / `assert_embedding_calls` / `assert_no_external_calls_full`
   - `seed_chunks_for_vector_test` (chunker 호출 0)
   - `cosine_reference` (math.fsum reference 비교용)
   - `sha256_hex` (chunker.py:42 와 동일)
   - `cleanup_vector_tables` (fixture teardown)

7. `tests/test_ai_vector_harness.py` (~830줄, 36 tests)
   - 사용자 요구 21개 단언 매핑
   - Codex T-1/T-2 보강 4개
   - 추가 회귀 보호 9개 (encode/decode roundtrip, indexer no-delete AST 검사,
     reason_code 정의, vector_disabled_reason, etc.)

8. `docs/migrations_rollback/m013_rollback.sql`
   - 운영 자동 실행 금지. 인덱스 + 테이블 + schema_migrations row 정리 SQL.
   - knowledge_chunks 는 건드리지 않음 (m012 분담).

9. `reports/ai_dev_loop/18-5_test_report.md` (영구)
10. `reports/ai_dev_loop/18-5_fix_summary.md` (본 파일)

### 수정 (4)

> ⚠ **Codex 1회차 검토 후 dosu_clinic.spec 변경 revert** (2026-05-02).
> 사용자 본 세션 지시문의 "PyInstaller spec 수정 금지" 가 체크리스트 18-5 의
> "수정 가능 범위" 보다 우선 — 명시적 금지를 따름. spec 은 18-4 baseline 그대로.
> 실제 빌드 시점 (사용자 승인 후) 에 별도 세션에서 hidden import 추가 권고.

1. **`app/models/models.py`**
   - import 에 `LargeBinary` 추가 (1줄)
   - 하단에 `KnowledgeVector` ORM 클래스 append (~50줄)
     - `__tablename__="knowledge_vectors"`
     - `__table_args__` UNIQUE (chunk_id, provider, model)
     - 컬럼: `id, chunk_id (FK ON DELETE CASCADE), provider, model, dimension,
       embedding_json (Text), embedding_blob (LargeBinary 미사용 슬롯),
       content_hash, created_at, updated_at`
   - 기존 클래스 무수정.

2. **`app/services/ai/rag/schemas.py`**
   - reason_code 6개 추가:
     - `REASON_VECTOR_DISABLED`
     - `REASON_EMBEDDING_SKIPPED_LOCAL_ONLY`
     - `REASON_EMBEDDING_SKIPPED_SAME_HASH`
     - `REASON_EMBEDDING_SKIPPED_SHORT_QUERY`
     - `REASON_EMBEDDING_SKIPPED_DISABLED`
     - `REASON_EMBEDDING_SKIPPED_API_KEY_MISSING`
   - `ALL_REASON_CODES` 23 → **29** (6개 append)
   - `__all__` 동기화
   - docstring 카운트 23 → 29
   - 기존 23개는 무수정.

3. **`app/services/ai/knowledge/indexer.py`**
   - module docstring 갱신 (18-5 vector hook 정책 추가)
   - `ReindexResult` 에 8개 필드 append (모두 default=0/""):
     - `embedded_chunks`, `skipped_embeddings_same_hash`,
       `skipped_embeddings_no_provider`, `failed_embeddings`,
       `embedding_provider_name`, `embedding_model`, `embedding_dimension`,
       `vector_disabled_reason`
   - `reindex_all` 시그니처에 keyword-only optional 인자 2개 추가:
     - `embedding_provider=None` (default=None → 18-4 호출자 회귀 0)
     - `vector_disabled_reason=""` (factory 차단 사유 전달용)
   - `_reindex_locked` 본체에 step 5 (vector 단계) 추가:
     - `embedding_provider is None` 이면 통째로 skip → `vector_disabled_reason="no_provider"`
     - 호출 시 try/except → 실패 시 `failed_embeddings += N` + `vector_disabled_reason="provider_error"` + reindex status 영향 0 (keyword fallback 정책)
   - `_embed_chunks_into_vectors` 신규 함수 (~80줄)
     - 모든 chunk 수집 → `get_vector_with_hash` 로 same_hash skip 판정
     - 대상 chunk 만 1회 batch `embed_documents`
     - `upsert_vector` per chunk → `embedded_chunks` ++
     - lazy import로 vector 패키지 부재 환경에서도 module load 가능
   - 18-4 무수정 함수: `_index_one_document`, `_chunk_to_orm`, `_apply_chunk_to_orm`, `_short_error`, `_safe_json`, `_utc_iso`, `_finalize_run`, `_final_status`.

4. **`tests/test_ai_manual_rag_harness.py`** (1개 테스트 갱신)
   - `test_schemas_reason_codes_23_defined` → `test_schemas_reason_codes_29_defined`
   - 18-5 reason_code 6개 추가에 따른 카운트 갱신 + 6개 정의 단언 보강.
   - **다른 18-2 테스트는 무수정** — 단순 카운트 동기화.

## 무수정 (회귀 보호 명시)

- `app/services/ai/manual_qa.py` — wrapper 그대로
- `app/services/ai/rag/{__init__,pipeline,retriever,prompts,safety}.py`
- `app/services/ai/{provider,pii,sms_draft,action_leave,date_resolver,...}.py`
- `app/routers/ai.py` — 응답 9키 후방호환 강제 유지
- `app/migrations/m001~m012.py` — 기존 마이그레이션 무수정
- `app/services/ai/knowledge/{loader,normalizer,chunker,keyword_index}.py`
- `tests/conftest.py` — 격리/SDK 차단/AI fixture 그대로
- `tests/harness/{db_guard,seed_data,helpers,fake_provider,rag_harness,reindex_harness,chunk_harness,safety_harness,contract}.py` — 18-0~18-4 helper 그대로
- `pyproject.toml` — per-file-ignores 무수정
- `requirements.txt` — 무수정 (외부 vector lib 미도입)
- `dosu_clinic.spec` — **18-4 baseline 그대로** (Codex M-1 지적 후 revert,
  사용자 본 세션 "PyInstaller spec 수정 금지" 우선). m013 마이그레이션은 glob
  자동 등록 (line 95) 으로 자동 hidden import. vector 패키지 명시 추가는 18-7
  배포 직전 별도 세션 권고.

## 의도/이유 요약 (변경 파일별)

| 파일 | 의도 | 이유 |
|---|---|---|
| m013 | 인덱스 멱등 보강 | m012 와 동일 패턴 — ORM create_all + 마이그레이션 인덱스 보강 |
| KnowledgeVector ORM | vector 영속화 | 사용자 요구 #3/#4/#5 (테이블 생성/저장/조회) + UNIQUE 제약으로 #5 (재생성 방지) |
| LargeBinary import | embedding_blob 슬롯 | 미래 dim>64 BLOB 확장 대비 (현재 nullable 미사용) |
| reason_code 6개 | 응답/로그 표준화 | docs/ai_rag_error_codes.md §1-8/§3 정의 — 18-7 m014 시점에 AiUsageLog 컬럼 도입 |
| vector/embeddings.py factory | local_only/disabled 차단 | 사용자 요구 #4/#9, T-1b 보강 — 인스턴스화 자체 차단 |
| FakeEmbeddingProvider | 외부 호출 0 | 사용자 요구 #1/#2 — 결정적 sha256 + raise_on_call 옵션 |
| vector/store.py upsert + same_hash skip | 재생성 방지 | 사용자 요구 #5/#6 |
| vector/store.py list dim 필터 | 안전 실패 | 사용자 요구 #13 — query dim 안 맞는 row 자동 제외 |
| vector/similarity.py 0.0 fallback | 안전 fallback | 사용자 요구 #13/#14 — raise 금지 |
| indexer 훅 (default=None) | 18-4 회귀 0 | 호출자 무수정 보장 |
| indexer try/except → status 영향 0 | keyword fallback | 사용자 요구 #12 — 전체 AI 죽지 않음 |
| spec hidden import | PyInstaller 빌드 | 신규 모듈 + 누락 재발 방지 |
| m013_rollback.sql | 운영 안전 롤백 | m012 와 동일 패턴 — 자동 실행 X |
| reason_code count 23→29 | schemas 갱신 정합 | 18-2 테스트가 카운트 단언 — 카운트 동기화만 |

## 외부 호출 0 입증

`vector/` 패키지 소스에 다음이 부재함:
```
import openai
from openai
import anthropic
from anthropic
```
test_2_no_external_embedding_call 이 inspect.getsource() 로 직접 검증.

`get_embedding_provider` factory 가 `provider in ("openai", "anthropic")` 분기에서 즉시 `EmbeddingUnavailable(kind="sdk_missing")` raise — 실제 SDK 호출 코드 경로 부재.

`tests/conftest.py:_block_sdk_modules` 가 import 된 openai/anthropic SDK 클래스를 raise stub 으로 교체 — 실수 호출 시 즉시 실패.

## API key 보호 입증

- `EmbeddingUnavailable.message` 는 kind 식별자만 노출. `api_key` 값 비노출.
- `_short_error()` 가 vector 단계 예외 메시지를 400자 컷.
- `vector_disabled_reason` 은 fixed enum-like 문자열만 (비밀값 미포함).
- 모든 로그 출력에 `api_key` 변수 references 0건.

## 후방호환

- v1.3.3 manual/ask 응답 9키 + manual/search 3키 변경 0.
- `manual_qa.ask_manual_question(provider_override=)` 시그니처 무수정.
- `pii.scan` / `AiSetting`/`AiUsageLog` 컬럼 무수정.
- `pyproject.toml` per-file-ignores 무수정.

## 다음 세션 권고

- 18-6 hybrid retriever — `retriever.retrieve(mode="hybrid")` 구현 + α/β 가중. 본 세션의 vector store 를 read 전용으로 사용.
- 18-7 admin/router — `AiUsageLog` m014 컬럼 추가 (`embedding_called`, `skipped_embedding_reason`, `reason_code`, `provider`, `model`, `dimension`, `content_hash`, `vector_disabled` 등) + 라우터에서 reason_code 응답 노출.
- 외부 OpenAIEmbeddingProvider 실제 SDK 연동도 18-7 권한.
