# AI/RAG 아키텍처 설계 (ai_rag_architecture_plan)

> 최종 RAG / Knowledge / Vector / Local-first AI 구조의 목표 그림.
> 본 문서는 **무엇을 만들 것인가**를 정의한다. 절차/순서는 `ai_rag_rollout_plan.md`,
> DB/스키마 변경은 `ai_rag_migration_plan.md`, 에러 코드는 `ai_rag_error_codes.md`,
> 테스트 매트릭스는 `ai_rag_test_plan.md`를 참조.

---

## 0. Local-first 핵심 문장

> 이 프로젝트의 AI는 외부 LLM API를 기본 엔진으로 쓰는 구조가 아니라,
> 내부 데이터와 규칙을 우선 사용하는 local-first AI assistant로 설계한다.
> 외부 API는 근거가 충분하고 문장 생성이 꼭 필요한 경우에만 선택적으로 호출한다.

---

## 1. 현재 구조 요약 (`ai_rag_current_state.md`에서 발췌)

- AI 서비스: `app/services/ai/` (provider 추상, openai/anthropic 클라이언트, manual_qa, sms_draft, action_leave, pii, ai_logging 등)
- RAG: `app/services/rag/search.py` — 토큰 기반 키워드 검색만. 벡터 DB·임베딩 미사용.
- 라우터: `app/routers/ai.py`. `/api/ai/manual/{search,ask}`는 v1.3.3 응답 스키마 후방호환 보호 대상.
- `manual_qa.ask_manual_question(provider_override=)`가 라우터 / 테스트의 단일 진입점.

---

## 2. 최종 목표 폴더 구조

```
app/
  services/
    ai/
      rag/
        __init__.py
        schemas.py            # 공용 dataclass/typed dict (Document, Chunk, Source, Answer, Confidence)
        safety.py             # Safety 검사 (PII 사전 차단, 위험 질문, 너무 짧은 질문)
        prompts.py            # RAG 답변용 프롬프트 + 버전 관리
        query_normalizer.py   # 한국어 정규화, 공백/유니코드 정제
        query_parser.py       # 질문에서 의도/엔티티 추출
        intent_router.py      # rule_based / db_query / keyword_search / chunk_search / llm 분기
        retriever.py          # keyword + (옵션)vector 통합 검색
        reranker.py           # BM25 가중/heading boost/메타 필터
        confidence.py         # top_score, source 다양성 기반 confidence 계산
        answer_composer.py    # Local Answer Composer (LLM 없이 답변 조립)
        answer_validator.py   # 위험 표현/실행 오인/PII/출처 일관성 검증
        source_builder.py     # UI용 출처 표시 데이터 빌드
        cache.py              # 질문/검색결과 캐시 (TTL)
        pipeline.py           # 전체 RAG 파이프라인 진입점
      knowledge/
        __init__.py
        loader.py             # knowledge/*.md 로딩
        normalizer.py         # 마크다운 정규화 (heading 추출, 코드블록 분리)
        chunker.py            # heading 기반 청커 (결정적, content_hash 기반 중복 방지)
        synonyms.py           # 한국어 동의어 사전 (휴무/연차/월차 등)
        keyword_index.py      # keyword/chunk-keyword inverted index
        indexer.py            # 인덱스 빌드/갱신/reindex 진입점
      vector/
        __init__.py
        embeddings.py         # EmbeddingProvider 추상 + 팩토리 (FakeEmbeddingProvider 포함)
        store.py              # knowledge_vectors 저장소 wrapper
        similarity.py         # cosine/dot 유사도, top-k 추출
      manual_qa.py            # 기존 wrapper — 신규 pipeline.run_manual_qa() 호출로 교체 (인터페이스 유지)
      health.py               # AI/RAG 상태 헬스 (chunk count, vector count, last reindex)
      ai_logging.py           # (현행 유지·확장)
      provider.py             # (현행 유지·확장: AiProvider, get_provider)
      openai_client.py        # (현행 유지)
      anthropic_client.py     # (현행 유지)
      sms_draft.py            # (현행 유지)
      action_leave.py         # (현행 유지)
      date_resolver.py        # (현행 유지)
      pii.py                  # (현행 유지)
      prompts.py              # (현행 유지 — sms/action용)
      validators.py           # (현행 유지)
```

`app/services/rag/` (현행)는 단계별 분리 후 `app/services/ai/rag/`로 흡수, 또는 `rag.search`만 후방호환 shim으로 유지. 방식은 `ai_rag_migration_plan.md`에서 결정.

---

## 3. 각 파일 책임 / RAG 구성요소 상세

각 구성요소에 대해 동일 포맷으로 정리:
**입력 / 출력 / 외부 API 사용 / local_only 동작 / 테스트 / 관련 하네스 / 구현 시점**

### 3-1. Document Loader (`knowledge/loader.py`)
- 입력: `knowledge/manuals/`, `knowledge/sms_guides/` 폴더 경로
- 출력: `Document(path, category, raw_text, mtime, content_hash)` 리스트
- 외부 API: 없음
- local_only: 정상 동작
- 테스트: 마크다운 누락/잘못된 인코딩/빈 파일 케이스
- 하네스: chunk_harness (간접)
- 구현: 18-3

### 3-2. Document Normalizer (`knowledge/normalizer.py`)
- 입력: `Document.raw_text`
- 출력: 헤딩 트리, 코드블록 마스킹된 본문
- 외부 API: 없음
- local_only: 정상 동작
- 테스트: heading 깊이/번호 매기기/코드블록 보호
- 하네스: chunk_harness
- 구현: 18-3

### 3-3. Metadata schema (`rag/schemas.py`)
- 정의:
  - `Document(path, category, content_hash, ...)`
  - `Chunk(id, doc_id, source_path, title, heading, section_path, chunk_index, content, content_hash, token_count, tags, category, document_version)`
  - `Source(title, path, snippet)` — UI 후방호환 키와 1:1
  - `Answer(text, sources, confidence, not_found, blocked, blocked_reason, guard_hits, top_score, masked_question, reason_code, llm_called, embedding_called, ai_mode, prompt_version)`
- 외부 API: 없음
- local_only: 영향 없음
- 구현: 18-1

### 3-4. Keyword Index (`knowledge/keyword_index.py`)
- 입력: `Chunk` 리스트
- 출력: inverted index (token → chunk_id, score)
- 외부 API: 없음
- local_only: 정상 동작
- 테스트: 동일 입력 → 동일 인덱스(결정성), 한국어 형태소 처리
- 하네스: rag_harness, chunk_harness
- 구현: 18-2 (기존 search.py 분리), 18-4 (chunk 단위로 갱신)

### 3-5. Synonym dictionary (`knowledge/synonyms.py`)
- 한국어 도메인 동의어: 휴무↔연차↔월차, 예약↔스케줄, 문자↔SMS, 도수↔도수치료 등
- 외부 API: 없음
- local_only: 정상 동작
- 구현: 18-2

### 3-6. Query Normalizer (`rag/query_normalizer.py`)
- NFC 정규화, 공백 정제, 한자/영문 케이스, 자모 분리 처리
- 외부 API: 없음
- 구현: 18-1

### 3-7. Query Parser (`rag/query_parser.py`)
- 의도/엔티티 추출 (날짜, 치료사명, 휴무유형 등 — `date_resolver` 재사용)
- 외부 API: 없음
- 구현: 18-1

### 3-8. Intent Router (`rag/intent_router.py`)
- 분기 결정: `safety_block` / `rule_based` / `db_query` / `keyword_search` / `chunk_search` / `vector_search` / `llm_compose`
- 외부 API: 없음 (분기만)
- local_only: vector_search/llm_compose 분기 자동 차단
- 구현: 18-1

### 3-9. Retriever (`rag/retriever.py`)
- 키워드 + (옵션) 벡터 hybrid 검색
- 출력: `list[Chunk]` + 점수
- 외부 API: vector 호출 시에만 (옵션)
- local_only: keyword만 사용
- 하네스: rag_harness, vector_harness, hybrid (rag_harness 확장)
- 구현: 18-2 → 18-5 → 18-6

### 3-10. Reranker (`rag/reranker.py`)
- BM25 가중치, heading boost, 카테고리 필터
- 외부 API: 없음
- 구현: 18-4 이후 선택

### 3-11. Confidence Evaluator (`rag/confidence.py`)
- 입력: top_score, source 다양성, query 길이
- 출력: `"high"|"low"|"unknown"` (현행 manual_qa의 `_confidence_for` 일반화)
- 외부 API: 없음
- 구현: 18-2 (현행 로직 추출)

### 3-12. Local Answer Composer (`rag/answer_composer.py`)
- **핵심**: LLM 없이 답변을 조립한다.
- 모드:
  - `db_answer` — 내부 DB 조회 결과를 정해진 포맷으로 표시
  - `keyword_passage` — 검색 결과 문단을 요약 없이 그대로 안내 + 출처
  - `template` — 휴무/예약 명령 응답용 고정 템플릿
  - `rule_based` — 날짜 파싱 등 규칙 기반 응답
  - `safety_block` / `status_query`
- 외부 API: 없음
- local_only: 정상 동작 (주력 경로)
- 구현: 18-2 → 18-4

### 3-13. Source/Citation Builder (`rag/source_builder.py`)
- UI 노출용 `[{title, path, snippet}, ...]` 빌드 — **현행 `_format_sources` 후방호환 키 유지**
- 외부 API: 없음
- 구현: 18-1

### 3-14. Answer Validator (`rag/answer_validator.py`)
- 현행 `manual_qa.validate_answer`를 추출/일반화
- PII 마스킹, 의료 단정, 실행 오인, 출처 없는 단정 차단
- 외부 API: 없음
- 구현: 18-2

### 3-15. Cache (`rag/cache.py`)
- key = (mode, normalized_query, prompt_version, chunk_index_version, vector_index_version)
- TTL 짧게 (기본 60s, 운영 결정 필요)
- 외부 API: 없음
- 구현: 18-4 이후 선택

### 3-16. Pipeline (`rag/pipeline.py`)
- 전체 진입점:
  ```
  safety → query_normalize → parse → intent_router →
   (rule|db|keyword|chunk|vector|hybrid) → rerank → confidence →
   answer_composer (or LLM gate) → answer_validator → source_builder
  ```
- 라우터 / `manual_qa.py` wrapper에서 호출
- 외부 API: 게이트 통과 시에만
- 구현: 18-2 (최소) → 18-4 → 18-6

### 3-17. Embedding Provider (`vector/embeddings.py`)
- 추상 인터페이스:
  ```python
  class EmbeddingProvider:
      name: str
      dimension: int
      def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
      def embed_query(self, text: str) -> list[float]: ...
  ```
- 구현체: `OpenAIEmbeddingProvider`, `LocalEmbeddingProvider(미정)`, `FakeEmbeddingProvider`(테스트)
- `local_only` 모드 시 인스턴스 생성 자체 금지 (factory에서 차단)
- 구현: 18-5

### 3-18. Vector Store (`vector/store.py`)
- `knowledge_vectors` 테이블(스키마는 migration_plan)
- read/write/upsert/by-content-hash
- 외부 API: 없음 (DB만)
- 구현: 18-5

### 3-19. Similarity (`vector/similarity.py`)
- cosine/dot 유사도, top-k
- 외부 API: 없음
- 구현: 18-5

### 3-20. Evaluation Dataset / Observability
- `docs/ai_rag_quality_eval_plan.md`로 위임

---

## 4. 데이터 흐름

### 4-1. 인덱싱 파이프라인
```
knowledge/*.md
  → loader → normalizer → chunker
  → keyword_index (항상)
  → embeddings (옵션, vector_enabled 시) → vector_store
```

- `content_hash` 동일 → 청크/임베딩 재생성 금지
- 부분 실패 → 실패 문서만 표시. 기존 인덱스 유지

### 4-2. 질의 파이프라인 (local-first)
```
question
 → safety
 → query_normalizer + query_parser
 → intent_router
   ├─ safety_block       → answer_composer(safety_block)
   ├─ rule_based         → answer_composer(rule_based)
   ├─ db_query           → answer_composer(db_answer)
   ├─ keyword/chunk      → retriever → reranker → confidence
   │                      └─ answer_composer(keyword_passage)
   └─ vector/hybrid (optional) → retriever(vector) → ...
 → (옵션) LLM Gate
   - sources >= 1, confidence != unknown, no PII, mode in {local_first|ai_assist}, ext_llm_allowed
   - 통과 시: prompt_builder → provider.generate → answer_validator
   - 차단 시: answer_composer(local) 결과를 그대로 반환
 → source_builder
 → 응답 (current_state §3 응답 키 그대로 + reason_code 추가)
```

---

## 5. API 흐름 (후방호환)

- `/api/ai/manual/search` — 신 `pipeline.run_manual_search(question)` 호출. 응답 키 동일.
- `/api/ai/manual/ask` — 신 `pipeline.run_manual_qa(db, question, provider, embedding_provider, mode)` 호출. 기존 9개 키 유지 + 추가 키:
  - `reason_code` (string, optional) — `ai_rag_error_codes.md`에서 정의
  - `llm_called` (bool, optional)
  - `embedding_called` (bool, optional)
  - `ai_mode` (string, optional)
  - `prompt_version` (string, optional)
- 추가 키는 모두 **optional**. 프론트가 모르면 무시 가능.

### 5-1. `manual_qa.py` wrapper 유지 계획
- `manual_qa.ask_manual_question(db, question, *, provider_override=None)` 시그니처 유지.
- 내부에서 `pipeline.run_manual_qa(...)` 호출 + provider/embedding 결정.
- 테스트에서 FakeProvider 주입 경로 그대로.

---

## 6. 기존 SMS AI / 휴무 AI와의 충돌 회피

- SMS AI(`sms_draft`), 휴무 AI(`action_leave`)는 RAG pipeline을 거치지 않음 — 별도 진입점 유지.
- 공유 모듈(`provider`, `pii`, `ai_logging`, `prompts`, `validators`, `date_resolver`)은 인터페이스 보존 변경.
- 신규 모듈은 모두 `app/services/ai/{rag,knowledge,vector}/`에 격리. 기존 import 경로 변경 없음.

---

## 7. LLM Provider 인터페이스 (현행 유지)

- `AiProvider.generate(prompt: str, system: str = "") -> AiResult`
- `AiResult(text, prompt_tokens, completion_tokens, raw)`
- 예외: `AiUnavailable(kind, message)`, `AiPiiBlocked(fields)`
- FakeProvider (테스트):
  - 동일 시그니처
  - provider call count 측정: `len(provider.calls)` (현재 `tests/conftest.py:122` `self.calls: list`). 향후 `call_count` property 추가 시에도 동일 값 반환.
  - 미리 주입한 응답 큐 반환

---

## 8. Embedding Provider 인터페이스

- `EmbeddingProvider.embed_documents(list[str]) -> list[list[float]]`
- `EmbeddingProvider.embed_query(str) -> list[float]`
- `dimension: int`, `name: str`
- FakeEmbeddingProvider:
  - 결정적 hash 기반 임베딩 (테스트 reproducibility)
  - `call_count` 노출
  - `local_only` 모드에서는 factory가 인스턴스 생성 자체를 차단 (호출 없음)

---

## 9. AI 모드 (mode)

| 모드 | 의미 | 외부 LLM | 외부 Embedding | API key 없으면 |
|---|---|---|---|---|
| `local_only` | 외부 호출 0회 | ❌ | ❌ | 정상 동작 |
| `local_first` (기본) | 내부 처리 우선, 필요시 외부 | 조건부 ✅ | 조건부 ✅ | 외부 기능만 비활성, 내부 정상 |
| `ai_assist` | 내부 결과 충분 시 LLM 보조 | 조건부 ✅ | 조건부 ✅ | 외부 기능만 비활성 |

- provider call count 단언 (`len(provider.calls)`):
  - `local_only`: 항상 0
  - `local_first`: sources 부족/PII/저신뢰 시 0
  - `ai_assist`: sources 부족 시 0
- embedding provider call count 단언 (`len(embedding_provider.calls)`): 동일 원칙

---

## 10. LLM 호출 조건 (게이트)

모두 만족해야 외부 LLM 호출 허용:
1. `mode in {local_first, ai_assist}`
2. `AI_EXTERNAL_LLM_ENABLED == True`
3. `AiSetting.enabled == True` 및 `api_key`/`model` 채워짐
4. `sources` >= 1 (RAG 결과 존재)
5. `confidence != "unknown"` (top_score >= 임계치)
6. PII 위험 없음
7. 사용자 의도가 "문장 다듬기/요약/자연어 생성" 필요
8. `local_only` 플래그 OFF

게이트 차단 시 `reason_code` 발급 + Local Answer Composer 결과 반환.

---

## 11. Embedding 호출 조건

모두 만족해야 호출:
1. `mode in {local_first, ai_assist}` 및 `local_only == False`
2. `AI_EXTERNAL_EMBEDDING_ENABLED == True`
3. document: `content_hash` 변경 (또는 신규)
4. query: invalid_query/너무 짧음/keyword로 충분 아님
5. embedding provider api_key 설정됨
6. 직전 호출이 timeout/오류로 disable되지 않음

차단 시 `reason_code` 발급, keyword fallback.

---

## 12. Fallback 정책

- vector 검색 실패 → keyword 검색
- LLM 호출 실패 → Local Answer Composer 결과
- chunk 인덱스 손상 → 마지막 정상 인덱스 유지 (reindex 실패 시 기존 보존)
- 모든 실패 → "정보 부족" 응답 (할루시네이션 금지)

---

## 13. 할루시네이션 금지 정책

- 출처 없는 단정 → `answer_validator`에서 차단
- 의료 단정/실행 완료 오인 → 차단 (`_RE_MEDICAL_CLAIM`, `_RE_EXECUTION_CLAIM`)
- LLM 응답에서 만들어낸 기능명/버튼명/API endpoint → 시스템 프롬프트로 명시 금지
- 차단 시 `blocked: true`, `blocked_reason`, 안내 문구로 대체

---

## 14. 개인정보 보호 정책

- 입력: `pii.scan` 마스킹 후 검색/LLM 전달
- 출력: `answer_validator`의 PII 마스킹
- 로그: 원문 PII 저장 금지 (sha256 해시 + 마스킹된 텍스트)
- 외부 API 전달 직전 1회 더 검사 → 위험 시 `AiPiiBlocked`

---

## 15. Hybrid Retriever 구조

- 점수 = α * keyword_score + β * vector_score (정규화 후 가중합)
- α/β는 `AiSetting`에 저장 (기본 α=0.6, β=0.4 — 운영 튜닝 필요)
- vector 비활성 시 자동 α=1.0, β=0.0
- 결과 dedup: chunk_id 기준

---

## 16. Prompt 버전 관리

- `rag/prompts.py`에 `PROMPTS = {"manual_qa.system": {"v1": "...", "v2": "..."}, ...}`
- 응답 로그/응답 JSON에 `prompt_version` 기록
- 프롬프트 변경은 새 버전 추가 (기존 삭제 금지) → A/B 비교 가능

---

## 17. AI 로그 / 감사 로그 필드

`AiUsageLog` 컬럼 후보 (m012 이후 마이그레이션으로 추가):
- `ai_mode`, `llm_called`, `embedding_called`
- `local_answer_used` (bool), `local_answer_type` ∈ `{db_query, keyword_search, chunk_keyword_search, rule_based, template, safety_block, status_query}`
- `skipped_llm_reason`, `skipped_embedding_reason`
- `external_api_allowed`
- `token_used_estimate`, `usage_total_tokens`, `input_tokens`, `output_tokens`, `embedding_tokens`
- `cost_estimate`
- `provider`, `model`, `prompt_version`
- `reason_code`

원칙:
- 원문 PII 저장 금지 (마스킹·해시만)
- API key 저장 금지 (관리자 화면에는 등록 여부만)

---

## 18. Feature Flag 설계

`AiSetting` 또는 별도 `AiFeatureFlag` 테이블:
- `AI_LOCAL_ONLY_MODE` (boolean)
- `AI_EXTERNAL_LLM_ENABLED`
- `AI_EXTERNAL_EMBEDDING_ENABLED`
- `AI_LOCAL_RULES_ENABLED`
- `AI_LOCAL_MANUAL_SEARCH_ENABLED`
- `AI_LOCAL_DB_QUERY_ENABLED`
- `AI_RAG_ENABLED`
- `AI_RAG_VECTOR_ENABLED`
- `AI_RAG_HYBRID_ENABLED`
- `AI_RAG_LOGGING_ENABLED`
- `AI_RAG_STRICT_SAFETY`

기본값:
- `AI_LOCAL_ONLY_MODE=false`, `AI_RAG_ENABLED=true`, vector/hybrid는 false (단계적 활성화)
- 모든 플래그 변경은 admin 권한

---

## 19. 출처 표시 정책

- 모든 답변에 `sources[].{title, path, snippet}` 동봉 (현행 키)
- LLM 답변은 마지막 줄에 사용 매뉴얼 파일명 표시 (시스템 프롬프트 명시)
- Local Answer Composer는 출처 누락 시 답변 생성 자체 거부 (안전 응답)

---

## 20. 성능 / Timeout 기준

- 검색: 200ms 이내 목표 (knowledge 10개 규모)
- LLM 호출: 기본 timeout 8s, 재시도 1회
- Embedding: 기본 timeout 4s, 재시도 0회 (실패 시 keyword fallback)
- 전체 요청 95%ile: 3s 이내 (LLM 호출 제외 시)

---

## 21. 동시 실행 정책

- reindex: 전역 lock (한 번에 1개)
- 일반 질의: 동시 처리 가능 (read-only)
- reindex 중 일반 질의: 기존 인덱스 사용

---

## 22. AI 설정 저장 위치

- `AiSetting` (DB, 단일 row)
- 신규 feature flag: `AiSetting`에 컬럼 추가 또는 `AiFeatureFlag` 신설 — 18-1에서 결정
- 환경변수는 사용하지 않음 (운영은 GUI 설정 일관성)

---

## 23. 후방호환 보장 (강한 약속)

- `/api/ai/manual/search`, `/api/ai/manual/ask`의 기존 응답 키 보존
- `manual_qa.ask_manual_question(provider_override=)` 시그니처 보존
- `_rag_search(query, category, limit)` 시그니처 보존 (또는 동등 wrapper 제공)
- `pii.scan(text)` 반환형 보존
- `AiSetting`/`AiUsageLog` 기존 컬럼 보존

---

## 24. 구현 시점 매핑 (요약)

| 구성요소 | 구현 세션 |
|---|---|
| 폴더 구조 / schemas / source_builder | 18-1 |
| query_normalizer / query_parser / intent_router (최소) | 18-1 |
| keyword_index 분리 / synonyms / confidence / answer_validator / answer_composer(min) | 18-2 |
| chunker / loader / normalizer | 18-3 |
| knowledge_chunks DB / indexer / reindex | 18-4 |
| embeddings / store / similarity | 18-5 |
| hybrid retriever / cache / reranker | 18-6 |
| 라우터 통합 / manual_qa wrapper / 관리자 UI | 18-7 |
| 회귀 + PyInstaller 검증 | 18-8 |
