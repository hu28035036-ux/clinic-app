# 18-4 knowledge_chunks DB / reindex — Fix Summary

## 1. 신규/수정 파일 목록

### 신규
1. `app/migrations/m012_knowledge_chunks.py` — m012 마이그레이션 (raw SQL, IF NOT EXISTS 멱등 가드)
2. `app/services/ai/knowledge/indexer.py` — reindex 진입점 + `ReindexResult` dataclass + lock
3. `tests/harness/reindex_harness.py` — helper (loader monkeypatch, chunk count, 외부호출 0 단언)
4. `tests/test_ai_reindex_harness.py` — 사용자 15 단언 + 추가 9 = **24 tests**
5. `docs/migrations_rollback/m012_rollback.sql` — 수동 롤백 SQL (자동 실행 금지)
6. `reports/ai_dev_loop/18-4_test_report.md` (본 세션 보존본)
7. `reports/ai_dev_loop/18-4_fix_summary.md` (본 파일)
8. `reports/ai_dev_loop/18-4_codex_review_request.md`

### 수정 (최소 범위)
9. `app/models/models.py` — 끝에 `KnowledgeChunk`, `KnowledgeIndexRun` 두 ORM 클래스만 append (기존 클래스 무수정)
10. `reports/ai_dev_loop/latest_test_report.md` — 18-4 결과로 overwrite
11. `reports/ai_dev_loop/latest_fix_summary.md` — 18-4 결과로 overwrite
12. `reports/ai_dev_loop/latest_codex_review_request.md` — 18-4 결과로 overwrite

### 손대지 않은 파일 (사용자 금지 사항 또는 회귀 위험)
- 모든 m001~m011, `dosu_clinic.spec`, `requirements.txt`, `pyproject.toml`
- `app/services/ai/manual_qa.py`, `app/services/rag/search.py`
- `app/services/ai/knowledge/{loader,normalizer,chunker,keyword_index}.py`
- `app/services/ai/rag/*.py`, `app/routers/*.py`
- `tests/conftest.py`, 기존 모든 테스트 파일
- `app/services/ai/knowledge/keyword_index.py:build_index|search` stub (NotImplementedError 그대로)

## 2. 변경 요약 (파일별)

### `app/models/models.py`
- 마지막에 `KnowledgeChunk` (15 컬럼 + UniqueConstraint(doc_id, chunk_index)) 와 `KnowledgeIndexRun` (15 컬럼) 두 클래스 추가
- 기존 클래스/import 무수정 (`from sqlalchemy import (..., UniqueConstraint)` 는 이미 import 됨)

### `app/migrations/m012_knowledge_chunks.py` (신규, 약 60줄)
- `MIGRATION_ID = 12`, `DESCRIPTION = "knowledge_chunks/knowledge_index_runs 인덱스 보강"`
- `_table_exists` 가드 + `CREATE UNIQUE INDEX IF NOT EXISTS uq_knowledge_chunks_doc_chunk` + `ix_knowledge_chunks_content_hash` + `ix_knowledge_chunks_category` + `ix_knowledge_index_runs_started`
- 두 번 실행해도 안전 — `test_22_m012_idempotent` 가 검증

### `app/services/ai/knowledge/indexer.py` (신규, 약 290줄)
- `ReindexResult` dataclass: 사용자 요구 12 필드 + `run_id` (internal)
- `reindex_all(db, *, trigger="manual")` 진입점 — `_REINDEX_LOCK.acquire(blocking=False)` 비차단 lock
- `_reindex_locked` 본체: cache reset → run row insert → load_documents → per-doc try/except → finalize
- `_index_one_document`: (doc_id, chunk_index) 기반 upsert 로직 (insert/skip/update)
- `_final_status`: failed=0 → success / processed≥1 → partial / 그 외 → failed
- `_short_error`: PII/원문 누출 방지 400자 컷
- 외부 호출 0 (chunker 만 호출)
- 어떤 분기에서도 `db.delete()` / `DELETE FROM` 호출 0 (사용자 요구 #7 강화)

### `tests/harness/reindex_harness.py` (신규, 약 110줄)
- `make_doc(path, raw_text, category)` — 인라인 Document 팩토리
- `count_chunks(db, doc_id=None)`, `count_runs(db, status=None)`
- `monkeypatch_load_documents(monkeypatch, docs)` — indexer.load_documents 패치
- `monkeypatch_chunker_raises(monkeypatch, error)` — 모든 호출 raise
- `monkeypatch_chunker_raises_for_path(monkeypatch, fail_path, error)` — 특정 path 만 raise (부분 실패 시뮬레이션)
- `assert_no_external_call(provider, embedding_provider)` — chunk_harness 와 동일 컨벤션

### `tests/test_ai_reindex_harness.py` (신규, 약 480줄)
- 24 tests (사용자 15 + 추가 9)
- `db_session` fixture: SessionLocal 그대로 (별도 in-memory engine 금지 — 위험요소 §14-1)
- `clean_chunk_tables` fixture: 각 테스트 전후 `KnowledgeChunk` / `KnowledgeIndexRun` truncate (테스트 격리)

### `docs/migrations_rollback/m012_rollback.sql` (신규)
- 수동 실행 only, 자동 실행 금지
- DROP INDEX × 4 + DROP TABLE × 2 + DELETE FROM schema_migrations WHERE id=12
- 실행 전 백업/승인 체크리스트 포함

## 3. content_hash 중복 방지 알고리즘

위치 키 `(doc_id, chunk_index)` 기준:

```python
existing = {c.chunk_index: c for c in
            db.query(KnowledgeChunk).filter(KnowledgeChunk.doc_id == doc_id).all()}

for ch in new_chunks:
    prev = existing.pop(ch.chunk_index, None)
    if prev is None:
        db.add(_chunk_to_orm(ch))
        result.inserted_chunks += 1
    elif prev.content_hash == ch.content_hash:
        result.skipped_chunks += 1     # ← 사용자 요구 #5
    else:
        _apply_chunk_to_orm(prev, ch)
        result.updated_chunks += 1     # ← 사용자 요구 #6

# existing 잔여 = orphan. 사용자 요구 #7: DELETE 금지 (보존).
```

`content_hash` 단일 컬럼 UNIQUE 는 걸지 않음 — 서로 다른 문서가 동일 텍스트일 수 있음. 중복 방지는 `(doc_id, chunk_index)` UNIQUE 로.

## 4. 부분 실패 보존 알고리즘

per-doc commit 으로 사용자 요구 #7 자동 충족:

```python
for doc in docs:
    try:
        _index_one_document(db, doc, result)
        db.commit()  # 직전 commit 은 후속 rollback 영향 0
    except Exception as e:
        db.rollback()
        result.failed_documents += 1
        result.errors.append({"path": doc.path, "error": _short(e), "stage": "persist"})
```

- 어떤 분기에서도 `db.delete()` 호출 0 → 기존 chunk 영구 보존
- 실패 path 와 short error 는 `KnowledgeIndexRun.failed_paths` 와 `errors` (JSON) 에 기록
- `_short_error` 가 400자 컷 + traceback 본문 제외 — PII/원문 누출 방지

## 5. 동시 실행 lock

```python
_REINDEX_LOCK = threading.Lock()

def reindex_all(db, *, trigger="manual") -> ReindexResult:
    if not _REINDEX_LOCK.acquire(blocking=False):
        return ReindexResult(status="skipped_in_progress", ...)
    try:
        return _reindex_locked(db, trigger=trigger)
    finally:
        _REINDEX_LOCK.release()
```

- 비차단 acquire → 진행 중이면 즉시 `skipped_in_progress` 반환, 새 run row 생성 0
- `test_18_lock_blocks_concurrent_reindex` 가 외부에서 lock 점유 후 호출하여 검증

## 6. 자동 수정 루프 횟수

- **2회** (5회 한도 중)
- 1차: `_final_status` 의 `processed > failed` 조건이 `1 > 1` 거짓 → 모든 partial 케이스가 failed 로 분류. `test_8` 1개 실패.
- 수정: 조건을 `processed >= 1` 로 변경 (한 개라도 성공하면 partial).
- 2차: 24/24 통과.

## 7. PyInstaller spec 비수정 정책 (위험요소)

- `dosu_clinic.spec:76-83` 의 `glob.glob('app/migrations/m*_*.py')` 가 m012 자동 등록 → spec 수정 0
- `app.models.models` 은 이미 hidden import 됨 → 신규 ORM 클래스도 자동 포함
- **18-7 (관리자 UI) 시점에 라우터가 `app.services.ai.knowledge.indexer` 를 import 추가하면 spec 보강 필요** — 본 세션은 internal-only 정책이라 보강 불필요. Codex 가 18-7 진입 시 명시적으로 검토 권장.

## 8. 손대지 않은 영역 (사용자 금지 사항 준수 입증)

- ❌ vector / embedding / hybrid retriever 코드 0 줄
- ❌ knowledge_vectors 테이블 0
- ❌ 외부 LLM/Embedding API 호출 코드 0
- ❌ UI / 관리자 화면 / `/api/ai/reindex` 라우터 0 (사용자 명시 금지)
- ❌ requirements.txt / pyproject.toml / dosu_clinic.spec 변경 0
- ❌ 기존 manual API 응답 9개 키 변경 0 (`test_contract_*` 9 tests 통과)
- ❌ 기존 SMS AI / 휴무 AI 동작 변경 0 (`test_ai_sms_*` / `test_ai_action_leave.py` 통과)

## 9. 회귀 보호

- pytest 전체: **313 passed, 1 skipped, 7 xfailed**
- 회귀 보호 테스트 모두 통과:
  - `test_ai_chunker_harness.py` (골든 fingerprint 6 매뉴얼 보존)
  - `test_ai_manual_rag_harness.py` + `..._contract.py` (응답 키 9개 보존)
  - `test_ai_safety_harness.py`
  - `test_ai_full_harness.py`
  - `test_migration_spec_discovery.py` (m012 자동 발견)

## 10. 기본값/상수 변경 사항

- 변경 없음 — `MIN_CHUNK_CHARS=200`, `MAX_CHUNK_CHARS=1200`, `OVERLAP_CHARS=150` 그대로 (chunker 무수정)
- 신규 상수 (indexer.py): `_ERROR_TEXT_LIMIT=400` (PII/원문 누출 방지 상한), `_FAILED_PATH_SEP="\n"`, `STATUS_*` 5개

## 11. 다음 세션 (18-5) 진입 권고

**yes** — Codex 검증 통과 후 18-5 (vector/embedding) 진입 가능. 근거: 사용자 요구 15개 + 추가 9개 단언 통과, 회귀 0, lock 동시성 검증, 외부 호출 0 검증.
