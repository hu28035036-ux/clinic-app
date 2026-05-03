# 18-4 knowledge_chunks DB / reindex — 테스트 리포트

세션: 18-4
브랜치: ai-rag-v1-integration
실행일: 2026-05-02
상태: ✅ 5회 루프 안에 통과 (실 사용 루프 = 2회)

## 1. 실행 환경

- 작업 디렉토리: `C:\Users\user\Desktop\새 폴더\병원예약관리\병원예약관리`
- Python: 3.12.10 (venv)
- pytest: 8.4.2
- ruff: 최신 (`venv\Scripts\python.exe -m ruff`)
- 운영 DB 격리: `tests/conftest.py` 가 `DOSU_DB_PATH` 를 `tests/temp/test_clinic_<uuid>.db` 로 강제

## 2. 실행한 명령

```
venv\Scripts\python.exe -m pytest tests/test_ai_reindex_harness.py -v
venv\Scripts\python.exe -m pytest tests/test_ai_chunker_harness.py tests/test_ai_manual_rag_harness.py tests/test_ai_manual_rag_contract.py tests/test_ai_safety_harness.py tests/test_ai_full_harness.py -v
venv\Scripts\python.exe -m pytest tests -v
venv\Scripts\python.exe -m ruff check app tests scripts
venv\Scripts\python.exe scripts\check_db_path.py
```

`run_check.bat` 은 비대화형 환경에서 pause 로 멈추므로 위 3단계를 개별 실행 (스크립트 내용은 동일).

## 3. 결과 요약

| 명령 | 결과 |
|---|---|
| `pytest tests/test_ai_reindex_harness.py` | **24 passed** (사용자 15 + 추가 9) |
| `pytest test_ai_chunker_harness + manual_rag + safety + full + contract` | **82 passed** (회귀 0) |
| `pytest tests` (전체) | **313 passed, 1 skipped, 7 xfailed** (회귀 0) |
| `ruff check app tests scripts` | **All checks passed!** |
| `scripts/check_db_path.py` | 운영 DB 경로 출력 (단독 실행 — conftest 격리는 별도 테스트에서 검증) |

## 4. 사용자 15개 단언 → 테스트 매핑

| # | 단언 | 테스트 함수 | 결과 |
|---|---|---|---|
| 1 | knowledge_chunks 테이블 생성 | `test_1_knowledge_chunks_table_created` + `test_1b/_1c` 컬럼 | ✅ |
| 2 | 문서 → chunk → DB 저장 | `test_2_document_to_chunks_to_db` | ✅ |
| 3 | 필드 보존 (source_path/title/heading/chunk_index/content/content_hash) | `test_3_chunk_fields_persisted` | ✅ |
| 4 | 두 번 reindex → 중복 chunk 없음 | `test_4_double_reindex_no_duplicates` | ✅ |
| 5 | content_hash 같으면 skip | `test_5_same_hash_skipped` | ✅ |
| 6 | 변경된 chunk 반영 | `test_6_changed_doc_updates_affected_chunks` | ✅ |
| 7 | reindex 실패 시 기존 chunk 보존 | `test_7_failure_preserves_existing_chunks` | ✅ |
| 8 | 부분 실패 정보 기록 | `test_8_partial_failure_records_failed_paths` | ✅ |
| 9 | API key 없어도 동작 | `test_9_works_without_api_key` | ✅ |
| 10 | LLM provider 호출 0 | `test_10_no_llm_provider_call` | ✅ |
| 11 | embedding provider 호출 0 | `test_11_no_embedding_provider_call` | ✅ |
| 12 | 운영 DB 미사용 | `test_12_does_not_use_operational_db` | ✅ |
| 13 | manual RAG 회귀 0 | `test_13_manual_rag_unaffected_by_reindex` + 별도 file 통과 | ✅ |
| 14 | safety 회귀 0 | `test_14_safety_harness_imports_and_keys_intact` + 별도 file 통과 | ✅ |
| 15 | full 회귀 0 | `test_15_full_harness_imports_intact` + 별도 file 통과 | ✅ |

추가 단언 (9개):
- `test_16_unique_doc_chunk_constraint` — UNIQUE (doc_id, chunk_index) IntegrityError 발생 ✅
- `test_17_run_status_not_running_after_reindex` — KnowledgeIndexRun.status 정상 종료 ✅
- `test_18_lock_blocks_concurrent_reindex` — lock 점유 중 호출 → skipped_in_progress + run row 미생성 ✅
- `test_19_indexer_import_graph_safe` — AST 검사 (네트워크/SDK/provider 부재) ✅
- `test_20_orphan_chunks_not_deleted` — 작아진 문서로 reindex 해도 row 수 보존 ✅
- `test_21_reindex_result_has_all_required_fields` — 12개 사용자 요구 필드 모두 노출 ✅
- `test_22_m012_idempotent` — m012.up() 두 번 실행해도 sqlite_master 변동 없음 ✅
- `test_1b_knowledge_chunks_columns_present` — 15개 필수 컬럼 존재 ✅
- `test_1c_knowledge_index_runs_columns_present` — 15개 컬럼 존재 ✅

## 5. 자동 수정 루프

| 루프 | 시점 | 결과 |
|---|---|---|
| 1차 | 초기 구현 | 23/24 통과 — `test_8_partial_failure_records_failed_paths` 실패 |
| - | 분석 | `_final_status` 가 `processed > failed` 조건이라 `2 docs (1 ok + 1 fail)` 케이스에서 `1 > 1` 거짓 → STATUS_FAILED 반환 |
| - | 수정 | `_final_status` 조건을 `processed >= 1` 로 변경 (한 개라도 성공하면 partial) |
| 2차 | 재실행 | **24/24 통과** |

5회 한도 중 2회 사용. 5회 실패 시나리오 미진입.

## 6. 기존 테스트 회귀

전체 313 passed (1 skipped, 7 xfailed). 회귀 0.

핵심 회귀 보호 테스트 통과:
- `test_ai_chunker_harness.py` — 32 tests (골든 fingerprint 6 매뉴얼 모두 일치)
- `test_ai_manual_rag_harness.py` — 18 tests
- `test_ai_manual_rag_contract.py` — 9 tests (응답 키 9개 후방호환)
- `test_ai_safety_harness.py` — 12 tests
- `test_ai_full_harness.py` — 8 tests
- `test_migration_spec_discovery.py` — m012 자동 글롭 감지 (전체 pytest 안에서 통과)

## 7. 운영 DB 보호 검사

- `tests/conftest.py` 가 import-time 에 `DOSU_DB_PATH=tests/temp/test_clinic_<uuid>.db` 설정 후 `assert_safe_db_path()` 호출 — 모든 테스트가 이 격리 경로에서 실행
- `test_12_does_not_use_operational_db` 가 indexer.py 의 import-graph 도 검사 (sqlite3/네트워크 SDK 부재)
- `scripts/check_db_path.py` 는 비-테스트 환경에서 단독 실행되어 운영 DB 경로 출력 — 테스트와 무관

## 8. 외부 호출 0 입증

- `test_10_no_llm_provider_call` — FakeProvider 의 `len(.calls) == 0` 단언
- `test_11_no_embedding_provider_call` — mock embedding provider `calls == 0` 단언
- `test_19_indexer_import_graph_safe` — AST 로 indexer.py 가 `requests/httpx/openai/anthropic/app.services.ai.provider/...rag.pipeline` 미import 검증
- `test_12_does_not_use_operational_db` — indexer.py 텍스트 grep 으로 sqlite3 직접 import 부재

## 9. 다음 세션 진입 자체 판단

**yes** — 18-5 (vector / embedding) 진입 가능.

근거:
- 사용자 요구 15개 + 추가 9개 단언 모두 통과
- 회귀 0 (313 passed)
- ruff 통과
- m012 idempotent 검증
- lock 동시성 검증
- 외부 호출 0 검증 (테스트 + AST + 텍스트 grep 3중)
- vector/embedding/hybrid/UI 미혼입 (사용자 금지 사항 준수)

단, Codex 검증 통과 전 18-5 진입 금지 (AI_WORKING_RULES §4).
