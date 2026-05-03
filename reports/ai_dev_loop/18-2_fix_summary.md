# 18-2 keyword RAG 분리 — Fix Summary (스코프 엄격화 후)

## 0. Codex 재검증 피드백 반영

1차 통과 후 Codex 재검증에서 다음 범위 초과 항목이 지적됨:
- `app/services/ai/vector/` 디렉토리 (4개 stub 파일) — 18-2 범위 외 (18-5 chunk+vector 시점)
- `rag/schemas.py` 의 `Chunk`, `embedding_called`, `REASON_VECTOR_DISABLED`, `REASON_EMBEDDING_SKIPPED_*` (5개) — 18-2 범위 외
- `tests/test_ai_full_harness.py::test_vector_package_importable` 및 관련 import 단언 — 18-2 범위 외

본 fix summary 는 위 항목을 모두 정리한 후의 최종 상태를 기록한다.

## 1. 변경 매핑 (where → where)

| 기존 | 신규 |
|---|---|
| `app/services/rag/search.py` 토큰화·inverted index·스코어링 | `app/services/ai/knowledge/keyword_index.py::search_documents` |
| `app/services/rag/search.py::_load_index` / `_build_runtime_index` | `app/services/ai/knowledge/loader.py::get_raw_documents` / `load_documents` |
| `app/services/ai/manual_qa.py::manual_search` 검색 단계 | `app/services/ai/rag/retriever.py::keyword_retrieve` |
| `app/services/ai/manual_qa.py::ask_manual_question` 전체 흐름 | `app/services/ai/rag/pipeline.py::run_manual_ask` |
| `app/services/ai/manual_qa.py::manual_search` 진입점 | `app/services/ai/rag/pipeline.py::run_manual_search` |
| `app/services/ai/manual_qa.py::validate_answer` | `app/services/ai/rag/pipeline.py::validate_answer` |

기존 `app/services/rag/search.py` 자체는 **변경 없음**.

## 2. 추가/수정/삭제한 파일 목록

### 신규/수정 (코드)
1. `app/services/ai/knowledge/loader.py` — `load_documents()`, `get_raw_documents()`, `reset_cache()` 정식 구현.
2. `app/services/ai/knowledge/keyword_index.py` — `search_documents()` 신규 구현. 기존 `build_index/search` (chunk 18-4 시그니처) 는 NotImplementedError 유지.
3. `app/services/ai/knowledge/__init__.py` — 패키지 docstring 갱신.
4. `app/services/ai/rag/retriever.py` — `keyword_retrieve()`, `to_sources()`, `reset_cache()` 신규 구현. 기존 `retrieve()` 는 NotImplementedError 유지.
5. `app/services/ai/rag/pipeline.py` — `run_manual_search()`, `run_manual_ask()`, `validate_answer()`, 정책 상수 정식 구현. 기존 `run_manual_qa()` 는 NotImplementedError 유지.
6. `app/services/ai/manual_qa.py` — wrapper로 축소 (281줄 → 약 80줄).
7. `app/services/ai/rag/schemas.py` — Chunk dataclass / embedding_called field / REASON_VECTOR_DISABLED / REASON_EMBEDDING_SKIPPED_* (5개) 제거. 23개 reason_code 와 4개 optional Answer 필드만 보유.

### 수정 (테스트/하네스 — 18-1 잔재 정리)
8. `tests/test_ai_full_harness.py` — `test_vector_package_importable` 제거. `test_no_circular_import_when_loading_skeleton` 에서 vector 4개 항목 제거. docstring 갱신.
9. `tests/test_ai_manual_rag_harness.py` — `test_schemas_optional_5_keys_present` → `test_schemas_optional_4_keys_present` (embedding_called 제거). `test_schemas_reason_codes_29_defined` → `test_schemas_reason_codes_23_defined`.
10. `tests/test_ai_manual_rag_contract.py` — `test_contract_optional_keys_not_required_in_v1_3_3` 의 optional 키 목록에서 embedding_called 제거.
11. `tests/harness/contract.py` — `OPTIONAL_KEYS` 에서 embedding_called 제거. docstring 갱신.

### 삭제
12. `app/services/ai/vector/__init__.py`
13. `app/services/ai/vector/embeddings.py`
14. `app/services/ai/vector/similarity.py`
15. `app/services/ai/vector/store.py`

### 손대지 않음
- `app/routers/ai.py`, `app/services/rag/search.py`, `tests/conftest.py`, 기타 tests/ 파일들.
- `requirements.txt`, `dosu_clinic.spec`, `app/migrations/`, `app/templates/`, `app/static/`, `pyproject.toml`.

## 3. manual_qa.py 호환 유지 방식

(이전 보고와 동일)
- `from app.services.ai import manual_qa as ai_manual_qa` 그대로 동작.
- 시그니처 100% 보존: `ask_manual_question`, `manual_search`, `validate_answer`.
- 공개 상수 `LOW_SCORE_THRESHOLD = 2`, `_MANUAL_SYSTEM_PROMPT` 재노출.

## 4. 응답 구조 보존

- `/api/ai/manual/search` → `{sources, masked_question, top_score}` 그대로.
- `/api/ai/manual/ask` → 9개 필수 키 그대로.
- `sources[]` → `{title, path, snippet}` 그대로.
- 신규 optional 키 추가 없음 (현재 응답에는 0개).

## 5. Local-first 게이트

`run_manual_ask` 의 게이트 (위에서 아래):
1. `results == []` → provider 호출 0
2. `top_score < LOW_SCORE_THRESHOLD(=2)` → provider 호출 0
3. `provider_override is None` → provider 호출 0
4. PII 마스킹은 retriever 호출 전 수행 → FakeProvider prompt 에 원본 PII 부재.

## 6. 18-2 스코프 준수 (모두 ✅)

- chunker / vector / embedding / hybrid retriever: ❌ 없음 (코드/디렉토리/테스트 모두)
- DB migration: ❌ 없음
- requirements / spec / UI / 라우터 응답 키: ❌ 변경 없음
- 운영 DB 접근: ❌ 없음
- 실제 외부 LLM/Embedding 호출: ❌ 없음 (FakeProvider only)
- 기존 SMS AI / 휴무 AI 동작: ❌ 변경 없음 (회귀 테스트 통과)
- 하네스/테스트 약화: ❌ 없음 (skip/xfail 추가 없음)
- 18-1 잔재 정리: ✅ 완료 (vector/, chunk/embedding 관련 schemas/tests)

## 7. 수정 루프 횟수

총 1회. 1회차에서 발생한 단일 결함 — `knowledge/loader.py` 의 `from ...config` 깊이 오류(3 dot → 4 dot) 즉시 수정 후 통과.
스코프 엄격화 (Codex 재검증 후) 는 별도 트랙으로 처리 — 추가 결함 0.
