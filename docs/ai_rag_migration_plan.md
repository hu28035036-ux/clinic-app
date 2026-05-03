# AI/RAG 마이그레이션 계획 (ai_rag_migration_plan)

> Chunk / Vector 도입과 reindex 운영을 위한 DB 확장·롤백·재인덱싱 정책.
> 본 문서는 **데이터/스키마 변경 측면**만 다룬다. 구조는 `ai_rag_architecture_plan.md`,
> 실행 순서는 `ai_rag_rollout_plan.md`, 에러 코드는 `ai_rag_error_codes.md` 참조.

---

## 0. 절대 원칙

1. **기존 마이그레이션(m001~m011) 수정 금지.** 새 마이그레이션은 **m012 이후**로만 추가.
2. **운영 DB(`%APPDATA%\도수치료예약\clinic.db`) 직접 접근 금지.** 마이그레이션은 앱 시작 시 `schema_migrations` 기준 자동 실행.
3. **`content_hash`가 같으면 chunk/embedding 중복 생성 금지.**
4. **문서 변경 없음 → embedding 재생성 금지.** (비용·토큰 절약)
5. **API key 없음 → vector 기능만 disabled.** keyword RAG는 정상 동작.
6. **vector 실패 → keyword RAG fallback.**
7. **reindex 실패 시 기존 index 삭제 금지.** 부분 실패 → 실패 문서만 표시.
8. **운영 중 reindex 실패해도 기존 keyword RAG는 계속 동작.**
9. **PyInstaller spec hidden import에 새 마이그레이션 등록 필수.**

---

## 1. 새 DB 테이블 후보

추가 대상 (마이그레이션 m012, m013):

| 테이블 | 마이그레이션 | 목적 |
|---|---|---|
| `knowledge_chunks` | m012 | 마크다운 → 청크 영속화 |
| `knowledge_vectors` | m013 | 청크 임베딩 저장 |
| `knowledge_index_runs` | m012 또는 m014 | reindex 이력/결과 (관리자 화면용) |

> 정확한 분배는 18-4 세션에서 확정. 본 문서는 후보 스키마 정의가 목적.

---

## 2. `knowledge_chunks` 스키마 후보 (m012)

```sql
CREATE TABLE knowledge_chunks (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  doc_id          TEXT    NOT NULL,           -- 파일 stable id (예: 상대경로 sha1)
  source_path     TEXT    NOT NULL,           -- 원본 상대 경로 (예: knowledge/manuals/sms_compose.md)
  category        TEXT    NOT NULL,           -- "manuals" | "sms_guides" 등
  title           TEXT    NOT NULL DEFAULT '',
  heading         TEXT    NOT NULL DEFAULT '',  -- 청크가 속한 헤딩 텍스트
  section_path    TEXT    NOT NULL DEFAULT '',  -- 헤딩 경로 "h2 > h3"
  chunk_index     INTEGER NOT NULL,            -- 문서 내 0부터
  content         TEXT    NOT NULL,
  content_hash    TEXT    NOT NULL,            -- sha256(content)
  token_count     INTEGER NOT NULL DEFAULT 0,
  tags            TEXT    NOT NULL DEFAULT '', -- "," 구분 또는 JSON
  document_version TEXT   NOT NULL DEFAULT '', -- 마지막 reindex 시점 식별자
  created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
  updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX ix_knowledge_chunks_doc_chunk
  ON knowledge_chunks (doc_id, chunk_index);

CREATE INDEX ix_knowledge_chunks_content_hash
  ON knowledge_chunks (content_hash);

CREATE INDEX ix_knowledge_chunks_category
  ON knowledge_chunks (category);
```

`content_hash` UNIQUE는 걸지 않음 (서로 다른 문서가 동일 텍스트일 수 있음). 중복 방지는 `(doc_id, chunk_index)` UNIQUE로.

---

## 3. `knowledge_vectors` 스키마 후보 (m013)

```sql
CREATE TABLE knowledge_vectors (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  chunk_id        INTEGER NOT NULL,
  provider        TEXT    NOT NULL,           -- "openai" | "fake" 등
  model           TEXT    NOT NULL,           -- "text-embedding-3-small" 등
  dimension       INTEGER NOT NULL,
  embedding_json  TEXT    NULL,               -- 길이가 작으면 JSON
  embedding_blob  BLOB    NULL,               -- 큰 벡터는 BLOB (둘 중 하나만 채움)
  content_hash    TEXT    NOT NULL,           -- 임베딩 시점의 chunk content_hash
  created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (chunk_id) REFERENCES knowledge_chunks(id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX ix_knowledge_vectors_chunk_provider_model
  ON knowledge_vectors (chunk_id, provider, model);

CREATE INDEX ix_knowledge_vectors_content_hash
  ON knowledge_vectors (content_hash);
```

운영 결정 사항(18-5에서 확정):
- `embedding_json` vs `embedding_blob` 선택 — dimension에 따라.
- 외부 vector DB(faiss/chromadb) 도입 여부 — 본 계획은 SQLite 기반 시작.

---

## 4. `knowledge_index_runs` 스키마 후보

```sql
CREATE TABLE knowledge_index_runs (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  started_at      TEXT    NOT NULL DEFAULT (datetime('now')),
  finished_at     TEXT    NULL,
  status          TEXT    NOT NULL DEFAULT 'running',  -- running|success|partial|failed
  total_docs      INTEGER NOT NULL DEFAULT 0,
  succeeded_docs  INTEGER NOT NULL DEFAULT 0,
  failed_docs     INTEGER NOT NULL DEFAULT 0,
  total_chunks    INTEGER NOT NULL DEFAULT 0,
  total_vectors   INTEGER NOT NULL DEFAULT 0,
  failed_paths    TEXT    NOT NULL DEFAULT '',  -- 줄바꿈 구분
  trigger         TEXT    NOT NULL DEFAULT '',  -- "startup"|"manual"|"upgrade"
  notes           TEXT    NOT NULL DEFAULT ''
);
```

관리자 화면에서 "마지막 reindex 결과" 표시에 사용.

---

## 5. `content_hash` 중복 방지 정책

- chunk: 같은 (doc_id, chunk_index) 위치에 동일 `content_hash`면 UPDATE 생략.
- vector: 같은 (chunk_id, provider, model) + 동일 `content_hash`면 재생성 생략.
- 문서가 변경되지 않은 reindex는 사실상 no-op.

---

## 6. Reindex 정책

### 6-1. 트리거
- **앱 시작**: `schema_migrations` 적용 후, knowledge 폴더 mtime 변경 감지 시 자동 reindex
- **수동**: 관리자 UI "Reindex 실행" 버튼
- **업그레이드**: 새 prompt_version / chunker_version 배포 시 자동

### 6-2. 동시 실행 방지
- 전역 lock (DB 또는 파일 lock).
- 진행 중 재실행 요청 → `reindex_in_progress` reason_code 반환.
- 진행 중 일반 질의는 **기존 인덱스 사용**.

### 6-3. 부분 실패 처리
- 실패 문서는 `knowledge_index_runs.failed_paths`에 기록.
- 성공한 문서의 chunk/vector는 commit.
- 전체 인덱스 삭제 금지.

### 6-4. 완료 후 교체
- 새 인덱스가 모두 commit된 후, 메모리 내 retriever가 새 인덱스 참조로 교체.
- 교체 실패 시 기존 인덱스 유지.

---

## 7. Embedding 실패 시 fallback

| 실패 유형 | 동작 |
|---|---|
| API key 없음 | vector 기능만 disabled, keyword RAG 정상. `vector_disabled` reason_code. |
| 호출 timeout | 해당 chunk만 vector 생성 실패 표기, 다음 chunk 진행. 검색 시 keyword fallback. |
| Provider 오류 | 5분간 embedding 호출 차단 (circuit breaker). keyword fallback. |
| 차원 불일치 | 새 model로 인식, 별도 row 생성 (UNIQUE에 model 포함되어 있으므로). |
| `local_only` 모드 | 호출 시도 자체 차단, `embedding_skipped_local_only` reason_code. |

---

## 8. API Key 없을 때 Vector Disabled 정책

- `AiSetting.api_key`가 비어 있고 `embedding_provider`가 외부 API를 요구하면:
  - `AI_EXTERNAL_EMBEDDING_ENABLED`를 자동 false 처리 (런타임).
  - reindex 시 vector 단계만 건너뜀, chunk 인덱싱은 계속.
  - 검색은 keyword/chunk-keyword만 사용.
  - 관리자 화면에 "Vector 비활성: API key 미설정" 표시.

---

## 9. 운영 DB 보호 정책

- 마이그레이션 실행 경로는 `%APPDATA%\도수치료예약\clinic.db` (앱 부팅 시).
- 테스트는 `tests/conftest.py`의 격리 경로(`tests/temp/test_clinic_<uuid>.db`)에서만.
- `scripts/check_db_path.py` 통과 안 하면 머지 금지 (CLAUDE.md / AI_WORKING_RULES §1.2).
- 마이그레이션은 idempotent: 동일 m012를 두 번 실행해도 안전.
- 운영 DB에 직접 SQL 실행 금지. 모든 변경은 `app/migrations/m0XX_*.py`로만.

---

## 10. 롤백 계획

### 10-1. 코드 롤백
- 신규 모듈은 모두 `app/services/ai/{rag,knowledge,vector}/` 격리. 폴더 삭제 + spec hidden import 제거로 v1.3.3 동작 복귀.
- `manual_qa.py` wrapper 인터페이스 유지가 필수 — wrapper만 v1.3.3 코드로 되돌리면 라우터 동작 회복.

### 10-2. 데이터 롤백
- m012, m013, m014 추가 테이블 제거 SQL을 별도로 보관 (`docs/migrations_rollback/`):
  ```sql
  DROP INDEX IF EXISTS ix_knowledge_vectors_content_hash;
  DROP INDEX IF EXISTS ix_knowledge_vectors_chunk_provider_model;
  DROP TABLE IF EXISTS knowledge_vectors;
  DROP INDEX IF EXISTS ix_knowledge_chunks_category;
  DROP INDEX IF EXISTS ix_knowledge_chunks_content_hash;
  DROP INDEX IF EXISTS ix_knowledge_chunks_doc_chunk;
  DROP TABLE IF EXISTS knowledge_chunks;
  DROP TABLE IF EXISTS knowledge_index_runs;
  ```
- `schema_migrations` 테이블에서 해당 m012, m013 행 삭제. (운영 DB는 백업 후 수동 실행)
- **롤백 SQL은 자동 실행하지 않는다.** 사용자 명시 승인 후만.

### 10-3. 설정 롤백
- 신규 feature flag(`AI_RAG_VECTOR_ENABLED` 등)는 기본값 false로 시작 → 롤백 시 영향 없음.
- 활성화된 운영 환경은 flag만 false로 내리면 v1.3.3 동작.

---

## 11. 호환성 매트릭스

| 시나리오 | keyword RAG | chunk RAG | vector | hybrid |
|---|:---:|:---:|:---:|:---:|
| v1.3.3 (현행) | ✅ | ❌ | ❌ | ❌ |
| 18-4 완료 (chunk DB 도입) | ✅ | ✅ | ❌ | ❌ |
| 18-5 완료 (vector store) | ✅ | ✅ | ✅ (flag on 시) | ❌ |
| 18-6 완료 (hybrid) | ✅ | ✅ | ✅ | ✅ (flag on 시) |
| API key 없음 | ✅ | ✅ | ❌ | (자동 keyword fallback) |
| `local_only` 모드 | ✅ | ✅ | ❌ | (keyword만) |

---

## 12. PyInstaller spec 영향

신규 모듈은 `dosu_clinic.spec` `hiddenimports`에 등록 필수:
```python
'app.services.ai.rag',
'app.services.ai.rag.schemas',
'app.services.ai.rag.safety',
'app.services.ai.rag.prompts',
'app.services.ai.rag.query_normalizer',
'app.services.ai.rag.query_parser',
'app.services.ai.rag.intent_router',
'app.services.ai.rag.retriever',
'app.services.ai.rag.reranker',
'app.services.ai.rag.confidence',
'app.services.ai.rag.answer_composer',
'app.services.ai.rag.answer_validator',
'app.services.ai.rag.source_builder',
'app.services.ai.rag.cache',
'app.services.ai.rag.pipeline',
'app.services.ai.knowledge',
'app.services.ai.knowledge.loader',
'app.services.ai.knowledge.normalizer',
'app.services.ai.knowledge.chunker',
'app.services.ai.knowledge.synonyms',
'app.services.ai.knowledge.keyword_index',
'app.services.ai.knowledge.indexer',
'app.services.ai.vector',
'app.services.ai.vector.embeddings',
'app.services.ai.vector.store',
'app.services.ai.vector.similarity',
'app.services.ai.health',
# 신규 마이그레이션
'app.migrations.m012_knowledge_chunks',
'app.migrations.m013_knowledge_vectors',
# (m014가 생기면 추가)
```

`requirements.txt`는 18-5 시점에만 갱신 (외부 vector lib 도입 시).

---

## 13. 단계별 마이그레이션 매핑

| 세션 | 마이그레이션 | 비고 |
|---|---|---|
| 18-0 | (없음) | 하네스/테스트만 추가 |
| 18-1 | (없음) | 폴더 구조 생성 |
| 18-2 | (없음) | keyword 분리·리팩터 |
| 18-3 | (없음) | chunker 단위테스트 — DB 미사용 |
| 18-4 | **m012**: knowledge_chunks (+ knowledge_index_runs) | 청크 영속화 |
| 18-5 | **m013**: knowledge_vectors | 임베딩 영속화 |
| 18-6 | (없음 또는 m014: AI feature flag) | hybrid 활성화. flag 컬럼이 `AiSetting`에 추가 시 m014 |
| 18-7 | (없음) | 라우터 통합 / UI |
| 18-8 | (없음) | 회귀 + PyInstaller |

---

## 14. Reindex 운영 정책 (관리자 UI 연계)

화면 표시 항목:
- Knowledge 문서 수
- Chunk 수 (`COUNT(*) FROM knowledge_chunks`)
- Vector 수 (`COUNT(*) FROM knowledge_vectors`)
- 마지막 reindex 시간 (`MAX(started_at)`)
- 마지막 결과 (`status`, `succeeded_docs/total_docs`)
- 실패 문서 목록 (`failed_paths`)
- Vector 사용 가능 여부 (api_key 존재 + flag on)
- 검색 모드 (keyword | hybrid)
- AI 모드 (local_only | local_first | ai_assist)
- "Reindex 실행" 버튼 (관리자 권한)

---

## 15. 검증 / 안전 체크리스트

- [ ] m012, m013 모두 idempotent (두 번 실행해도 OK)
- [ ] m011 이하는 변경 없음 (diff 0)
- [ ] `scripts/check_db_path.py` 통과
- [ ] PyInstaller hidden import에 신규 마이그레이션 등록
- [ ] reindex 중복 실행 lock 동작 확인
- [ ] reindex 실패 시 기존 chunk/vector 보존 확인
- [ ] API key 없는 환경에서 chunk indexing은 성공, vector만 skip 확인
- [ ] 롤백 SQL 작성 + 보관
- [ ] tests/ 격리 환경에서만 마이그레이션 실행 확인
