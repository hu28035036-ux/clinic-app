# 18-4 knowledge_chunks DB / reindex — Codex 검증 요청

## 1. 세션 이름

`18-4_db_reindex`

## 2. 작업 목표

18-3 chunker 산출물을 SQLite 에 영속화. m012 마이그레이션(`knowledge_chunks` + `knowledge_index_runs`) 도입. 내부 함수 `reindex_all(db)` 가 매뉴얼 문서를 chunk 단위로 저장. content_hash 중복 방지. 부분 실패 시 기존 인덱스 보존. lock 동시성 차단. 외부 LLM/Embedding 호출 0. 기존 manual API / SMS AI / 휴무 AI 회귀 0.

본 세션에서는 **vector / embedding / hybrid / 관리자 API / UI / spec 수정 모두 금지** (사용자 명시 지시).

## 3. 변경 파일 목록

### 신규 (8)
1. `app/migrations/m012_knowledge_chunks.py`
2. `app/services/ai/knowledge/indexer.py`
3. `tests/harness/reindex_harness.py`
4. `tests/test_ai_reindex_harness.py` (24 tests)
5. `docs/migrations_rollback/m012_rollback.sql`
6. `reports/ai_dev_loop/18-4_test_report.md`
7. `reports/ai_dev_loop/18-4_fix_summary.md`
8. `reports/ai_dev_loop/18-4_codex_review_request.md` (본 파일)

### 수정 (4)
9. `app/models/models.py` — 끝에 `KnowledgeChunk`, `KnowledgeIndexRun` 두 클래스 append
10. `reports/ai_dev_loop/latest_test_report.md` (overwrite)
11. `reports/ai_dev_loop/latest_fix_summary.md` (overwrite)
12. `reports/ai_dev_loop/latest_codex_review_request.md` (overwrite)

## 4. 변경 요약

- m012: knowledge_chunks (15 컬럼, UNIQUE (doc_id, chunk_index)) + knowledge_index_runs (15 컬럼) 두 테이블 + 4 인덱스
- ORM 모델 두 개를 `app/models/models.py` 끝에 append (기존 클래스 무수정)
- indexer.py: `reindex_all(db, *, trigger)` + `ReindexResult` dataclass + threading.Lock 비차단 lock + per-doc commit + (doc_id, chunk_index) 기반 upsert (insert/skip/update) + 어떤 분기에서도 DELETE 호출 0
- reindex_harness: in-memory Document 팩토리, loader monkeypatch, chunker monkeypatch (전체/특정 path), 외부 호출 0 단언
- 테스트 24개: 사용자 15 + UNIQUE/lock/idempotent/import-graph/orphan-not-deleted/ReindexResult 필드/manual_search 회귀 등 9개 추가

## 5. 절대 바뀌면 안 되는 기능 (회귀 보호 대상)

- v1.3.3 `/api/ai/manual/search` / `/api/ai/manual/ask` 응답 9개 키 (`not_found, answer, confidence, sources[].{title,path,snippet}, blocked, blocked_reason, guard_hits, top_score, masked_question`)
- `manual_qa.ask_manual_question(provider_override=)` 시그니처
- 18-3 chunker 결정성 (golden fingerprint 6 매뉴얼)
- 기존 SMS AI / 휴무 AI 응답 / 라우터 동작
- m001~m011 마이그레이션 본문 (수정 0)
- `tests/conftest.py` 격리 4단계 (수정 0)
- `pyproject.toml` per-file-ignores `app/**` (수정 0)
- `dosu_clinic.spec` (수정 0 — m012 는 글롭 자동 등록)
- `requirements.txt` (수정 0)

## 6. 실행한 테스트 명령

```
venv\Scripts\python.exe -m pytest tests/test_ai_reindex_harness.py -v
venv\Scripts\python.exe -m pytest tests/test_ai_chunker_harness.py tests/test_ai_manual_rag_harness.py tests/test_ai_manual_rag_contract.py tests/test_ai_safety_harness.py tests/test_ai_full_harness.py -v
venv\Scripts\python.exe -m pytest tests -v
venv\Scripts\python.exe -m ruff check app tests scripts
venv\Scripts\python.exe scripts\check_db_path.py
```

## 7. 테스트 결과 요약

| 명령 | 결과 |
|---|---|
| `pytest tests/test_ai_reindex_harness.py -v` | **24 passed** |
| `pytest test_ai_chunker_harness + manual_rag + safety + full + contract -v` | **82 passed** |
| `pytest tests -v` | **313 passed, 1 skipped, 7 xfailed** |
| `ruff check app tests scripts` | **All checks passed!** |
| `scripts/check_db_path.py` | 단독 실행 시 운영 경로 정상 (테스트는 conftest 가 격리) |

## 8. 자동 수정 루프 횟수

**2회 / 5회 한도**

| 루프 | 상태 |
|---|---|
| 1차 | 23/24 — `_final_status` 가 `processed > failed` 조건이라 partial 케이스가 failed 로 분류 |
| 2차 | 24/24 — `_final_status` 를 `processed >= 1` 로 수정 |

## 9. 5회 실패 여부

**아니오** (2회 안에 통과)

## 10. 운영 DB 보호 검사 결과

- `tests/conftest.py` 가 import-time 에 `DOSU_DB_PATH=tests/temp/test_clinic_<uuid>.db` 강제 + `assert_safe_db_path()` 호출
- `test_12_does_not_use_operational_db` — db_guard 호출 + indexer.py 텍스트 검사 (sqlite3/네트워크 SDK 부재)
- `test_19_indexer_import_graph_safe` — AST 로 forbidden module prefix 검사
- 모든 313 테스트가 격리 DB 에서 실행됨 (운영 DB 미접근)

## 11. RAG 하네스 결과

- `test_ai_chunker_harness.py` — 32 passed (골든 fingerprint 보존)
- `test_ai_manual_rag_harness.py` — 18 passed
- `test_ai_safety_harness.py` — 12 passed
- `test_ai_full_harness.py` — 8 passed
- `test_ai_reindex_harness.py` — 24 passed (신규)

## 12. API 계약 테스트 결과

- `test_ai_manual_rag_contract.py` — 9 passed (응답 9개 키 후방호환 확인)
- 신규 indexer 는 라우터 미연결 (internal-only) → API 응답 변경 0

## 13. 할루시네이션 금지 테스트 결과

- 신규 indexer 는 LLM 미사용 → 할루시네이션 발생 경로 자체 부재
- 기존 `test_ai_hallucination.py` / `test_ai_safety_harness.py` 의 의료 단정/실행 오인 차단 테스트 모두 통과 (회귀 0)

## 14. PII 보호 테스트 결과

- `test_ai_safety_harness.py` 의 PII 마스킹 테스트 모두 통과
- 신규 indexer 의 `_short_error` 가 400자 컷 + traceback 본문 제외 — PII/원문/API key 누출 방지

## 15. 기존 SMS AI 회귀 테스트 결과

- `test_ai_sms_draft.py` / `test_ai_sms_validate.py` / `test_ai_sms_draft_hallucination.py` 모두 통과
- 신규 indexer 가 SMS AI 모듈 미수정 / 미import

## 16. 기존 휴무 AI 회귀 테스트 결과

- `test_ai_action_leave.py` 통과
- 신규 indexer 가 action_leave / date_resolver 미수정 / 미import

## 17. 남은 위험 요소

1. **PyInstaller spec 미수정 정책**: `app.services.ai.knowledge.indexer` 가 internal-only 라 spec hidden import 미등록 — 18-7 (관리자 UI) 가 라우터에서 indexer 를 import 추가하면 spec 보강 필요. 본 세션은 사용자 명시 금지로 미반영.
2. **orphan chunk 정책**: 문서가 작아져 chunk 수가 줄면 기존 row 가 보존됨 (사용자 요구 #7 강화). 18-5/18-6 의 retriever 가 `document_version` 으로 stale 거를 책임 — 본 세션 범위 밖.
3. **conftest 격리 의존**: 모든 테스트가 `tests/conftest.py` 의 4단계 격리에 의존. conftest 약화 금지.
4. **errors JSON 직렬화**: 비-ASCII (한국어 path) + 예외 객체 — `json.dumps(ensure_ascii=False, default=str)` 로 처리. exception 의 `__str__` 이 PII 를 포함할 수 있어 `_short_error` 가 400자 컷 적용.
5. **per-doc commit 트랜잭션 경계**: SQLAlchemy 표준 동작 — `commit()` 후 `rollback()` 은 다음 트랜잭션만 영향. `test_7` / `test_8` 에서 명시 검증.

## 18. Codex 가 집중 검토할 파일

1. `app/migrations/m012_knowledge_chunks.py` — 멱등성, IF NOT EXISTS, m011 와 동일 패턴
2. `app/services/ai/knowledge/indexer.py` — DELETE 부재 / lock 정확성 / per-doc commit / (doc_id, chunk_index) upsert 분기
3. `app/models/models.py` (끝부분) — `KnowledgeChunk` UniqueConstraint 정의, `KnowledgeIndexRun` 컬럼 누락 여부
4. `tests/test_ai_reindex_harness.py` — 24 tests 의 단언이 실제 사용자 15 요구사항을 모두 cover 하는지
5. `tests/harness/reindex_harness.py` — monkeypatch 패치가 indexer 모듈 attribute 를 정확히 잡는지

## 19. Codex 가 반드시 확인할 체크리스트

- [ ] m012 두 번 실행 안전 (idempotent) — `test_22_m012_idempotent` 단언 직접 재실행
- [ ] m001~m011 diff 0 — `git diff main -- app/migrations/m0[01]*.py app/migrations/m011*.py` 가 빈 결과
- [ ] lock 동시성 차단 — `test_18_lock_blocks_concurrent_reindex` 가 새 row 미생성 단언 검증
- [ ] 부분 실패 시 기존 인덱스 보존 — `test_7` 와 `test_20_orphan_chunks_not_deleted` 모두 통과
- [ ] indexer.py 에 `db.delete()` / `DELETE FROM` / `query(...).delete()` 호출 부재 — grep
- [ ] 운영 DB 미접근 — `test_12` + AST 검사 + 텍스트 grep 3중 통과
- [ ] PyInstaller hidden import 자동 등록 — `dosu_clinic.spec:76-83` 글롭이 m012 잡는지
- [ ] manual_qa / sms_draft / action_leave 미수정 — `git diff main -- app/services/ai/manual_qa.py app/services/ai/sms_draft.py app/services/ai/action_leave.py app/services/rag/search.py` 빈 결과
- [ ] requirements.txt / dosu_clinic.spec / pyproject.toml 수정 0 — git diff
- [ ] keyword_index.py 의 `build_index/search` stub 유지 (NotImplementedError) — git diff
- [ ] 응답 9개 키 보존 — `test_ai_manual_rag_contract.py` 9 tests 통과

## 20. 다음 세션 (18-5) 진입 자체 판단

**yes**

근거:
- 사용자 요구 15개 단언 + 추가 9개 단언 모두 통과 (24/24)
- 회귀 0 (전체 313 passed)
- ruff All checks passed
- m012 idempotent 검증
- lock 동시성 검증
- 외부 호출 0 3중 검증 (테스트 + AST + 텍스트 grep)
- vector/embedding/hybrid/UI/spec/requirements 미혼입 (사용자 금지 사항 100% 준수)
- 자동 수정 루프 2회 (5회 한도 여유)

단, AI_WORKING_RULES §4 에 따라 Codex 검증 통과 전 18-5 진입 금지.
