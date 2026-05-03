# 18-2 keyword RAG 분리 — 테스트 리포트 (스코프 엄격화 후)

세션: 18-2 (keyword manual RAG 검색 로직 신규 구조 분리)
일시: 2026-05-02
대상 브랜치: ai-rag-v1-integration
업데이트: Codex 재검증 피드백 반영 — vector/ 디렉토리 + chunk/embedding 관련 schemas/tests 제거

## 1. 실행 명령 및 결과 요약

| # | 명령 | 결과 |
|---|---|---|
| 1 | `pytest tests/test_ai_manual_rag_harness.py -v` | **18 passed** |
| 2 | `pytest tests/test_ai_manual_rag_contract.py -v` | **9 passed** |
| 3 | `pytest tests/test_ai_safety_harness.py -v` | **12 passed** |
| 4 | `pytest tests/test_ai_full_harness.py -v` | **8 passed** (이전 9 → vector_package_importable 정리) |
| 5 | `pytest tests -v` | **254 passed, 1 skipped, 7 xfailed** |
| 6 | `ruff check app tests scripts` | **All checks passed!** |
| 7 | `python scripts/check_db_path.py` | **EXIT_CODE=0** |

신규 추가/약화된 테스트 없음. 18-1 잔재(vector/embedding/chunk) 정리만 수행.

## 2. 핵심 단언 통과 항목

### 2.1 응답 키 회귀 0
- `test_contract_manual_search_required_keys_3` ✅
- `test_contract_manual_ask_required_keys_9` ✅
- `test_contract_manual_search_200_response_has_all_required_keys` ✅
- `test_contract_manual_ask_200_response_has_all_9_keys` ✅
- `test_contract_source_items_have_3_keys` ✅
- `test_contract_manual_ask_no_unknown_required_keys_removed` ✅
- `test_contract_optional_keys_not_required_in_v1_3_3` ✅ (embedding_called 제거 후 4개 optional 키만 검사)

### 2.2 manual_qa import 경로/시그니처 보존
- `test_existing_manual_qa_still_importable` ✅
- `test_existing_rag_search_still_importable` ✅

### 2.3 18-1 stub 단언 (NotImplementedError) 보존
- `test_pipeline_run_manual_qa_not_implemented` ✅
- `test_retriever_retrieve_not_implemented` ✅

### 2.4 분리 전후 동작 동등성
- `test_existing_manual_qa_known_question_unchanged` ✅
- `test_existing_manual_qa_unknown_question_unchanged` ✅

### 2.5 안전 정책
- 12개 safety 테스트 전부 ✅

### 2.6 라우터 통합 smoke
- `test_router_manual_search_smoke_unchanged` ✅
- `test_router_manual_ask_disabled_unchanged` ✅
- `test_router_manual_ask_with_fake_unchanged` ✅

### 2.7 패키지 import 무결성
- `test_rag_package_importable` ✅
- `test_knowledge_package_importable` ✅
- ~~`test_vector_package_importable`~~ — 삭제됨 (스코프 외)
- `test_no_circular_import_when_loading_skeleton` ✅ (vector 항목 4개 제거 후)

### 2.8 schemas 정합성 (스코프 엄격화 후)
- `test_schemas_optional_4_keys_present` ✅ (이전 5개 → 4개. embedding_called 제거)
- `test_schemas_reason_codes_23_defined` ✅ (이전 29 → 23. §3 embedding 5개 + REASON_VECTOR_DISABLED 1개 제거)

## 3. 스코프 정리 내역

| 항목 | 처리 |
|---|---|
| `app/services/ai/vector/` 디렉토리 | 삭제 (4개 stub 파일) |
| `rag/schemas.py::Chunk` dataclass | 제거 |
| `rag/schemas.py::Answer.embedding_called` | 제거 (4개 optional 잔존) |
| `rag/schemas.py::REASON_VECTOR_DISABLED` | 제거 |
| `rag/schemas.py::REASON_EMBEDDING_SKIPPED_*` (5개) | 제거 |
| `tests/test_ai_full_harness.py::test_vector_package_importable` | 제거 |
| `tests/test_ai_full_harness.py::test_no_circular_import_when_loading_skeleton` | vector 4개 항목 제거 |
| `tests/test_ai_manual_rag_harness.py::test_schemas_optional_5_keys_present` | optional_4 로 갱신 |
| `tests/test_ai_manual_rag_harness.py::test_schemas_reason_codes_29_defined` | 23 로 갱신 |
| `tests/test_ai_manual_rag_contract.py::test_contract_optional_keys_not_required_in_v1_3_3` | embedding_called 제거 |
| `tests/harness/contract.py::OPTIONAL_KEYS` | embedding_called 제거 |

## 4. 외부 호출 차단

테스트 중 `openai.OpenAI` / `anthropic.Anthropic` SDK 클래스가 conftest의 `_block_sdk_modules()` 로 즉시 fail stub 으로 교체됨. FakeProvider 만 사용. `len(fake.calls)` 모드별 단언 통과.

## 5. 결론

분리 전후 외형 동작 100% 동일. 18-2 스코프(keyword RAG 분리만, chunk/vector/embedding/hybrid 미포함) 엄격 준수. 18-3 진입 가능 상태.
